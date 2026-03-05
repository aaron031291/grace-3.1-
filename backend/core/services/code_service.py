"""Code domain service — codebase, projects, code generation."""
from pathlib import Path
import json, logging

logger = logging.getLogger(__name__)
PROJECTS_META = Path(__file__).parent.parent.parent / "data" / "code_projects.json"

def _kb():
    from settings import settings
    return Path(settings.KNOWLEDGE_BASE_PATH)

def _safe(rel):
    kb = _kb()
    target = (kb / rel).resolve()
    if not str(target).startswith(str(kb.resolve())):
        raise ValueError("Path traversal blocked")
    return target

def _load_projects():
    PROJECTS_META.parent.mkdir(parents=True, exist_ok=True)
    if PROJECTS_META.exists():
        try: return json.loads(PROJECTS_META.read_text())
        except Exception as e:
            logger.warning(f"Failed to load projects metadata: {e}")
    return []

def _save_projects(data):
    PROJECTS_META.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_META.write_text(json.dumps(data, indent=2, default=str))

def list_projects():
    return {"projects": _load_projects()}

def project_tree(folder, max_depth=3):
    target = _safe(folder)
    target.mkdir(parents=True, exist_ok=True)
    kb = _kb()
    def _t(p, depth=0):
        r = {"path": str(p.relative_to(kb)), "name": p.name, "type": "directory", "children": []}
        if depth >= max_depth: return r
        try:
            for item in sorted(p.iterdir()):
                if item.name.startswith("."): continue
                if item.is_dir(): r["children"].append(_t(item, depth+1))
                else: r["children"].append({"path": str(item.relative_to(kb)), "name": item.name, "type": "file", "size": item.stat().st_size})
        except PermissionError: pass
        return r
    return _t(target)

def read_file(path):
    target = _safe(path)
    if not target.exists(): return {"error": "Not found"}
    return {"path": path, "content": target.read_text(errors="ignore")[:50000],
            "language": target.suffix.lstrip("."), "size": target.stat().st_size}

def write_file(path, content):
    target = _safe(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    try:
        from api._genesis_tracker import track
        track(key_type="code_change", what=f"File written: {path}",
              who="code_service", file_path=path, tags=["code", "write"])
    except Exception as e:
        logger.debug(f"Genesis tracking unavailable for code_change: {e}")
    return {"path": path, "saved": True}

def create_file(path, content=""):
    target = _safe(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": path, "created": True}

def delete_file(path):
    target = _safe(path)
    if not target.exists(): return {"error": "Not found"}
    target.unlink()
    return {"path": path, "deleted": True}

def generate_code(prompt, project_folder=""):
    try:
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client()
        context = ""
        if project_folder:
            try:
                target = _safe(project_folder)
                files = []
                for f in target.rglob("*"):
                    if f.is_file() and f.suffix in (".py", ".js", ".ts", ".jsx", ".tsx"):
                        files.append(f.name)
                context = f"Project files: {', '.join(files[:20])}"
            except Exception: pass

        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        response = client.generate(prompt=full_prompt, system_prompt="You are a code generator.", max_tokens=4096)
        return {"code": response if isinstance(response, str) else str(response), "prompt": prompt}
    except Exception as e:
        return {"error": str(e)}

def apply_code(path, content):
    return write_file(path, content)
