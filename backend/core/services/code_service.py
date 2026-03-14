"""Code domain service Ã¢â‚¬â€ codebase, projects, code generation."""
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
            logger.warning("[CODE] Failed to load project metadata from %s: %s", PROJECTS_META, e)
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
        except PermissionError:
            logger.debug("[CODE] Permission denied reading %s", p)
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
        logger.debug("[CODE] Genesis tracking for file write skipped: %s", e)
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

def generate_code(prompt, project_folder="", use_pipeline=False):
    """
    Generate code via Qwen (latest coder model). Follows pipeline when use_pipeline=True:
    consensus design Ã¢â€ â€™ Qwen build Ã¢â€ â€™ compile/test Ã¢â€ â€™ self-heal. Otherwise uses Qwen coder only.
    """
    try:
        if use_pipeline:
            from cognitive.qwen_coding_net import generate_code as pipeline_generate
            return pipeline_generate(prompt, project_folder, use_pipeline=True)
        from llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("code")
        context = ""
        if project_folder:
            try:
                target = _safe(project_folder)
                files = []
                for f in target.rglob("*"):
                    if f.is_file() and f.suffix in (".py", ".js", ".ts", ".jsx", ".tsx"):
                        files.append(f.name)
                context = f"Project files: {', '.join(files[:20])}"
            except Exception as e:
                logger.debug("[CODE] Context loading for code gen skipped: %s", e)
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        import ast
        
        max_retries = 3
        for attempt in range(max_retries):
            response = client.generate(prompt=full_prompt, system_prompt="You are a precise code generator. Output only valid code.", max_tokens=4096)
            code = response if isinstance(response, str) else str(response)
            
            # Strip markdown ticks for AST validation
            clean_code = code.strip()
            if clean_code.startswith("```"):
                lines = clean_code.split("\n")
                if lines[0].startswith("```"): lines = lines[1:]
                if lines[-1].startswith("```"): lines = lines[:-1]
                clean_code = "\n".join(lines).strip()
                
            try:
                ast.parse(clean_code)
                is_valid = True
                break # It's valid, exit the retry loop
            except SyntaxError as syntax_err:
                logger.warning(f"Standard LLM generated invalid syntax (Attempt {attempt+1}/{max_retries}): {syntax_err}")
                full_prompt += f"\n\nERROR IN PREVIOUS OUTPUT:\n{syntax_err}\nFix the syntax error and return the full corrected code."
                is_valid = False
                
        return {"ok": is_valid, "code": code, "prompt": prompt}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def apply_code(path, content):
    return write_file(path, content)
