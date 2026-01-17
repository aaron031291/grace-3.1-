"""
Trigger Self-Healing System from Component Test Report

Reads the component test report and triggers the autonomous healing system
to fix all identified issues.
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from database.session import SessionLocal, initialize_session_factory
from database.connection import DatabaseConnection, DatabaseConfig, DatabaseType
from cognitive.autonomous_healing_system import (
    AutonomousHealingSystem,
    TrustLevel,
    AnomalyType
)
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType
from settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_test_report(report_path: Path) -> Dict[str, Any]:
    """Load the component test report."""
    if not report_path.exists():
        raise FileNotFoundError(f"Test report not found: {report_path}")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def categorize_issues(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize issues by type for targeted healing."""
    categorized = {
        "database_table_errors": [],
        "import_errors": [],
        "syntax_errors": [],
        "other_errors": []
    }
    
    for result in results:
        if result["status"] != "passed" and result.get("issues"):
            for issue in result["issues"]:
                issue_type = issue.get("type", "")
                message = issue.get("message", "").lower()
                
                if "table" in message and ("already defined" in message or "does not exist" in message):
                    categorized["database_table_errors"].append({
                        "component": result["component_name"],
                        "path": result["component_path"],
                        "issue": issue,
                        "result": result
                    })
                elif issue_type == "import_error":
                    categorized["import_errors"].append({
                        "component": result["component_name"],
                        "path": result["component_path"],
                        "issue": issue,
                        "result": result
                    })
                elif issue_type == "syntax_error":
                    categorized["syntax_errors"].append({
                        "component": result["component_name"],
                        "path": result["component_path"],
                        "issue": issue,
                        "result": result
                    })
                else:
                    categorized["other_errors"].append({
                        "component": result["component_name"],
                        "path": result["component_path"],
                        "issue": issue,
                        "result": result
                    })
    
    return categorized


def create_anomalies_from_issues(
    categorized_issues: Dict[str, List[Dict[str, Any]]],
    genesis_service
) -> List[Dict[str, Any]]:
    """Create anomaly objects from categorized issues."""
    anomalies = []
    
    # Database table errors
    if categorized_issues["database_table_errors"]:
        # Extract unique table names
        missing_tables = set()
        file_paths = []
        for item in categorized_issues["database_table_errors"]:
            message = item["issue"].get("message", "")
            file_path = item.get("path", "")
            if file_path:
                file_paths.append(file_path)
            # Try to extract table name
            if "table" in message.lower():
                import re
                # Look for table names in quotes or after 'table'
                matches = re.findall(r"table['\"]?\s*:?\s*['\"]?(\w+)['\"]?", message, re.IGNORECASE)
                if matches:
                    missing_tables.update(matches)
        
        if missing_tables or file_paths:
            # Create Genesis Keys for tracking
            evidence = []
            for item in categorized_issues["database_table_errors"][:10]:
                try:
                    key = genesis_service.create_key(
                        key_type=GenesisKeyType.ERROR,
                        what_description=f"Database table error in {item['component']}",
                        who_actor="component_tester",
                        where_location=item["path"],
                        why_reason=item["issue"].get("message", ""),
                        how_method="component_testing",
                        file_path=item["path"],
                        error_message=item["issue"].get("message", ""),
                        error_type="database_table_error",
                        context_data={
                            "component": item["component"],
                            "issue_type": item["issue"].get("type"),
                            "severity": item["issue"].get("severity")
                        }
                    )
                    evidence.append(key.key_id)
                except Exception as e:
                    logger.error(f"Failed to create Genesis Key: {e}")
            
            anomalies.append({
                "type": AnomalyType.DATA_INCONSISTENCY,
                "severity": "critical",
                "details": f"Database table errors detected: {len(categorized_issues['database_table_errors'])} components affected",
                "service": "database",
                "missing_tables": list(missing_tables),
                "file_paths": list(set(file_paths))[:20],  # Limit to 20 unique paths
                "error_message": "Table redefinition errors - SQLAlchemy metadata issue",
                "evidence": evidence[:10]
            })
    
    # Import errors
    if categorized_issues["import_errors"]:
        evidence = []
        for item in categorized_issues["import_errors"][:10]:
            try:
                key = genesis_service.create_key(
                    key_type=GenesisKeyType.ERROR,
                    what_description=f"Import error in {item['component']}",
                    who_actor="component_tester",
                    where_location=item["path"],
                    why_reason=item["issue"].get("message", ""),
                    how_method="component_testing",
                    file_path=item["path"],
                    error_message=item["issue"].get("message", ""),
                    error_type="import_error",
                    context_data={
                        "component": item["component"],
                        "issue_type": item["issue"].get("type"),
                        "severity": item["issue"].get("severity")
                    }
                )
                evidence.append(key.key_id)
            except Exception as e:
                logger.error(f"Failed to create Genesis Key: {e}")
        
        anomalies.append({
            "type": AnomalyType.ERROR_SPIKE,
            "severity": "high",
            "details": f"Import errors detected: {len(categorized_issues['import_errors'])} components affected",
            "evidence": evidence[:10]
        })
    
    # Syntax errors
    if categorized_issues["syntax_errors"]:
        evidence = []
        for item in categorized_issues["syntax_errors"][:10]:
            try:
                key = genesis_service.create_key(
                    key_type=GenesisKeyType.ERROR,
                    what_description=f"Syntax error in {item['component']}",
                    who_actor="component_tester",
                    where_location=item["path"],
                    why_reason=item["issue"].get("message", ""),
                    how_method="component_testing",
                    file_path=item["path"],
                    error_message=item["issue"].get("message", ""),
                    error_type="syntax_error",
                    context_data={
                        "component": item["component"],
                        "issue_type": item["issue"].get("type"),
                        "severity": item["issue"].get("severity"),
                        "line": item["issue"].get("line")
                    }
                )
                evidence.append(key.key_id)
            except Exception as e:
                logger.error(f"Failed to create Genesis Key: {e}")
        
        anomalies.append({
            "type": AnomalyType.DATA_INCONSISTENCY,
            "severity": "high",
            "details": f"Syntax errors detected: {len(categorized_issues['syntax_errors'])} components affected",
            "evidence": evidence[:10]
        })
    
    return anomalies


