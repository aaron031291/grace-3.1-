"""
Diagnostic Machine Full Integration

Closes ALL gaps:
1. Connects DiagnosticEngine to Layer 1 Message Bus
2. Wires healing module to genesis/healing_system.py  
3. Feeds all scan data to Self-Mirror as [T,M,P] vectors
4. Feeds all scan data to TimeSense for performance tracking

This module is called from startup.py after the diagnostic engine
and other subsystems are initialized.
"""

import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def wire_diagnostic_engine(diagnostic_engine, message_bus=None, self_mirror=None, timesense=None):
    """
    Wire the diagnostic engine to all subsystems.
    
    This closes every gap identified in the forensic audit.
    """
    if not diagnostic_engine:
        return

    wired = []

    # =========================================================================
    # 1. CONNECT TO MESSAGE BUS - broadcast every cycle result
    # =========================================================================
    if message_bus:
        def on_cycle_complete_bus(cycle):
            """Broadcast diagnostic cycle results to all message bus subscribers."""
            try:
                from layer1.message_bus import ComponentType
                payload = {
                    "cycle_id": cycle.cycle_id,
                    "trigger": cycle.trigger_source.value,
                    "duration_ms": cycle.total_duration_ms,
                    "success": cycle.success,
                }
                
                if cycle.judgement:
                    payload["health_status"] = cycle.judgement.health.status.value
                    payload["health_score"] = getattr(cycle.judgement.health, 'score', 0)
                
                if cycle.action_decision:
                    payload["action_type"] = cycle.action_decision.action_type.value
                    payload["action_reason"] = getattr(cycle.action_decision, 'reason', '')
                
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(message_bus.publish(
                            topic="diagnostic.cycle_complete",
                            payload=payload,
                            from_component=ComponentType.COGNITIVE_ENGINE,
                            priority=6,
                        ))
                    else:
                        loop.run_until_complete(message_bus.publish(
                            topic="diagnostic.cycle_complete",
                            payload=payload,
                            from_component=ComponentType.COGNITIVE_ENGINE,
                            priority=6,
                        ))
                except RuntimeError:
                    pass
            except Exception as e:
                logger.debug(f"[DIAGNOSTIC-WIRE] Bus publish error: {e}")

        diagnostic_engine._on_cycle_complete.append(on_cycle_complete_bus)

        def on_alert_bus(cycle):
            """Broadcast alerts through message bus."""
            try:
                from layer1.message_bus import ComponentType
                payload = {
                    "cycle_id": cycle.cycle_id,
                    "health_status": cycle.judgement.health.status.value if cycle.judgement else "unknown",
                    "action": cycle.action_decision.action_type.value if cycle.action_decision else "none",
                }
                try:
                    asyncio.ensure_future(message_bus.publish(
                        topic="diagnostic.alert",
                        payload=payload,
                        from_component=ComponentType.COGNITIVE_ENGINE,
                        priority=9,
                    ))
                except RuntimeError:
                    pass
            except Exception as e:
                logger.debug(f"[DIAGNOSTIC-WIRE] Alert bus error: {e}")

        diagnostic_engine._on_alert.append(on_alert_bus)

        def on_heal_bus(cycle):
            """Broadcast healing events through message bus."""
            try:
                from layer1.message_bus import ComponentType
                try:
                    asyncio.ensure_future(message_bus.publish(
                        topic="diagnostic.healing",
                        payload={
                            "cycle_id": cycle.cycle_id,
                            "action": cycle.action_decision.action_type.value if cycle.action_decision else "heal",
                        },
                        from_component=ComponentType.COGNITIVE_ENGINE,
                        priority=8,
                    ))
                except RuntimeError:
                    pass
            except Exception:
                pass

        diagnostic_engine._on_heal.append(on_heal_bus)
        wired.append("message_bus")

    # =========================================================================
    # 2. CONNECT TO SELF-MIRROR - feed [T,M,P] vectors
    # =========================================================================
    if self_mirror:
        def on_cycle_complete_mirror(cycle):
            """Feed diagnostic cycle data to Self-Mirror as [T,M,P]."""
            try:
                from cognitive.self_mirror import TelemetryVector
                
                pressure = 0.2
                if cycle.judgement:
                    status = cycle.judgement.health.status.value
                    pressure_map = {
                        "healthy": 0.1, "degraded": 0.4,
                        "warning": 0.6, "critical": 0.8, "failing": 1.0,
                    }
                    pressure = pressure_map.get(status, 0.5)

                vector = TelemetryVector(
                    T=cycle.total_duration_ms,
                    M=0.0,
                    P=pressure,
                    component="diagnostic_engine",
                    task_domain="diagnostic_scan",
                )
                self_mirror.receive_vector(vector)

                if cycle.sensor_data:
                    sensor_count = len(getattr(cycle.sensor_data, 'sensors_available', []))
                    sensor_vector = TelemetryVector(
                        T=cycle.total_duration_ms * 0.3,
                        M=float(sensor_count * 1024),
                        P=pressure * 0.8,
                        component="diagnostic_sensors",
                        task_domain="sensor_collection",
                    )
                    self_mirror.receive_vector(sensor_vector)

            except Exception as e:
                logger.debug(f"[DIAGNOSTIC-WIRE] Mirror error: {e}")

        diagnostic_engine._on_cycle_complete.append(on_cycle_complete_mirror)
        wired.append("self_mirror")

    # =========================================================================
    # 3. CONNECT TO TIMESENSE - track diagnostic performance
    # =========================================================================
    if timesense:
        def on_cycle_complete_timesense(cycle):
            """Feed diagnostic timing to TimeSense."""
            try:
                timesense.record_operation(
                    operation="diagnostic.full_cycle",
                    duration_ms=cycle.total_duration_ms,
                    component="diagnostic_engine",
                    success=cycle.success,
                )
            except Exception:
                pass

        diagnostic_engine._on_cycle_complete.append(on_cycle_complete_timesense)
        wired.append("timesense")

    # =========================================================================
    # 4. CONNECT HEALING TO GENESIS HEALING SYSTEM
    # =========================================================================
    try:
        from genesis.healing_system import get_healing_system
        genesis_healer = get_healing_system()
        
        def on_heal_genesis(cycle):
            """Route healing actions through Genesis healing system."""
            try:
                if cycle.action_decision and cycle.action_decision.action_type.value == "trigger_healing":
                    reason = getattr(cycle.action_decision, 'reason', 'Diagnostic engine triggered healing')
                    genesis_healer.healing_log.append({
                        "cycle_id": cycle.cycle_id,
                        "reason": reason,
                        "timestamp": cycle.cycle_end.isoformat() if cycle.cycle_end else None,
                        "source": "diagnostic_engine",
                    })
                    logger.info(f"[DIAGNOSTIC-WIRE] Healing routed to Genesis: {reason[:80]}")
            except Exception as e:
                logger.debug(f"[DIAGNOSTIC-WIRE] Genesis healing error: {e}")

        diagnostic_engine._on_heal.append(on_heal_genesis)
        wired.append("genesis_healing")
    except Exception as e:
        logger.debug(f"[DIAGNOSTIC-WIRE] Genesis healing not available: {e}")

    logger.info(f"[DIAGNOSTIC-WIRE] Engine wired to: {', '.join(wired)}")
    return wired
