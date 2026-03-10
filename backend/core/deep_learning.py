"""
Grace Deep Learning Model — predicts action success, component risk,
and trust scores from Genesis key patterns.

Architecture: 3-head MLP on 32-dim feature vector
  Head 1: Will next action succeed? (binary)
  Head 2: Which component breaks next? (10-class)
  Head 3: What trust score? (regression 0-1)

Trains continuously from Genesis keys. CPU-only, <50MB.
"""

import math
import json
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional
from collections import Counter

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.info("PyTorch not available — deep learning disabled")


COMPONENT_CLASSES = [
    "chat_engine", "llm_orchestrator", "consensus_engine", "retrieval",
    "ingestion", "database", "genesis_tracker", "diagnostic_engine",
    "self_healing", "unknown",
]

KEY_TYPES = [
    "ai_response", "api_request", "system_event", "error",
    "code_change", "file_op", "learning_complete", "gap_identified",
    "user_input", "unknown",
]


def _key_to_features(key: dict) -> list:
    """Convert a Genesis key to a 32-dim feature vector."""
    features = [0.0] * 32

    # Key type one-hot (10 dims)
    kt = key.get("key_type", "unknown")
    if kt in KEY_TYPES:
        features[KEY_TYPES.index(kt)] = 1.0

    # Is error (1 dim)
    features[10] = 1.0 if key.get("is_error") else 0.0

    # Hour of day (1 dim, normalized)
    when = key.get("when", "")
    try:
        dt = datetime.fromisoformat(when) if when else datetime.now(timezone.utc)
        features[11] = dt.hour / 24.0
        features[12] = dt.weekday() / 7.0
    except Exception:
        pass

    # Text length features (3 dims)
    what = key.get("what", "")
    features[13] = min(len(what) / 200.0, 1.0)
    features[14] = 1.0 if "error" in what.lower() else 0.0
    features[15] = 1.0 if "fail" in what.lower() else 0.0

    # Tag count (1 dim)
    tags = key.get("tags", [])
    features[16] = min(len(tags) / 10.0, 1.0) if isinstance(tags, list) else 0.0

    # Who actor hash (4 dims)
    who = key.get("who", "")
    if who:
        h = hash(who) % 10000
        features[17] = (h % 100) / 100.0
        features[18] = ((h // 100) % 100) / 100.0

    # Component detection from what/who (10 dims)
    text = (what + " " + who).lower()
    for i, comp in enumerate(COMPONENT_CLASSES):
        if comp.replace("_", " ") in text or comp.replace("_", "") in text:
            features[19 + i] = 1.0

    # Has file path (1 dim)
    features[29] = 1.0 if key.get("file_path") else 0.0

    # Error type present (1 dim)
    features[30] = 1.0 if key.get("error_type") else 0.0

    # Trust-related (1 dim)
    features[31] = key.get("trust_score", 0.5) if isinstance(key.get("trust_score"), (int, float)) else 0.5

    return features


if TORCH_AVAILABLE:
    class GracePredictor(nn.Module):
        """3-head predictor: success, component risk, trust score."""

        def __init__(self, input_dim: int = 32, hidden_dim: int = 64,
                     n_components: int = 10):
            super().__init__()
            self.shared = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1),
            )
            self.head_success = nn.Linear(hidden_dim, 1)
            self.head_component = nn.Linear(hidden_dim, n_components)
            self.head_trust = nn.Linear(hidden_dim, 1)

        def forward(self, x):
            h = self.shared(x)
            success = torch.sigmoid(self.head_success(h))
            component = self.head_component(h)
            trust = torch.sigmoid(self.head_trust(h))
            return success.squeeze(-1), component, trust.squeeze(-1)


