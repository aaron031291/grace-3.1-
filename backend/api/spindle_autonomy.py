import time
import logging

try:
    from prometheus_client import Counter, Gauge
    SPINDLE_AUTONOMY_RATIO = Gauge('spindle_autonomy_ratio', 'Ratio of autonomous decisions vs human escalations')
    EVENT_BUS_LAG_MS = Gauge('event_bus_lag_ms', 'Event bus lag in ms')
    WEBSOCKET_UPTIME = Gauge('websocket_uptime_seconds', 'Websocket uptime in seconds')
    AUTONOMOUS_ACTIONS = Counter('spindle_autonomous_actions_total', 'Total autonomous actions')
    ESCALATED_ACTIONS = Counter('spindle_escalated_actions_total', 'Total human escalations directly from Spindle')
except ImportError:
    SPINDLE_AUTONOMY_RATIO = None
    EVENT_BUS_LAG_MS = None
    WEBSOCKET_UPTIME = None
    AUTONOMOUS_ACTIONS = None
    ESCALATED_ACTIONS = None

logger = logging.getLogger(__name__)

def update_autonomy_metrics(was_autonomous: bool):
    if AUTONOMOUS_ACTIONS and ESCALATED_ACTIONS and SPINDLE_AUTONOMY_RATIO:
        if was_autonomous:
            AUTONOMOUS_ACTIONS.inc()
        else:
            ESCALATED_ACTIONS.inc()
        
        # Simple ratio calculation assuming we want a gauge of recent ratio...
        # Prometheus usually does this via rate() in the query, but we can set a gauge for simplicity
        total = AUTONOMOUS_ACTIONS._value.get() + ESCALATED_ACTIONS._value.get()
        if total > 0:
            SPINDLE_AUTONOMY_RATIO.set(AUTONOMOUS_ACTIONS._value.get() / total)

def autonomy_gate(event: dict, trust_score: float) -> dict:
    """
    Deterministic gate to bypass FLAG_FOR_HUMAN when confidence is sufficiently high.
    Implements Grace's Rule-8 from consensus.
    """
    if trust_score < 0.60:
        autonomy = False
        fallback = "escalate"
    elif 0.60 <= trust_score < 0.75:
        autonomy = True
        fallback = "safe_mode"
    else:
        autonomy = True
        fallback = "autonomous"
        
    update_autonomy_metrics(was_autonomous=autonomy)
    
    return {
        "autonomy": autonomy,
        "confidence": trust_score,
        "fallback": fallback
    }
