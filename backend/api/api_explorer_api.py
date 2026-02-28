"""
API Explorer — Call any backend endpoint interactively from the frontend.

Eliminates all black boxes by letting users browse, call, and see
the response of every single endpoint in the system.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests as req
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/explorer", tags=["API Explorer"])


class ExplorerCallRequest(BaseModel):
    method: str  # GET, POST, PUT, DELETE
    path: str
    body: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, str]] = None


@router.post("/call")
async def call_endpoint(request: ExplorerCallRequest):
    """Call any backend endpoint and return the response. No black boxes."""
    url = f"http://localhost:8000{request.path}"

    if request.params:
        url += "?" + "&".join(f"{k}={v}" for k, v in request.params.items())

    headers = {"Content-Type": "application/json"}

    try:
        if request.method.upper() == "GET":
            resp = req.get(url, headers=headers, timeout=30)
        elif request.method.upper() == "POST":
            resp = req.post(url, headers=headers, json=request.body or {}, timeout=30)
        elif request.method.upper() == "PUT":
            resp = req.put(url, headers=headers, json=request.body or {}, timeout=30)
        elif request.method.upper() == "DELETE":
            resp = req.delete(url, headers=headers, timeout=30)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported method: {request.method}")

        try:
            data = resp.json()
        except Exception:
            data = resp.text[:5000]

        return {
            "status_code": resp.status_code,
            "response_time_ms": round(resp.elapsed.total_seconds() * 1000, 1),
            "data": data,
            "headers": dict(resp.headers),
        }
    except req.ConnectionError:
        return {"status_code": 0, "error": "Connection refused", "data": None}
    except req.Timeout:
        return {"status_code": 0, "error": "Timeout", "data": None}
    except Exception as e:
        return {"status_code": 0, "error": str(e), "data": None}


@router.get("/routes")
async def list_all_routes():
    """List every single route with full metadata for the explorer."""
    try:
        from app import app

        routes = []
        for route in app.routes:
            if not hasattr(route, "methods"):
                continue
            for method in route.methods:
                if method in ("HEAD", "OPTIONS"):
                    continue

                doc = ""
                if hasattr(route, "endpoint") and route.endpoint.__doc__:
                    doc = route.endpoint.__doc__.strip().split("\n")[0]

                params = []
                if "{" in route.path:
                    import re
                    params = re.findall(r'\{(\w+)\}', route.path)

                routes.append({
                    "method": method,
                    "path": route.path,
                    "name": getattr(route, "name", ""),
                    "description": doc,
                    "path_params": params,
                })

        routes.sort(key=lambda r: r["path"])
        return {"total": len(routes), "routes": routes}
    except Exception as e:
        return {"total": 0, "routes": [], "error": str(e)}
