"""
System Specifications API

Provides endpoints for accessing GRACE's system specifications.
"""

from fastapi import APIRouter
from typing import Dict, Any

from system_specs import get_system_specs
from agent_reminder import get_agent_reminder, create_reminder_files

router = APIRouter(prefix="/system-specs", tags=["system-specs"])


@router.get("/")
async def get_specs() -> Dict[str, Any]:
    """
    Get GRACE system specifications.
    
    Returns:
        System specifications as dictionary
    """
    specs = get_system_specs()
    return specs.to_dict()


@router.get("/prompt")
async def get_specs_prompt() -> str:
    """
    Get system specifications as formatted prompt string.
    
    Returns:
        Formatted system specs for LLM prompts
    """
    specs = get_system_specs()
    return specs.to_prompt_string()


@router.get("/reminder")
async def get_reminder() -> str:
    """
    Get polite reminder message for external agents.
    
    Returns:
        Reminder message with system specs
    """
    reminder = get_agent_reminder()
    return reminder.get_reminder_message()


@router.post("/create-reminder-files")
async def create_reminders():
    """
    Create reminder files for external agents.
    
    Creates:
    - GRACE_SYSTEM_SPECS.txt in project root
    - backend/config/agent_reminder.json
    """
    create_reminder_files()
    return {"status": "success", "message": "Reminder files created"}
