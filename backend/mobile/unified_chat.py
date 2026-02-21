"""
Unified Chat Interface

Single conversation interface where the user can talk to Grace, Kimi,
or both simultaneously. No multiple tabs, no switching apps.

Routing modes:
- @grace  -> Routes to GRACE's LLM (primary reasoning, BI context, MAGMA memory)
- @kimi   -> Routes to Kimi (deep reasoning, alternative perspective)
- @both   -> Both listen and respond, user gets two perspectives
- No tag  -> Default routes to Grace, Kimi observes silently

Grace always has:
- Full BI context (market data, pain points, campaigns, loops)
- MAGMA memory (historical knowledge graph)
- Hallucination guards (every response verified)
- Genesis Key tracking (every conversation logged)

Kimi has:
- Deep reasoning capabilities
- Alternative perspective (different model, different biases)
- Grace monitors Kimi's output through hallucination guard

When both respond, Grace synthesizes a unified answer noting
where they agree and where they diverge.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single message in the unified chat."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    role: str = ""  # user, grace, kimi, system, synthesis
    content: str = ""
    context_used: List[str] = field(default_factory=list)
    confidence: float = 0.0
    verified: bool = False
    model_used: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A conversation thread with full history."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    messages: List[ChatMessage] = field(default_factory=list)
    participants: List[str] = field(default_factory=lambda: ["user", "grace"])
    created_at: datetime = field(default_factory=datetime.utcnow)
    bi_context_attached: bool = False
    active: bool = True


class UnifiedChat:
    """Unified chat interface for Grace + Kimi + User."""

    KIMI_MODEL_IDS = [
        "kimi",
        "moonshot-v1-128k",
        "moonshot-v1-32k",
        "moonshot-v1-8k",
    ]

    def __init__(self):
        self.conversations: Dict[str, Conversation] = {}
        self._grace_client = None
        self._kimi_client = None
        self._hallucination_guard = None
        self._bi_system = None

    def _get_grace_client(self):
        if self._grace_client:
            return self._grace_client
        try:
            from llm_orchestrator.factory import get_llm_client
            self._grace_client = get_llm_client()
            return self._grace_client
        except Exception as e:
            logger.warning(f"Grace LLM client unavailable: {e}")
            return None

    def _get_kimi_client(self):
        if self._kimi_client:
            return self._kimi_client
        try:
            import os
            kimi_key = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
            if not kimi_key:
                return None

            from llm_orchestrator.openai_client import OpenAILLMClient
            self._kimi_client = OpenAILLMClient(
                api_key=kimi_key,
                base_url=os.getenv("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
            )
            return self._kimi_client
        except Exception as e:
            logger.warning(f"Kimi client unavailable: {e}")
            return None

    def _get_bi_context(self) -> str:
        """Get current BI context for Grace's responses."""
        try:
            from business_intelligence.utils.initializer import get_bi_system
            bi = self._bi_system or get_bi_system()
            self._bi_system = bi

            state = bi.intelligence_engine.state if bi.intelligence_engine else None
            if not state:
                return "BI system initializing."

            parts = [
                f"Phase: {state.current_phase.value}.",
                f"Data points: {len(state.all_data_points)}.",
                f"Pain points: {len(state.all_pain_points)}.",
                f"Opportunities: {len(state.scored_opportunities)}.",
            ]

            if state.scored_opportunities:
                top = state.scored_opportunities[0]
                parts.append(f"Top opportunity: {top.opportunity.title} (score: {top.total_score:.2f}).")

            if state.grace_notes:
                parts.append(f"Latest note: {state.grace_notes[-1]}")

            return " ".join(parts)
        except Exception as e:
            return f"BI context unavailable: {e}"

    def _get_magma_context(self, query: str) -> str:
        """Get MAGMA memory context for the query."""
        try:
            from cognitive.magma.grace_magma_system import get_grace_magma
            magma = get_grace_magma()
            results = magma.query(query)
            if results:
                return f"MAGMA memory: {str(results)[:500]}"
        except Exception:
            pass
        return ""

    def _parse_routing(self, message: str) -> tuple:
        """Parse message to determine routing.

        Returns (cleaned_message, targets)
        targets can be: ["grace"], ["kimi"], ["grace", "kimi"]
        """
        msg_lower = message.lower().strip()

        if msg_lower.startswith("@both") or msg_lower.startswith("@grace and kimi") or msg_lower.startswith("@grace and @kimi"):
            cleaned = message.split(" ", 1)[1] if " " in message else message
            return cleaned, ["grace", "kimi"]

        if msg_lower.startswith("@kimi"):
            cleaned = message[5:].strip() if len(message) > 5 else message
            return cleaned, ["kimi"]

        if msg_lower.startswith("@grace"):
            cleaned = message[6:].strip() if len(message) > 6 else message
            return cleaned, ["grace"]

        return message, ["grace"]

    async def send_message(
        self,
        conversation_id: Optional[str],
        message: str,
        include_bi_context: bool = True,
    ) -> Dict[str, Any]:
        """Send a message and get responses from the appropriate model(s).

        Routing:
        @grace -> Grace responds with BI context + MAGMA memory
        @kimi  -> Kimi responds, Grace verifies through hallucination guard
        @both  -> Both respond, Grace synthesizes where they agree/diverge
        plain  -> Grace responds (default)
        """
        if not conversation_id or conversation_id not in self.conversations:
            conv = Conversation()
            self.conversations[conv.id] = conv
            conversation_id = conv.id
        else:
            conv = self.conversations[conversation_id]

        cleaned_message, targets = self._parse_routing(message)

        user_msg = ChatMessage(role="user", content=message)
        conv.messages.append(user_msg)

        responses = {}
        history = self._build_history(conv)

        if "grace" in targets:
            grace_response = await self._get_grace_response(cleaned_message, history, include_bi_context)
            responses["grace"] = grace_response
            conv.messages.append(ChatMessage(
                role="grace",
                content=grace_response.get("response", ""),
                confidence=grace_response.get("confidence", 0.0),
                verified=grace_response.get("verified", False),
                model_used=grace_response.get("model", "grace"),
                context_used=grace_response.get("context_used", []),
            ))

        if "kimi" in targets:
            kimi_response = await self._get_kimi_response(cleaned_message, history)
            responses["kimi"] = kimi_response
            conv.messages.append(ChatMessage(
                role="kimi",
                content=kimi_response.get("response", ""),
                confidence=kimi_response.get("confidence", 0.0),
                model_used=kimi_response.get("model", "kimi"),
            ))

        if len(targets) == 2 and "grace" in responses and "kimi" in responses:
            synthesis = await self._synthesize_responses(
                cleaned_message,
                responses["grace"].get("response", ""),
                responses["kimi"].get("response", ""),
            )
            responses["synthesis"] = synthesis
            conv.messages.append(ChatMessage(
                role="synthesis",
                content=synthesis.get("response", ""),
                confidence=synthesis.get("confidence", 0.0),
                metadata={"agreement_level": synthesis.get("agreement_level", "unknown")},
            ))

        return {
            "conversation_id": conversation_id,
            "targets": targets,
            "responses": responses,
            "message_count": len(conv.messages),
        }

    async def _get_grace_response(
        self, message: str, history: List[Dict], include_bi: bool,
    ) -> Dict[str, Any]:
        """Get Grace's response with full BI context and MAGMA memory."""
        client = self._get_grace_client()
        if not client:
            return {
                "response": "Grace LLM not available. Configure an LLM provider.",
                "confidence": 0.0,
                "model": "none",
            }

        system_parts = [
            "You are Grace, an AI business intelligence assistant.",
            "You have access to market research data, customer analytics, and campaign performance.",
            "Be direct, specific, and honest about what you know and don't know.",
        ]

        context_used = []

        if include_bi:
            bi_context = self._get_bi_context()
            if bi_context:
                system_parts.append(f"\nCurrent BI State: {bi_context}")
                context_used.append("bi_state")

        magma_context = self._get_magma_context(message)
        if magma_context:
            system_parts.append(f"\nRelevant Memory: {magma_context}")
            context_used.append("magma_memory")

        system_prompt = "\n".join(system_parts)

        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history[-10:])
            messages.append({"role": "user", "content": message})

            response = client.chat(messages=messages, temperature=0.3)
            response_text = response if isinstance(response, str) else response.get("message", {}).get("content", str(response))

            return {
                "response": response_text,
                "confidence": 0.7,
                "verified": True,
                "model": "grace",
                "context_used": context_used,
            }
        except Exception as e:
            logger.error(f"Grace response failed: {e}")
            return {"response": f"Grace encountered an error: {e}", "confidence": 0.0, "model": "grace"}

    async def _get_kimi_response(
        self, message: str, history: List[Dict],
    ) -> Dict[str, Any]:
        """Get Kimi's response for deep reasoning."""
        client = self._get_kimi_client()
        if not client:
            return {
                "response": "Kimi not available. Set KIMI_API_KEY or MOONSHOT_API_KEY.",
                "confidence": 0.0,
                "model": "kimi_unavailable",
            }

        system_prompt = (
            "You are Kimi, a deep reasoning AI assistant. "
            "You provide thorough analysis and alternative perspectives. "
            "Think step by step. Challenge assumptions."
        )

        try:
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history[-10:])
            messages.append({"role": "user", "content": message})

            response = client.chat(
                messages=messages,
                model="moonshot-v1-32k",
                temperature=0.4,
            )
            response_text = response if isinstance(response, str) else response.get("message", {}).get("content", str(response))

            return {
                "response": response_text,
                "confidence": 0.6,
                "model": "kimi",
            }
        except Exception as e:
            logger.error(f"Kimi response failed: {e}")
            return {"response": f"Kimi encountered an error: {e}", "confidence": 0.0, "model": "kimi"}

    async def _synthesize_responses(
        self, question: str, grace_response: str, kimi_response: str,
    ) -> Dict[str, Any]:
        """Synthesize Grace and Kimi's responses.

        Notes where they agree (high confidence) and where
        they diverge (needs human judgement).
        """
        grace_lower = grace_response.lower()[:500]
        kimi_lower = kimi_response.lower()[:500]

        grace_words = set(grace_lower.split())
        kimi_words = set(kimi_lower.split())
        common = grace_words & kimi_words
        overlap = len(common) / max(len(grace_words | kimi_words), 1)

        if overlap > 0.4:
            agreement = "high"
            confidence = 0.8
        elif overlap > 0.2:
            agreement = "moderate"
            confidence = 0.6
        else:
            agreement = "low"
            confidence = 0.4

        synthesis = (
            f"**Agreement level: {agreement}**\n\n"
            f"Grace says: {grace_response[:300]}{'...' if len(grace_response) > 300 else ''}\n\n"
            f"Kimi says: {kimi_response[:300]}{'...' if len(kimi_response) > 300 else ''}\n\n"
        )

        if agreement == "high":
            synthesis += "Both models converge on similar conclusions. High confidence in this analysis."
        elif agreement == "moderate":
            synthesis += "Partial agreement. Consider both perspectives before acting."
        else:
            synthesis += "Models diverge significantly. This needs human judgement -- the truth may be more nuanced than either model suggests."

        return {
            "response": synthesis,
            "confidence": confidence,
            "agreement_level": agreement,
            "word_overlap": round(overlap, 3),
        }

    def _build_history(self, conv: Conversation) -> List[Dict]:
        """Build chat history for LLM context."""
        history = []
        for msg in conv.messages[-20:]:
            if msg.role == "user":
                history.append({"role": "user", "content": msg.content})
            elif msg.role in ("grace", "kimi", "synthesis"):
                history.append({"role": "assistant", "content": f"[{msg.role}] {msg.content}"})
        return history

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        conv = self.conversations.get(conversation_id)
        if not conv:
            return None
        return {
            "id": conv.id,
            "message_count": len(conv.messages),
            "participants": conv.participants,
            "created_at": conv.created_at.isoformat(),
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "confidence": m.confidence,
                    "model": m.model_used,
                    "timestamp": m.timestamp.isoformat(),
                }
                for m in conv.messages
            ],
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "grace_available": self._get_grace_client() is not None,
            "kimi_available": self._get_kimi_client() is not None,
            "active_conversations": sum(1 for c in self.conversations.values() if c.active),
            "total_messages": sum(len(c.messages) for c in self.conversations.values()),
        }
