"""
Clarity Framework API - Grace-Aligned Coding Agent Cognitive Framework

REST endpoints for the Clarity Framework that competes with
Claude, ChatGPT, and Gemini using template-first approach
with full Grace architecture integration.
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

bp = Blueprint('clarity', __name__, url_prefix='/api/clarity')


def get_framework():
    """Get the Clarity Framework instance."""
    from cognitive.clarity_framework import get_clarity_framework
    return get_clarity_framework()


@bp.route('/solve', methods=['POST'])
def solve_task():
    """
    Solve a coding task using the Clarity Framework.
    
    Uses Grace-aligned cognitive processing with:
    - OODA Loop (Observe, Orient, Decide, Act)
    - Genesis Key tracking
    - Oracle consultation
    - Template-first code generation
    - Multi-layer verification with anti-hallucination
    - Trust-scored autonomous execution
    
    Request body:
    {
        "description": "Write a function that...",
        "language": "python",
        "test_cases": ["assert func(1) == 2"],
        "function_name": "my_func"
    }
    
    Response:
    {
        "success": true,
        "code": "def my_func...",
        "llm_used": false,
        "template_used": "List Filter",
        "oracle_consulted": true,
        "trust_score": 0.92,
        "trust_gate": "autonomous",
        "genesis_keys": ["GK-abc123"],
        "verification": {...},
        "phase_times": {...}
    }
    """
    try:
        data = request.get_json() or {}
        
        description = data.get('description', '')
        if not description:
            return jsonify({
                "success": False,
                "error": "description is required"
            }), 400
        
        framework = get_framework()
        result = framework.solve(
            description=description,
            language=data.get('language', 'python'),
            test_cases=data.get('test_cases'),
            function_name=data.get('function_name')
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Solve error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/batch-solve', methods=['POST'])
def batch_solve():
    """
    Solve multiple coding tasks in parallel.
    
    Request body:
    {
        "tasks": [
            {"description": "...", "test_cases": [...]},
            {"description": "...", "test_cases": [...]}
        ],
        "parallel": true
    }
    
    Response includes summary with LLM independence rate.
    """
    try:
        data = request.get_json() or {}
        tasks = data.get('tasks', [])
        
        if not tasks:
            return jsonify({
                "success": False,
                "error": "tasks array is required"
            }), 400
        
        framework = get_framework()
        results = framework.batch_solve(
            tasks=tasks,
            parallel=data.get('parallel', True)
        )
        
        # Calculate summary
        total = len(results)
        successful = sum(1 for r in results if r.get('success'))
        template_solved = sum(1 for r in results if r.get('success') and not r.get('llm_used'))
        oracle_assisted = sum(1 for r in results if r.get('oracle_consulted'))
        
        return jsonify({
            "success": True,
            "results": results,
            "summary": {
                "total": total,
                "successful": successful,
                "success_rate": successful / total * 100 if total > 0 else 0,
                "template_solved": template_solved,
                "llm_independence_rate": template_solved / total * 100 if total > 0 else 0,
                "oracle_assisted": oracle_assisted,
                "oracle_contribution_rate": oracle_assisted / total * 100 if total > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Batch solve error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/kpi-dashboard', methods=['GET'])
def get_kpi_dashboard():
    """
    Get comprehensive KPI dashboard.
    
    Includes:
    - Template coverage rate
    - LLM independence rate
    - Verification pass rate
    - Trust score distribution
    - Grace integration status
    - Genesis key tracking
    - Oracle contribution metrics
    """
    try:
        framework = get_framework()
        dashboard = framework.get_kpi_dashboard()
        
        return jsonify({
            "success": True,
            "dashboard": dashboard
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] KPI dashboard error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/templates', methods=['GET'])
def list_templates():
    """
    List all available templates with statistics.
    """
    try:
        framework = get_framework()
        templates = []
        
        for tid, template in framework.template_compiler.templates.items():
            stats = framework.template_compiler.template_stats.get(tid, {})
            uses = stats.get("uses", 0)
            successes = stats.get("successes", 0)
            
            templates.append({
                "id": tid,
                "name": template.get("name", tid),
                "category": template.get("category", "unknown"),
                "keywords": template.get("pattern_keywords", []),
                "languages": template.get("languages", ["python"]),
                "base_success_rate": template.get("success_rate", 0.5),
                "actual_success_rate": successes / uses if uses > 0 else None,
                "uses": uses,
                "successes": successes,
                "failures": stats.get("failures", 0)
            })
        
        # Sort by uses (most used first)
        templates.sort(key=lambda t: t["uses"], reverse=True)
        
        return jsonify({
            "success": True,
            "templates": templates,
            "total": len(templates),
            "categories": list(set(t["category"] for t in templates))
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Templates error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/templates/<template_id>', methods=['GET'])
def get_template(template_id: str):
    """
    Get details of a specific template.
    """
    try:
        framework = get_framework()
        template = framework.template_compiler.templates.get(template_id)
        
        if not template:
            return jsonify({
                "success": False,
                "error": f"Template {template_id} not found"
            }), 404
        
        stats = framework.template_compiler.template_stats.get(template_id, {})
        
        return jsonify({
            "success": True,
            "template": {
                "id": template_id,
                "name": template.get("name", template_id),
                "category": template.get("category", "unknown"),
                "keywords": template.get("pattern_keywords", []),
                "languages": template.get("languages", ["python"]),
                "code_template": template.get("template", ""),
                "required_params": template.get("params", []),
                "base_success_rate": template.get("success_rate", 0.5),
                "stats": stats
            }
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Get template error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/grace-status', methods=['GET'])
def grace_integration_status():
    """
    Get Grace architecture integration status.
    
    Shows status of:
    - Genesis Key tracking
    - Unified Oracle Hub
    - Memory Mesh
    - Trust Scorer
    - Hallucination Guard
    """
    try:
        framework = get_framework()
        
        return jsonify({
            "success": True,
            "grace_integration": {
                "genesis_tracking": {
                    "enabled": framework.genesis_tracker.genesis_service is not None,
                    "total_keys_created": framework.kpi.total_genesis_keys
                },
                "unified_oracle": {
                    "connected": framework.oracle_liaison.oracle_hub is not None,
                    "patterns_loaded": len(framework.oracle_liaison.oracle_patterns) if hasattr(framework.oracle_liaison, 'oracle_patterns') else 0
                },
                "memory_mesh": {
                    "active": framework.memory_learner.memory_mesh is not None
                },
                "trust_scorer": {
                    "enhanced": framework.trust_manager.trust_scorer is not None,
                    "thresholds": {
                        "autonomous": framework.trust_manager.auto_threshold,
                        "supervised": framework.trust_manager.supervised_threshold
                    }
                },
                "verification": {
                    "hallucination_guard": framework.verification_gate.hallucination_guard is not None
                }
            },
            "framework_config": {
                "llm_fallback_enabled": framework.enable_llm_fallback,
                "max_parallel_agents": framework.max_parallel_agents,
                "template_count": len(framework.template_compiler.templates)
            }
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Grace status error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/memory/stats', methods=['GET'])
def get_memory_stats():
    """
    Get Memory Mesh learning statistics.
    
    Shows what the Clarity Framework has learned from past tasks.
    """
    try:
        framework = get_framework()
        stats = framework.memory_learner.get_learning_stats()
        
        return jsonify({
            "success": True,
            "memory_stats": stats
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Memory stats error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/memory/gaps', methods=['GET'])
def get_knowledge_gaps():
    """
    Get identified knowledge gaps.
    
    Shows templates/patterns that need improvement.
    """
    try:
        framework = get_framework()
        gaps = framework.memory_learner.identify_knowledge_gaps()
        
        return jsonify({
            "success": True,
            "gaps": gaps,
            "total": len(gaps),
            "recommendations": [
                {
                    "gap": gap,
                    "action": "Consider adding more templates or improving existing ones for this pattern"
                }
                for gap in gaps[:5]
            ]
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Knowledge gaps error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/memory/history', methods=['GET'])
def get_learning_history():
    """
    Get recent learning history.
    
    Shows what tasks have been solved and their outcomes.
    """
    try:
        framework = get_framework()
        limit = request.args.get('limit', 20, type=int)
        
        # Get recent entries from file-based memory
        history = framework.memory_learner.file_based_memory[-limit:][::-1]
        
        return jsonify({
            "success": True,
            "history": history,
            "total_entries": len(framework.memory_learner.file_based_memory)
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Learning history error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/memory/template/<template_id>', methods=['GET'])
def get_template_history(template_id: str):
    """
    Get learning history for a specific template.
    """
    try:
        framework = get_framework()
        history = framework.memory_learner.get_template_success_history(template_id)
        
        return jsonify({
            "success": True,
            "template_history": history
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Template history error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/memory/feedback', methods=['POST'])
def submit_feedback():
    """
    Submit feedback on a past task outcome.
    
    Used to improve learning when we discover if a decision was correct.
    
    Request body:
    {
        "learning_id": "abc123",
        "was_correct": true
    }
    """
    try:
        data = request.get_json() or {}
        learning_id = data.get('learning_id')
        was_correct = data.get('was_correct')
        
        if not learning_id or was_correct is None:
            return jsonify({
                "success": False,
                "error": "learning_id and was_correct are required"
            }), 400
        
        framework = get_framework()
        framework.memory_learner.feedback_update(learning_id, was_correct)
        
        return jsonify({
            "success": True,
            "message": f"Feedback recorded for {learning_id}"
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Feedback error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/compare', methods=['POST'])
def compare_approaches():
    """
    Compare template-only vs LLM-fallback approaches for a task.
    
    Useful for benchmarking and understanding when templates
    can compete with LLMs.
    
    Request body:
    {
        "description": "Write a function that...",
        "test_cases": ["assert func(1) == 2"]
    }
    """
    try:
        data = request.get_json() or {}
        description = data.get('description', '')
        test_cases = data.get('test_cases', [])
        
        if not description:
            return jsonify({
                "success": False,
                "error": "description is required"
            }), 400
        
        from cognitive.clarity_framework import ClarityFramework
        
        # Template-only attempt
        template_framework = ClarityFramework(
            enable_llm_fallback=False
        )
        template_result = template_framework.solve(
            description=description,
            test_cases=test_cases
        )
        
        # With LLM fallback
        llm_framework = ClarityFramework(
            enable_llm_fallback=True
        )
        llm_result = llm_framework.solve(
            description=description,
            test_cases=test_cases
        )
        
        return jsonify({
            "success": True,
            "comparison": {
                "template_only": {
                    "success": template_result.get("success"),
                    "template_used": template_result.get("template_used"),
                    "trust_score": template_result.get("trust_score"),
                    "code": template_result.get("code")
                },
                "with_llm_fallback": {
                    "success": llm_result.get("success"),
                    "llm_used": llm_result.get("llm_used"),
                    "template_used": llm_result.get("template_used"),
                    "trust_score": llm_result.get("trust_score"),
                    "code": llm_result.get("code")
                },
                "analysis": {
                    "template_sufficient": template_result.get("success"),
                    "llm_needed": not template_result.get("success") and llm_result.get("success"),
                    "both_failed": not template_result.get("success") and not llm_result.get("success")
                }
            }
        })
        
    except Exception as e:
        logger.error(f"[CLARITY-API] Compare error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
