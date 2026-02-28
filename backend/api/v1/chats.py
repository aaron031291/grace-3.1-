"""v1/chats — Chat, world model, cognitive, MCP"""
from fastapi import APIRouter, Request
from typing import Optional, Dict, Any
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/chats", tags=["v1 Chats"])


class ChatMessage(BaseModel):
    message: str
    chat_id: Optional[str] = None
    folder_path: Optional[str] = None
    use_kimi: bool = False
    include_system_state: bool = False


@router.get("")
async def list_chats(limit: int = 50, folder_path: str = ""):
    from app import app
    import requests as req
    params = f"?limit={limit}"
    if folder_path:
        params += f"&folder_path={folder_path}"
    r = req.get(f"http://localhost:8000/chats{params}", timeout=10)
    return r.json() if r.ok else {"chats": []}


@router.post("")
async def create_chat(title: str = "New Chat", folder_path: str = ""):
    import requests as req
    r = req.post("http://localhost:8000/chats", json={"title": title, "folder_path": folder_path}, timeout=10)
    return r.json() if r.ok else {}


@router.get("/{chat_id}")
async def get_chat(chat_id: str):
    import requests as req
    r = req.get(f"http://localhost:8000/chats/{chat_id}", timeout=10)
    return r.json() if r.ok else {}


@router.get("/{chat_id}/messages")
async def get_messages(chat_id: str):
    import requests as req
    r = req.get(f"http://localhost:8000/chats/{chat_id}/messages", timeout=10)
    return r.json() if r.ok else {"messages": []}


@router.post("/{chat_id}/prompt")
async def send_prompt(chat_id: str, request: ChatMessage):
    import requests as req
    r = req.post(f"http://localhost:8000/chats/{chat_id}/prompt",
                 json={"messages": [{"role": "user", "content": request.message}]}, timeout=60)
    return r.json() if r.ok else {}


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str):
    import requests as req
    r = req.delete(f"http://localhost:8000/chats/{chat_id}", timeout=10)
    return r.json() if r.ok else {}


@router.get("/world-model/state")
async def world_model_state():
    import requests as req
    r = req.get("http://localhost:8000/api/world-model/state", timeout=10)
    return r.json() if r.ok else {}


@router.post("/world-model/chat")
async def world_model_chat(request: ChatMessage):
    import requests as req
    r = req.post("http://localhost:8000/api/world-model/chat",
                 json={"query": request.message, "include_system_state": request.include_system_state,
                       "provider": "kimi" if request.use_kimi else None}, timeout=60)
    return r.json() if r.ok else {}


@router.get("/world-model/subsystems")
async def world_model_subsystems():
    import requests as req
    r = req.get("http://localhost:8000/api/world-model/subsystems", timeout=10)
    return r.json() if r.ok else {}