class GraceModelManager:
    """Manages training and inference for the Grace DL model."""

    MODEL_PATH = "data/grace_model.pt"

    def __init__(self):
        self.model = None
        self.optimizer = None
        self._lock = threading.Lock()

        if TORCH_AVAILABLE:
            self.model = GracePredictor()
            self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
            self._load_weights()

    def _load_weights(self):
        try:
            from pathlib import Path
            p = Path(self.MODEL_PATH)
            if p.exists():
                self.model.load_state_dict(torch.load(str(p), map_location="cpu"))
                logger.info("Grace model loaded from disk")
        except Exception as e:
            logger.debug(f"No saved model: {e}")

    def _save_weights(self):
        try:
            from pathlib import Path
            Path(self.MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
            torch.save(self.model.state_dict(), self.MODEL_PATH)
        except Exception:
            pass

    def train_batch(self, keys: List[dict]) -> dict:
        """Train on a batch of Genesis keys."""
        if not TORCH_AVAILABLE or not self.model or len(keys) < 2:
            return {"status": "skipped", "reason": "not enough data or no torch"}

        with self._lock:
            self.model.train()

            features = []
            labels_success = []
            labels_component = []
            labels_trust = []

            for i in range(len(keys) - 1):
                x = _key_to_features(keys[i])
                next_key = keys[i + 1]

                features.append(x)
                labels_success.append(0.0 if next_key.get("is_error") else 1.0)

                comp_text = (next_key.get("what", "") + " " + next_key.get("who", "")).lower()
                comp_idx = 9  # unknown
                for j, c in enumerate(COMPONENT_CLASSES):
                    if c.replace("_", " ") in comp_text:
                        comp_idx = j
                        break
                labels_component.append(comp_idx)
                labels_trust.append(0.3 if next_key.get("is_error") else 0.7)

            X = torch.FloatTensor(features)
            y_s = torch.FloatTensor(labels_success)
            y_c = torch.LongTensor(labels_component)
            y_t = torch.FloatTensor(labels_trust)

            pred_s, pred_c, pred_t = self.model(X)

            loss_s = nn.BCELoss()(pred_s, y_s)
            loss_c = nn.CrossEntropyLoss()(pred_c, y_c)
            loss_t = nn.MSELoss()(pred_t, y_t)
            loss = loss_s + loss_c + 0.5 * loss_t

            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            self._save_weights()

            return {
                "status": "trained",
                "samples": len(features),
                "loss": round(loss.item(), 4),
                "loss_success": round(loss_s.item(), 4),
                "loss_component": round(loss_c.item(), 4),
                "loss_trust": round(loss_t.item(), 4),
            }

    def predict(self, key: dict) -> dict:
        """Predict success, risky component, and trust for next action."""
        if not TORCH_AVAILABLE or not self.model:
            return {"available": False}

        with self._lock:
            self.model.eval()
            with torch.no_grad():
                x = torch.FloatTensor([_key_to_features(key)])
                pred_s, pred_c, pred_t = self.model(x)

                success_prob = pred_s[0].item()
                component_probs = torch.softmax(pred_c[0], dim=0)
                risky_idx = torch.argmax(component_probs).item()
                trust_pred = pred_t[0].item()

                return {
                    "available": True,
                    "success_probability": round(success_prob, 3),
                    "risky_component": COMPONENT_CLASSES[risky_idx],
                    "component_risk": round(component_probs[risky_idx].item(), 3),
                    "predicted_trust": round(trust_pred, 3),
                    "all_risks": {
                        COMPONENT_CLASSES[i]: round(component_probs[i].item(), 3)
                        for i in range(len(COMPONENT_CLASSES))
                        if component_probs[i].item() > 0.05
                    },
                }

    def train_from_db(self, hours: int = 24, limit: int = 1000) -> dict:
        """Load Genesis keys from DB and train."""
        try:
            from core.intelligence import GenesisKeyMiner
            miner = GenesisKeyMiner()
            keys = miner._load_keys(hours, limit)
            if not keys:
                return {"status": "no_data"}

            result = self.train_batch(keys)

            try:
                from api._genesis_tracker import track
                track(
                    key_type="learning_complete",
                    what=f"DL model trained: {result.get('samples', 0)} samples, loss={result.get('loss', '?')}",
                    who="grace_model",
                    tags=["deep-learning", "training", "genesis_train"],
                )
            except Exception:
                pass

            return result
        except Exception as e:
            return {"status": f"error: {e}"}


_model_manager: Optional[GraceModelManager] = None


def get_model() -> GraceModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = GraceModelManager()
    return _model_manager