def trigger_healing(session: Session, report_path: Path, trust_level: TrustLevel = TrustLevel.MEDIUM_RISK_AUTO):
    """Trigger healing system to fix issues from test report."""
    logger.info(f"[HEALING-TRIGGER] Loading test report: {report_path}")
    
    # Load report
    report = load_test_report(report_path)
    
    logger.info(
        f"[HEALING-TRIGGER] Report loaded: "
        f"{report['summary']['total_components']} components, "
        f"{report['summary']['failed']} failed, "
        f"{report['summary']['errors']} errors, "
        f"{report['healing_summary']['total_issues_found']} issues found"
    )
    
    # Initialize services
    genesis_service = get_genesis_service()
    healing_system = AutonomousHealingSystem(
        session=session,
        trust_level=trust_level,
        enable_learning=True
    )
    
    # Categorize issues
    logger.info("[HEALING-TRIGGER] Categorizing issues...")
    categorized = categorize_issues(report["results"])
    
    logger.info(
        f"[HEALING-TRIGGER] Issues categorized: "
        f"Database: {len(categorized['database_table_errors'])}, "
        f"Import: {len(categorized['import_errors'])}, "
        f"Syntax: {len(categorized['syntax_errors'])}, "
        f"Other: {len(categorized['other_errors'])}"
    )
    
    # Create anomalies
    logger.info("[HEALING-TRIGGER] Creating anomalies from issues...")
    anomalies = create_anomalies_from_issues(categorized, genesis_service)
    
    logger.info(f"[HEALING-TRIGGER] Created {len(anomalies)} anomalies")
    
    # Trigger healing
    logger.info("[HEALING-TRIGGER] Triggering healing system...")
    
    healing_results = {
        "timestamp": datetime.utcnow().isoformat(),
        "anomalies_processed": len(anomalies),
        "healing_actions": []
    }
    
    for anomaly in anomalies:
        logger.info(f"[HEALING-TRIGGER] Processing anomaly: {anomaly['type'].value} - {anomaly['details']}")
        
        # Decide healing actions
        decisions = healing_system.decide_healing_actions([anomaly])
        
        if decisions:
            logger.info(f"[HEALING-TRIGGER] Decided {len(decisions)} healing actions")
            
            # Execute healing
            results = healing_system.execute_healing(decisions)
            
            healing_results["healing_actions"].append({
                "anomaly": anomaly,
                "decisions": decisions,
                "execution_results": results
            })
            
            logger.info(
                f"[HEALING-TRIGGER] Healing executed: "
                f"{len(results['executed'])} executed, "
                f"{len(results['awaiting_approval'])} awaiting approval, "
                f"{len(results['failed'])} failed"
            )
    
    # Run full monitoring cycle
    logger.info("[HEALING-TRIGGER] Running full monitoring cycle...")
    cycle_result = healing_system.run_monitoring_cycle()
    
    healing_results["monitoring_cycle"] = cycle_result
    
    logger.info(
        f"[HEALING-TRIGGER] Monitoring cycle complete: "
        f"Health: {cycle_result['health_status']}, "
        f"Anomalies: {cycle_result['anomalies_detected']}, "
        f"Actions executed: {cycle_result['actions_executed']}"
    )
    
    return healing_results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Trigger healing from component test report")
    parser.add_argument(
        "--report",
        type=str,
        default="backend/tests/component_test_report.json",
        help="Path to test report"
    )
    parser.add_argument(
        "--trust-level",
        type=int,
        default=3,
        help="Trust level for healing (0-9, default: 3)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for healing results"
    )
    
    args = parser.parse_args()
    
    # Initialize database
    db_type = DatabaseType(settings.DATABASE_TYPE) if settings else DatabaseType.SQLITE
    db_config = DatabaseConfig(
        db_type=db_type,
        host=settings.DATABASE_HOST if settings else None,
        port=settings.DATABASE_PORT if settings else None,
        username=settings.DATABASE_USER if settings else None,
        password=settings.DATABASE_PASSWORD if settings else None,
        database=settings.DATABASE_NAME if settings else "grace",
        database_path=settings.DATABASE_PATH if settings else None,
        echo=settings.DATABASE_ECHO if settings else False,
    )
    DatabaseConnection.initialize(db_config)
    initialize_session_factory()
    
    # Get session (import after initialization)
    from database.session import SessionLocal
    session = SessionLocal()
    
    try:
        # Trigger healing
        report_path = Path(args.report)
        results = trigger_healing(
            session=session,
            report_path=report_path,
            trust_level=TrustLevel(args.trust_level)
        )
        
        # Save results
        output_path = Path(args.output) if args.output else report_path.parent / "healing_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"[HEALING-TRIGGER] Healing results saved to: {output_path}")
        
        # Print summary
        print("\n" + "="*70)
        print("HEALING TRIGGER SUMMARY")
        print("="*70)
        print(f"Anomalies Processed: {results['anomalies_processed']}")
        print(f"Total Healing Actions: {len(results['healing_actions'])}")
        
        total_executed = sum(
            len(action['execution_results']['executed'])
            for action in results['healing_actions']
        )
        total_awaiting = sum(
            len(action['execution_results']['awaiting_approval'])
            for action in results['healing_actions']
        )
        total_failed = sum(
            len(action['execution_results']['failed'])
            for action in results['healing_actions']
        )
        
        print(f"Actions Executed: {total_executed}")
        print(f"Awaiting Approval: {total_awaiting}")
        print(f"Failed: {total_failed}")
        
        if results.get("monitoring_cycle"):
            cycle = results["monitoring_cycle"]
            print(f"\nMonitoring Cycle:")
            print(f"  Health Status: {cycle['health_status']}")
            print(f"  Anomalies Detected: {cycle['anomalies_detected']}")
            print(f"  Actions Executed: {cycle['actions_executed']}")
        
        print(f"\nResults saved to: {output_path}")
        print("="*70)
        
    except Exception as e:
        logger.error(f"[HEALING-TRIGGER] Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
