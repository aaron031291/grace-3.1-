"""
Get Stability Report - Simple API-based Report Generator

Uses the API endpoint to get stability report, or provides instructions.
"""
import sys
import requests
import json
from datetime import datetime
from pathlib import Path

def get_report_from_api(base_url="http://localhost:8000"):
    """Get stability report from API."""
    print("=" * 80)
    print("GRACE STABILITY PROOF SYSTEM - REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    try:
        # Check if server is running
        print("Checking if Grace server is running...")
        try:
            response = requests.get(f"{base_url}/health/live", timeout=2)
            if response.status_code != 200:
                raise Exception("Server not responding")
        except Exception as e:
            print(f"ERROR: Cannot connect to Grace server at {base_url}")
            print(f"   {e}")
            print()
            print("Please ensure Grace is running:")
            print("  1. Start Grace server: python backend/app.py")
            print("  2. Wait for server to start")
            print("  3. Run this script again")
            return None
        
        print("✅ Server is running")
        print()
        
        # Get stability proof
        print("Fetching stability proof...")
        response = requests.get(f"{base_url}/health/stability-proof", timeout=30)
        
        if response.status_code != 200:
            print(f"❌ ERROR: Failed to get stability proof: {response.status_code}")
            print(f"   {response.text}")
            return None
        
        data = response.json()
        
        if data.get("status") != "success":
            print(f"❌ ERROR: {data.get('message', 'Unknown error')}")
            return None
        
        proof_data = data.get("proof", {})
        
        # Generate report
        print("\n" + "=" * 80)
        print("STABILITY PROOF REPORT")
        print("=" * 80)
        
        # Overall Status
        print("\n📊 OVERALL STATUS")
        print("-" * 80)
        print(f"Proof ID: {proof_data.get('proof_id', 'N/A')}")
        print(f"Timestamp: {proof_data.get('timestamp', 'N/A')}")
        print(f"Stability Level: {proof_data.get('stability_level', 'N/A').upper()}")
        print(f"Overall Confidence: {proof_data.get('overall_confidence', 0):.2%}")
        print(f"System State Hash: {proof_data.get('system_state_hash', 'N/A')}")
        print(f"Verified: {'YES' if proof_data.get('is_verified') else 'NO'}")
        
        # Stability Assessment
        print("\n" + "=" * 80)
        print("STABILITY ASSESSMENT")
        print("=" * 80)
        
        stability_level = proof_data.get('stability_level', '')
        if stability_level == 'provably_stable':
            print("\n[OK] SYSTEM IS PROVABLY STABLE")
            print("   All components are operational and deterministic.")
            print("   Mathematical proof has been verified.")
            print("   System is in optimal state.")
        elif stability_level == 'stable':
            print("\n[OK] SYSTEM IS STABLE")
            print("   All components are operational.")
            print("   System is functioning normally.")
        elif stability_level == 'partially_stable':
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
        
        checks = proof_data.get('checks', [])
        stable_count = sum(1 for c in checks if c.get('is_stable', False))
        unstable_count = len(checks) - stable_count
        
        for i, check in enumerate(checks, 1):
            component = check.get('component', 'unknown')
            is_stable = check.get('is_stable', False)
            confidence = check.get('confidence', 0.0)
            
            status_icon = "[OK]" if is_stable else "[FAIL]"
            status_text = "STABLE" if is_stable else "UNSTABLE"
            
            print(f"\n{i}. {component.upper().replace('_', ' ')}")
            print(f"   Status: {status_icon} {status_text}")
            print(f"   Confidence: {confidence:.2%}")
            
            violations = check.get('violations', [])
            if violations:
                print(f"   [WARN] Violations:")
                for violation in violations:
                    print(f"     - {violation}")
            
            details = check.get('details', {})
            if details:
                print(f"   Details:")
                for key, value in details.items():
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=6)
                    print(f"     • {key}: {value}")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        print(f"\nTotal Components Checked: {len(checks)}")
        print(f"Stable Components: {stable_count} ({stable_count/len(checks)*100:.1f}%)")
        print(f"Unstable Components: {unstable_count} ({unstable_count/len(checks)*100:.1f}%)")
        print(f"Overall Confidence: {proof_data.get('overall_confidence', 0):.2%}")
        
        # Monitor Status
        print("\n" + "=" * 80)
        print("MONITOR STATUS")
        print("=" * 80)
        
        try:
            monitor_response = requests.get(f"{base_url}/health/stability-monitor/status", timeout=10)
            if monitor_response.status_code == 200:
                monitor_data = monitor_response.json().get('monitor', {})
                status = monitor_data.get('status', 'unknown')
                
                if status == 'running':
                    print("\n[OK] Real-Time Monitor: RUNNING")
                    print(f"   Total Checks: {monitor_data.get('total_checks', 0)}")
                    print(f"   Stable Count: {monitor_data.get('stable_count', 0)}")
                    print(f"   Unstable Count: {monitor_data.get('unstable_count', 0)}")
                    print(f"   Check Interval: {monitor_data.get('check_interval_seconds', 0)} seconds")
                    
                    if monitor_data.get('last_check_time'):
                        print(f"   Last Check: {monitor_data['last_check_time']}")
                    
                    if monitor_data.get('uptime_seconds'):
                        uptime_hours = monitor_data['uptime_seconds'] / 3600
                        print(f"   Uptime: {uptime_hours:.2f} hours")
                else:
                    print(f"\n⚠️  Real-Time Monitor: {status.upper()}")
            else:
                print("\n⚠️  Could not get monitor status")
        except Exception as e:
            print(f"\n⚠️  Could not get monitor status: {e}")
        
        # Recommendations
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        
        if stability_level == 'provably_stable':
            print("\n[OK] System is in optimal state. No action required.")
            print("   Continue monitoring for any changes.")
        elif stability_level == 'stable':
            print("\n[OK] System is stable. Continue normal operations.")
            print("   Monitor for any degradation.")
        elif stability_level == 'partially_stable':
            print("\n[WARN] Review unstable components:")
            for check in checks:
                if not check.get('is_stable', False):
                    violations = check.get('violations', [])
                    print(f"   - {check.get('component')}: {', '.join(violations) if violations else 'Check details'}")
            print("\n   Consider investigating root causes.")
        else:
            print("\n[FAIL] IMMEDIATE ACTION REQUIRED:")
            print("   Unstable components detected:")
            for check in checks:
                if not check.get('is_stable', False):
                    violations = check.get('violations', [])
                    print(f"   - {check.get('component')}: {', '.join(violations) if violations else 'Check details'}")
            print("\n   Investigate and resolve issues immediately.")
        
        # Export to JSON
        print("\n" + "=" * 80)
        print("EXPORT")
        print("=" * 80)
        
        report_file = Path(__file__).parent.parent / "stability_report.json"
        try:
            with open(report_file, 'w') as f:
                json.dump(proof_data, f, indent=2, default=str)
            print(f"\n[OK] Report exported to: {report_file}")
        except Exception as e:
            print(f"\n⚠️  Could not export report: {e}")
        
        print("\n" + "=" * 80)
        print("REPORT COMPLETE")
        print("=" * 80)
        print()
        
        return proof_data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Network error: {e}")
        print()
        print("Please ensure:")
        print("  1. Grace server is running")
        print("  2. Server is accessible at", base_url)
        print("  3. No firewall blocking the connection")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Grace Stability Report')
    parser.add_argument('--url', default='http://localhost:8000', 
                       help='Grace server URL (default: http://localhost:8000)')
    
    args = parser.parse_args()
    
    proof = get_report_from_api(args.url)
    
    if proof:
        stability_level = proof.get('stability_level', '')
        if stability_level in ['stable', 'provably_stable']:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Unstable
    else:
        sys.exit(2)  # Error
