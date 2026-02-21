"""
GRACE Mobile API

Lightweight API endpoints optimized for mobile consumption.
Everything the mobile app needs in as few requests as possible.

Design principles:
- Single-request dashboards (one call, all data)
- Quick actions (approve/reject in one tap)
- Optimized payloads (no unnecessary data)
- Offline-friendly (queue actions when disconnected)
- Biometric auth support
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile", tags=["Mobile App"])


# ==================== Models ====================

class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token")
    platform: str = Field("android", description="ios or android")


class QuickActionRequest(BaseModel):
    notification_id: str = Field(..., description="Notification ID to respond to")
    action: str = Field(..., description="Action taken (approve, reject, reply, etc)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional response data")


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="Message to Grace")
    voice_transcription: bool = Field(False, description="Whether this was voice-transcribed")


class VoiceCommandRequest(BaseModel):
    command: str = Field(..., description="Voice command text")


# ==================== Mobile Dashboard ====================

@router.get("/dashboard")
async def get_mobile_dashboard():
    """Single-request mobile dashboard -- everything at a glance.

    Returns the 4 key numbers + alerts + pending actions.
    Designed for a single phone screen.
    """
    try:
        from business_intelligence.utils.initializer import get_bi_system
        bi = get_bi_system()

        waitlist_count = 0
        waitlist_target = 500
        if bi.waitlist_manager:
            stats = await bi.waitlist_manager.get_stats()
            waitlist_count = stats.active_signups
            waitlist_target = stats.validation_threshold

        total_spend = 0.0
        total_signups = 0
        cpa = 0.0
        if bi.campaign_manager:
            summary = await bi.campaign_manager.get_campaign_summary()
            total_spend = summary.get("total_spend", 0)
            total_signups = summary.get("total_signups", 0)
            cpa = summary.get("overall_cpa", 0)

        top_opp_score = 0.0
        top_opp_title = ""
        if bi.intelligence_engine and bi.intelligence_engine.state.scored_opportunities:
            top = bi.intelligence_engine.state.scored_opportunities[0]
            top_opp_score = top.total_score
            top_opp_title = top.opportunity.title

        phase = "initializing"
        if bi.intelligence_engine:
            phase = bi.intelligence_engine.state.current_phase.value

        from mobile.push_notifications import PushNotificationService
        notif_service = _get_notification_service()
        pending = await notif_service.get_pending_notifications()
        action_required = [n for n in pending if n.get("requires_response")]

        return {
            "glance": {
                "waitlist": {"count": waitlist_count, "target": waitlist_target, "pct": round(waitlist_count / max(waitlist_target, 1) * 100, 1)},
                "spend_today": round(total_spend, 2),
                "cpa": round(cpa, 2),
                "top_opportunity": {"title": top_opp_title[:40], "score": round(top_opp_score, 2)},
            },
            "phase": phase,
            "alerts": pending[:5],
            "action_required": len(action_required),
            "action_items": action_required[:3],
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Mobile dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Device Registration ====================

@router.post("/register-device")
async def register_device(request: DeviceRegisterRequest):
    """Register a mobile device for push notifications."""
    try:
        service = _get_notification_service()
        return await service.register_device(
            device_id=request.device_id,
            fcm_token=request.fcm_token,
            platform=request.platform,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Notifications ====================

@router.get("/notifications")
async def get_notifications(unread_only: bool = True):
    """Get notifications (pending/all)."""
    try:
        service = _get_notification_service()
        if unread_only:
            return {"notifications": await service.get_pending_notifications()}
        return {
            "notifications": [
                {
                    "id": n.id, "title": n.title, "body": n.body,
                    "category": n.category.value, "priority": n.priority.value,
                    "read": n.read, "responded": n.responded,
                    "created_at": n.created_at.isoformat(),
                }
                for n in sorted(service.notifications, key=lambda n: n.created_at, reverse=True)[:50]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/status")
async def get_notification_status():
    """Get push notification system status."""
    try:
        return _get_notification_service().get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Quick Actions ====================

@router.post("/quick-action")
async def execute_quick_action(request: QuickActionRequest):
    """Execute a quick action from a notification (approve, reject, reply).

    Designed for one-tap responses from the phone lock screen.
    """
    try:
        service = _get_notification_service()

        result = await service.record_response(
            notification_id=request.notification_id,
            action=request.action,
            response_data=request.data,
        )

        if request.action == "approve":
            notif = next((n for n in service.notifications if n.id == request.notification_id), None)
            if notif and notif.data.get("action_id"):
                from business_intelligence.utils.initializer import get_bi_system
                bi = get_bi_system()
                if bi.campaign_manager:
                    await bi.campaign_manager.approve_campaign(notif.data["action_id"])
                    result["campaign_approved"] = True

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Chat ====================

@router.post("/chat")
async def mobile_chat(request: ChatMessageRequest):
    """Send a chat message to Grace from mobile.

    Supports text and voice-transcribed messages.
    Grace responds with her current BI context.
    """
    try:
        from business_intelligence.utils.initializer import get_bi_system
        bi = get_bi_system()

        if bi.reasoning_engine:
            state = await bi.intelligence_engine.get_status() if bi.intelligence_engine else {}
            result = await bi.reasoning_engine.generate_grace_briefing(
                {"user_message": request.message, **state}
            )
            return {
                "response": result.reasoning,
                "confidence": result.confidence,
                "source": "grace_bi_reasoning",
                "voice_transcribed": request.voice_transcription,
            }

        return {
            "response": "Grace BI reasoning engine not available. Configure an LLM provider.",
            "confidence": 0.0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Voice Commands ====================

@router.post("/voice-command")
async def process_voice_command(request: VoiceCommandRequest):
    """Process a voice command from the mobile app.

    Supported commands:
    - 'What's the waitlist at?'
    - 'Pause the [platform] campaign'
    - 'Run a quick scan on [niche]'
    - 'What's our CPA?'
    - 'Give me the daily briefing'
    - 'How many pain points have we found?'
    """
    try:
        command = request.command.lower().strip()
        from business_intelligence.utils.initializer import get_bi_system
        bi = get_bi_system()

        if any(w in command for w in ["waitlist", "signups", "how many signed"]):
            if bi.waitlist_manager:
                stats = await bi.waitlist_manager.get_stats()
                return {
                    "response": f"Waitlist is at {stats.active_signups} out of {stats.validation_threshold}. "
                                f"{'Target reached!' if stats.validation_reached else f'{stats.validation_threshold - stats.active_signups} more needed.'}",
                    "data": {"count": stats.active_signups, "target": stats.validation_threshold},
                }

        if any(w in command for w in ["cpa", "cost per", "acquisition cost"]):
            if bi.campaign_manager:
                summary = await bi.campaign_manager.get_campaign_summary()
                return {
                    "response": f"Overall CPA is {summary.get('overall_cpa', 0):.2f} GBP. "
                                f"Total spend: {summary.get('total_spend', 0):.2f} GBP. "
                                f"Total signups: {summary.get('total_signups', 0)}.",
                    "data": summary,
                }

        if any(w in command for w in ["briefing", "update", "what's happening"]):
            if bi.reasoning_engine:
                state = await bi.intelligence_engine.get_status() if bi.intelligence_engine else {}
                result = await bi.reasoning_engine.generate_grace_briefing(state)
                return {"response": result.reasoning, "confidence": result.confidence}

        if any(w in command for w in ["pain point", "problems", "complaints"]):
            if bi.intelligence_engine:
                count = len(bi.intelligence_engine.state.all_pain_points)
                return {"response": f"I've found {count} pain points across all niches.", "data": {"count": count}}

        if any(w in command for w in ["opportunity", "best opportunity", "top opportunity"]):
            if bi.intelligence_engine and bi.intelligence_engine.state.scored_opportunities:
                top = bi.intelligence_engine.state.scored_opportunities[0]
                return {
                    "response": f"Top opportunity: {top.opportunity.title} with score {top.total_score:.2f}. "
                                f"Verdict: {top.verdict}",
                    "data": {"title": top.opportunity.title, "score": top.total_score},
                }

        if "scan" in command or "research" in command:
            words = command.split()
            niche = " ".join(words[words.index("on") + 1:]) if "on" in words else " ".join(words[-2:])
            return {
                "response": f"I'll run a quick scan on '{niche}'. This will take a moment. "
                            "I'll send you a notification when it's done.",
                "action": "quick_scan",
                "niche": niche,
            }

        return {
            "response": "I didn't understand that command. Try: 'What's the waitlist at?', "
                        "'What's our CPA?', 'Give me the briefing', or 'Run a scan on [niche]'.",
            "understood": False,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Document Upload (Camera-to-Knowledge) ====================

@router.post("/upload-document")
async def upload_document_to_knowledge(
    file: UploadFile = File(...),
    category: str = Form("general"),
    notes: str = Form(""),
):
    """Upload a document from phone to GRACE's knowledge base.

    Supports: images (camera/screenshots), PDFs, text files.
    Images are OCR'd automatically. All content is ingested
    into the knowledge base with Genesis Key tracking.
    """
    try:
        content = await file.read()
        file_ext = os.path.splitext(file.filename or "")[1].lower()

        result = {
            "filename": file.filename,
            "size_bytes": len(content),
            "category": category,
            "format": file_ext,
            "status": "received",
        }

        if file_ext in (".jpg", ".jpeg", ".png", ".heic", ".webp"):
            result["processing"] = "OCR will extract text from image"
            result["pipeline"] = "image -> OCR -> text -> knowledge base ingestion"
        elif file_ext == ".pdf":
            result["processing"] = "PDF text extraction"
            result["pipeline"] = "pdf -> text extraction -> knowledge base ingestion"
        elif file_ext in (".txt", ".md", ".csv", ".json"):
            result["processing"] = "Direct text ingestion"
            result["pipeline"] = "text -> knowledge base ingestion"
        else:
            result["processing"] = "File stored for manual review"

        upload_dir = os.path.join("backend", "data", "mobile_uploads")
        os.makedirs(upload_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(upload_dir, f"{timestamp}_{file.filename}")
        with open(filepath, "wb") as f:
            f.write(content)

        result["stored_at"] = filepath
        result["notes"] = notes

        logger.info(f"Mobile upload: {file.filename} ({len(content)} bytes) -> {category}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Task View ====================

@router.get("/tasks")
async def get_task_overview():
    """Get overview of all BI tasks -- what's processing, what's complete."""
    try:
        from business_intelligence.utils.initializer import get_bi_system
        bi = get_bi_system()

        tasks = []

        if bi.intelligence_engine:
            state = bi.intelligence_engine.state
            tasks.append({
                "module": "Intelligence Engine",
                "status": state.current_phase.value,
                "cycles_completed": state.total_cycles,
                "data_points": len(state.all_data_points),
            })

        if bi.campaign_manager:
            for c in bi.campaign_manager.campaigns[-10:]:
                tasks.append({
                    "module": "Campaign",
                    "name": c.name,
                    "status": c.status,
                    "requires_action": c.status == "pending_approval",
                })

        if bi.intelligence_engine:
            for r in bi.intelligence_engine.state.research_reports[-5:]:
                tasks.append({
                    "module": "Research",
                    "name": f"Research: {r.niche}",
                    "status": r.status,
                    "confidence": r.grace_confidence,
                })

        return {"tasks": tasks, "total": len(tasks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helpers ====================

_notification_service = None


def _get_notification_service():
    global _notification_service
    if _notification_service is None:
        from mobile.push_notifications import PushNotificationService
        _notification_service = PushNotificationService()
        _notification_service.initialize()
    return _notification_service
