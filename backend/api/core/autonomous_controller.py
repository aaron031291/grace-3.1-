"""
Autonomous Controller — unified entry point for the Ouroboros loop
and consensus auto-fixer.

Replaces:
  - api/autonomous_loop_api.py
  - api/consensus_fixer_api.py
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/autonomous", tags=["Autonomous Controller"])


# Re-export from autonomous_loop_api (all endpoints preserved)
from api.autonomous_loop_api import (
    loop_status, start_loop, stop_loop, run_single_cycle, get_loop_log
)

router.add_api_route("/status", loop_status, methods=["GET"])
router.add_api_route("/start", start_loop, methods=["POST"])
router.add_api_route("/stop", stop_loop, methods=["POST"])
router.add_api_route("/cycle", run_single_cycle, methods=["POST"])
router.add_api_route("/log", get_loop_log, methods=["GET"])


# Re-export from consensus_fixer_api
from api.consensus_fixer_api import (
    scan_all_problems, consensus_fix_all, consensus_fix_one
)

router.add_api_route("/scan", scan_all_problems, methods=["POST"])
router.add_api_route("/fix-all", consensus_fix_all, methods=["POST"])
router.add_api_route("/fix-one", consensus_fix_one, methods=["POST"])
