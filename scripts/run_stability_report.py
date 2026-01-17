"""
Run Stability Proof System and Generate Report

Executes the stability proof system and generates a comprehensive report.
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import json

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

# Set up environment
os.environ.setdefault('PYTHONPATH', str(backend_dir))

# Import with error handling
try:
    from database.session import initialize_session_factory, SessionLocal
except ImportError:
    # Try alternative path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from backend.database.session import initialize_session_factory, SessionLocal

# Import stability proof directly (avoiding cognitive engine imports)
try:
    # Import directly from the file to avoid __init__ issues
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "deterministic_stability_proof",
        backend_dir / "cognitive" / "deterministic_stability_proof.py"
    )
    stability_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stability_module)
    
    get_stability_prover = stability_module.get_stability_prover
    StabilityLevel = stability_module.StabilityLevel
    
    # Try to get monitor
    try:
        spec_monitor = importlib.util.spec_from_file_location(
            "realtime_stability_monitor",
            backend_dir / "cognitive" / "realtime_stability_monitor.py"
        )
        monitor_module = importlib.util.module_from_spec(spec_monitor)
        spec_monitor.loader.exec_module(monitor_module)
        get_stability_monitor = monitor_module.get_stability_monitor
    except Exception:
        get_stability_monitor = None
        
except Exception as e:
    print(f"ERROR: Could not import stability proof module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def generate_report():
    """Generate comprehensive stability report."""
    print("=" * 80)
    print("GRACE STABILITY PROOF SYSTEM - REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    # Initialize database
    print("Initializing database connection...")
    try:
        from database.config import DatabaseConfig
        from database.connection import DatabaseConnection
        
        db_config = DatabaseConfig()
        DatabaseConnection.initialize(db_config)
        SessionLocal = initialize_session_factory()  # This returns the sessionmaker
        session = SessionLocal()
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    try:
        # Get stability prover
        print("Creating stability prover...")
        prover = get_stability_prover(session=session)
        
        # Generate stability proof
        print("Generating stability proof...")
        print("-" * 80)
        proof = prover.prove_stability(include_proof=True)
        
        # Generate report
        print("\n" + "=" * 80)
        print("STABILITY PROOF REPORT")
        print("=" * 80)
        
        # Overall Status
        print("\n[STATUS] OVERALL STATUS")
        print("-" * 80)
        print(f"Proof ID: {proof.proof_id}")
        print(f"Timestamp: {proof.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Stability Level: {proof.stability_level.value.upper()}")
        print(f"Overall Confidence: {proof.overall_confidence:.2%}")
        print(f"System State Hash: {proof.system_state_hash}")
        print(f"Verified: {'YES' if proof.is_verified else 'NO'}")
        
        # Stability Level Indicator
        print("\n" + "=" * 80)
        print("STABILITY ASSESSMENT")
        print("=" * 80)
        
        if proof.stability_level == StabilityLevel.PROVABLY_STABLE:
            print("\n[OK] SYSTEM IS PROVABLY STABLE")
            print("   All components are operational and deterministic.")
            print("   Mathematical proof has been verified.")
            print("   System is in optimal state.")
        elif proof.stability_level == StabilityLevel.STABLE:
            print("\n[OK] SYSTEM IS STABLE")
            print("   All components are operational.")
            print("   System is functioning normally.")
        elif proof.stability_level == StabilityLevel.PARTIALLY_STABLE:
            print("\n[WARN] SYSTEM IS PARTIALLY STABLE")
            print("   Some components may have issues.")
            print("   Review component details below.")
        else:
            print("\n[FAIL] SYSTEM IS UNSTABLE")
            print("   Multiple components have issues.")
            print("   Immediate attention required.")
        
        # Component Details
        print("\n" + "=" * 80)
        print("COMPONENT STATUS")
        print("=" * 80)
        
        stable_count = 0
        unstable_count = 0
        
        for i, check in enumerate(proof.checks, 1):
            status_icon = "[OK]" if check.is_stable else "[FAIL]"
            status_text = "STABLE" if check.is_stable else "UNSTABLE"
            
            if check.is_stable:
                stable_count += 1
            else:
                unstable_count += 1
            
            print(f"\n{i}. {check.component.upper().replace('_', ' ')}")
            print(f"   Status: {status_icon} {status_text}")
            print(f"   Confidence: {check.confidence:.2%}")
            print(f"   Timestamp: {check.timestamp.strftime('%H:%M:%S UTC')}")
            
            if check.details:
                print(f"   Details:")
                for key, value in check.details.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=2)
                    print(f"     • {key}: {value}")
            
            if check.violations:
                print(f"   [WARN] Violations:")
                for violation in check.violations:
                    print(f"     - {violation}")
            
            if check.proof:
                print(f"   Proof:")
                print(f"     Theorem: {check.proof.theorem}")
                print(f"     Conclusion: {check.proof.conclusion}")
                print(f"     Verified: {'YES' if check.proof.verified else 'NO'}")
        
        # Summary Statistics
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        print(f"\nTotal Components Checked: {len(proof.checks)}")
        print(f"Stable Components: {stable_count} ({stable_count/len(proof.checks)*100:.1f}%)")
        print(f"Unstable Components: {unstable_count} ({unstable_count/len(proof.checks)*100:.1f}%)")
        print(f"Overall Confidence: {proof.overall_confidence:.2%}")
        
        # Mathematical Proof
        print("\n" + "=" * 80)
        print("MATHEMATICAL PROOF")
        print("=" * 80)
        
        math_proof = proof.mathematical_proof
        print(f"\nTheorem: {math_proof.theorem}")
        print(f"\nPremises:")
        for premise in math_proof.premises:
            print(f"  • {premise}")
        
        print(f"\nProof Steps:")
        for step in math_proof.steps:
            step_num = step.get('step', '?')
            desc = step.get('description', 'N/A')
            result = step.get('result', 'N/A')
            print(f"  Step {step_num}: {desc}")
            print(f"    Result: {result}")
        
        print(f"\nConclusion: {math_proof.conclusion}")
        print(f"Proof Type: {math_proof.proof_type}")
        print(f"Verified: {'YES' if math_proof.verified else 'NO'}")
        
        # Monitor Status (if available)
        print("\n" + "=" * 80)
        print("MONITOR STATUS")
        print("=" * 80)
        
        try:
            monitor = get_stability_monitor()
            monitor_status = monitor.get_current_status()
            
            if monitor_status.get('status') == 'running':
                print("\n[OK] Real-Time Monitor: RUNNING")
                print(f"   Total Checks: {monitor_status.get('total_checks', 0)}")
                print(f"   Stable Count: {monitor_status.get('stable_count', 0)}")
                print(f"   Unstable Count: {monitor_status.get('unstable_count', 0)}")
                print(f"   Check Interval: {monitor_status.get('check_interval_seconds', 0)} seconds")
                
                if monitor_status.get('last_check_time'):
                    print(f"   Last Check: {monitor_status['last_check_time']}")
                
                if monitor_status.get('uptime_seconds'):
                    uptime_hours = monitor_status['uptime_seconds'] / 3600
                    print(f"   Uptime: {uptime_hours:.2f} hours")
                
                if monitor_status.get('alerts_count', 0) > 0:
                    print(f"   [WARN] Active Alerts: {monitor_status['alerts_count']}")
            else:
                print(f"\n[WARN] Real-Time Monitor: {monitor_status.get('status', 'unknown').upper()}")
                print("   Monitor is not running. It will start automatically when Grace starts.")
        except Exception as e:
            print(f"\n[WARN] Could not get monitor status: {e}")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        
        if proof.stability_level == StabilityLevel.PROVABLY_STABLE:
            print("\n[OK] System is in optimal state. No action required.")
            print("   Continue monitoring for any changes.")
        elif proof.stability_level == StabilityLevel.STABLE:
            print("\n[OK] System is stable. Continue normal operations.")
            print("   Monitor for any degradation.")
        elif proof.stability_level == StabilityLevel.PARTIALLY_STABLE:
            print("\n[WARN] Review unstable components:")
            for check in proof.checks:
                if not check.is_stable:
                    print(f"   • {check.component}: {', '.join(check.violations) if check.violations else 'Check details'}")
            print("\n   Consider investigating root causes.")
        else:
            print("\n[FAIL] IMMEDIATE ACTION REQUIRED:")
            print("   Unstable components detected:")
            for check in proof.checks:
                if not check.is_stable:
                    print(f"   • {check.component}: {', '.join(check.violations) if check.violations else 'Check details'}")
            print("\n   Investigate and resolve issues immediately.")
        
        # Export to JSON (optional)
        print("\n" + "=" * 80)
        print("EXPORT")
        print("=" * 80)
        
        report_file = Path(__file__).parent.parent / "stability_report.json"
        try:
            with open(report_file, 'w') as f:
                json.dump(proof.to_dict(), f, indent=2, default=str)
            print(f"\n[OK] Report exported to: {report_file}")
        except Exception as e:
            print(f"\n[WARN] Could not export report: {e}")
        
        print("\n" + "=" * 80)
        print("REPORT COMPLETE")
        print("=" * 80)
        print()
        
        return proof
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        session.close()


if __name__ == "__main__":
    proof = generate_report()
    
    if proof:
        # Exit with appropriate code
        if proof.stability_level in [StabilityLevel.STABLE, StabilityLevel.PROVABLY_STABLE]:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Unstable
    else:
        sys.exit(2)  # Error
