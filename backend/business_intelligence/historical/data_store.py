"""
Historical Data Store

Persists all BI intelligence over time using JSON file storage.
This is designed to work immediately without requiring additional
database setup -- it uses the filesystem as the persistence layer.

Data retention is configurable. The store maintains:
- Intelligence snapshots (daily)
- Market data points (rolling window)
- Pain point evolution
- Opportunity score history
- Campaign results
- Waitlist growth

When the data grows large enough, this can be migrated to SQLite
or PostgreSQL using the existing GRACE database infrastructure.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path

from business_intelligence.models.data_models import (
    IntelligenceSnapshot,
    MarketDataPoint,
    PainPoint,
    MarketOpportunity,
    CampaignResult,
)

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'value'):
            return obj.value
        if hasattr(obj, '__dataclass_fields__'):
            return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
        return super().default(obj)


class HistoricalDataStore:
    """File-based historical data store for BI intelligence."""

    def __init__(
        self,
        storage_dir: str = "backend/data/bi_intelligence",
        retention_days: int = 365,
    ):
        self.storage_dir = Path(storage_dir)
        self.retention_days = retention_days
        self._ensure_directories()

    def _ensure_directories(self):
        subdirs = [
            "snapshots", "market_data", "pain_points",
            "opportunities", "campaigns", "waitlist",
        ]
        for subdir in subdirs:
            (self.storage_dir / subdir).mkdir(parents=True, exist_ok=True)

    async def save_snapshot(self, snapshot: IntelligenceSnapshot) -> str:
        """Save an intelligence snapshot."""
        filename = f"snapshot_{snapshot.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.storage_dir / "snapshots" / filename

        data = self._serialize(snapshot)
        self._write_json(filepath, data)

        logger.info(f"Saved intelligence snapshot: {filename}")
        return str(filepath)

    async def load_snapshots(
        self,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """Load historical snapshots."""
        snapshot_dir = self.storage_dir / "snapshots"
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        snapshots = []

        if not snapshot_dir.exists():
            return snapshots

        for filepath in sorted(snapshot_dir.glob("snapshot_*.json")):
            try:
                data = self._read_json(filepath)
                if data:
                    ts = data.get("timestamp", "")
                    if ts:
                        snap_time = datetime.fromisoformat(ts)
                        if snap_time >= cutoff:
                            snapshots.append(data)
            except Exception as e:
                logger.error(f"Failed to load snapshot {filepath}: {e}")

        return snapshots

    async def save_market_data(
        self,
        data_points: List[MarketDataPoint],
        niche: str = "",
    ) -> int:
        """Save market data points."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        niche_slug = niche.replace(" ", "_").lower()[:30] or "general"
        filename = f"market_{niche_slug}_{date_str}.json"
        filepath = self.storage_dir / "market_data" / filename

        existing = self._read_json(filepath) or []
        for dp in data_points:
            existing.append(self._serialize(dp))

        self._write_json(filepath, existing)
        return len(data_points)

    async def load_market_data(
        self,
        niche: Optional[str] = None,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """Load historical market data."""
        data_dir = self.storage_dir / "market_data"
        if not data_dir.exists():
            return []

        pattern = f"market_{'*' if not niche else niche.replace(' ', '_').lower()[:30]}*.json"
        all_data = []

        for filepath in data_dir.glob(pattern):
            try:
                data = self._read_json(filepath)
                if isinstance(data, list):
                    all_data.extend(data)
                elif data:
                    all_data.append(data)
            except Exception as e:
                logger.error(f"Failed to load market data {filepath}: {e}")

        return all_data

    async def save_pain_points(
        self,
        pain_points: List[PainPoint],
        niche: str = "",
    ) -> int:
        """Save discovered pain points."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        niche_slug = niche.replace(" ", "_").lower()[:30] or "general"
        filename = f"pain_points_{niche_slug}_{date_str}.json"
        filepath = self.storage_dir / "pain_points" / filename

        data = [self._serialize(pp) for pp in pain_points]
        self._write_json(filepath, data)
        return len(data)

    async def load_pain_point_history(
        self,
        niche: Optional[str] = None,
        days_back: int = 90,
    ) -> List[Dict[str, Any]]:
        """Load pain point history to track evolution."""
        pp_dir = self.storage_dir / "pain_points"
        if not pp_dir.exists():
            return []

        all_points = []
        pattern = f"pain_points_{'*' if not niche else niche.replace(' ', '_').lower()[:30]}*.json"

        for filepath in pp_dir.glob(pattern):
            try:
                data = self._read_json(filepath)
                if isinstance(data, list):
                    all_points.extend(data)
            except Exception as e:
                logger.error(f"Failed to load pain points {filepath}: {e}")

        return all_points

    async def save_campaign_results(
        self,
        results: List[CampaignResult],
    ) -> int:
        """Save campaign results."""
        date_str = datetime.utcnow().strftime("%Y%m%d")
        filename = f"campaigns_{date_str}.json"
        filepath = self.storage_dir / "campaigns" / filename

        existing = self._read_json(filepath) or []
        for r in results:
            existing.append(self._serialize(r))

        self._write_json(filepath, existing)
        return len(results)

    async def get_timeline(
        self,
        days_back: int = 90,
    ) -> Dict[str, Any]:
        """Get a timeline view of all intelligence over time.

        This is the "historical datagraph" mentioned in the requirements --
        the ability to look back 1, 2, 3, 6 months and see how the
        intelligence picture has evolved.
        """
        snapshots = await self.load_snapshots(days_back=days_back)

        timeline = {
            "period_days": days_back,
            "total_snapshots": len(snapshots),
            "data_points_over_time": [],
            "pain_points_over_time": [],
            "opportunities_over_time": [],
            "phase_transitions": [],
        }

        for snap in snapshots:
            ts = snap.get("timestamp", "")
            timeline["data_points_over_time"].append({
                "date": ts,
                "count": snap.get("data_points_collected", 0),
            })

            pp_count = len(snap.get("top_pain_points", []))
            timeline["pain_points_over_time"].append({
                "date": ts,
                "count": pp_count,
            })

            opp_count = len(snap.get("top_opportunities", []))
            timeline["opportunities_over_time"].append({
                "date": ts,
                "count": opp_count,
            })

            timeline["phase_transitions"].append({
                "date": ts,
                "phase": snap.get("phase", "unknown"),
            })

        if len(snapshots) >= 2:
            first = snapshots[0]
            last = snapshots[-1]

            first_dp = first.get("data_points_collected", 0)
            last_dp = last.get("data_points_collected", 0)

            timeline["growth"] = {
                "data_points": {
                    "start": first_dp,
                    "end": last_dp,
                    "change": last_dp - first_dp,
                    "percentage": ((last_dp - first_dp) / max(first_dp, 1)) * 100,
                },
                "phases_progressed": (
                    first.get("phase", "unknown") != last.get("phase", "unknown")
                ),
            }

        return timeline

    async def cleanup_old_data(self) -> Dict[str, int]:
        """Remove data older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        cutoff_str = cutoff.strftime("%Y%m%d")
        removed = {"snapshots": 0, "market_data": 0, "pain_points": 0, "campaigns": 0}

        for subdir in removed:
            dir_path = self.storage_dir / subdir
            if not dir_path.exists():
                continue

            for filepath in dir_path.glob("*.json"):
                parts = filepath.stem.split("_")
                date_parts = [p for p in parts if len(p) == 8 and p.isdigit()]
                if date_parts and date_parts[0] < cutoff_str:
                    filepath.unlink()
                    removed[subdir] += 1

        total = sum(removed.values())
        if total:
            logger.info(f"Cleaned up {total} old data files: {removed}")

        return removed

    def _serialize(self, obj: Any) -> Any:
        """Serialize a dataclass or other object to JSON-compatible dict."""
        if hasattr(obj, '__dataclass_fields__'):
            return json.loads(json.dumps(asdict(obj), cls=DateTimeEncoder))
        return obj

    def _write_json(self, filepath: Path, data: Any):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, cls=DateTimeEncoder)

    def _read_json(self, filepath: Path) -> Any:
        if not filepath.exists():
            return None
        try:
            with open(filepath) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read {filepath}: {e}")
            return None
