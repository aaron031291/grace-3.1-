"""
File Generator — Grace creates documents, PDFs, code files, any format.

When user says "generate me a report", "create a PDF", "build a document",
Grace writes the content and saves it as the requested format.

Supports: PDF, TXT, MD, JSON, CSV, HTML, PY, JS, TS, YAML, any text format.
Connected to: Kimi/Opus for content, Librarian for placement, Genesis for tracking.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_kb():
    try:
        from settings import settings
        return Path(settings.KNOWLEDGE_BASE_PATH)
    except Exception:
        return Path("knowledge_base")


class FileGenerator:
    """Generate any file type from a prompt. Grace creates documents."""

    def generate(self, prompt: str, filename: str, folder: str = "",
                 file_type: str = "auto", use_kimi: bool = True) -> Dict[str, Any]:
        """
        Generate a file from a prompt.
        Grace writes the content and saves it.
        """
        # Auto-detect file type from filename
        if file_type == "auto":
            ext = Path(filename).suffix.lower()
            type_map = {
                '.pdf': 'pdf', '.txt': 'txt', '.md': 'markdown',
                '.json': 'json', '.csv': 'csv', '.html': 'html',
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.jsx': 'react', '.tsx': 'react',
                '.yaml': 'yaml', '.yml': 'yaml',
                '.css': 'css', '.sql': 'sql',
                '.sh': 'bash', '.xml': 'xml',
            }
            file_type = type_map.get(ext, 'txt')

        # Generate content via LLM
        content = self._generate_content(prompt, filename, file_type, use_kimi)
        if not content:
            return {"success": False, "error": "Failed to generate content"}

        # Save the file
        kb = _get_kb()
        target_dir = kb / folder if folder else kb
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / filename
        
        if file_type == 'pdf':
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                c = canvas.Canvas(str(file_path), pagesize=letter)
                y = 750
                for line in content.split('\n'):
                    if y < 50:
                        c.showPage()
                        y = 750
                    c.drawString(72, y, line[:90])
                    y -= 14
                c.save()
            except ImportError:
                pdf_content = self._format_as_pdf_text(content, filename)
                file_path = file_path.with_suffix('.pdf.txt')
                file_path.write_text(pdf_content, encoding='utf-8')
        else:
            file_path.write_text(content, encoding='utf-8')

        result = {
            "success": True,
            "filename": file_path.name,
            "path": str(file_path.relative_to(kb)),
            "folder": folder,
            "file_type": file_type,
            "size": file_path.stat().st_size,
            "content_preview": content[:500],
        }

        # Register in docs library
        try:
            from api.docs_library_api import register_document
            register_document(
                filename=file_path.name, file_path=str(file_path),
                file_size=file_path.stat().st_size, source="file_generator",
                upload_method="ai_generated", directory=folder,
            )
        except Exception:
            pass

        # Librarian organise
        try:
            from cognitive.librarian_autonomous import get_autonomous_librarian
            get_autonomous_librarian().organise_file(str(file_path.relative_to(kb)))
        except Exception:
            pass

        # Ingest into Magma
        try:
            from cognitive.magma_bridge import ingest
            ingest(f"Generated {file_type}: {filename}\n{content[:1000]}", source="file_generator")
        except Exception:
            pass

        # Genesis track
        try:
            from api._genesis_tracker import track
            track(key_type="file_op",
                  what=f"Generated file: {filename} ({file_type})",
                  where=str(file_path), file_path=str(file_path),
                  input_data={"prompt": prompt[:200]},
                  output_data={"size": result["size"], "type": file_type},
                  tags=["file_generator", file_type, "ai_generated"])
        except Exception:
            pass

        return result

    def _generate_content(self, prompt: str, filename: str, file_type: str, 
                          use_kimi: bool) -> Optional[str]:
        """Generate the file content using LLM."""
        format_instructions = {
            'pdf': "Generate a well-structured document with clear sections, headings, and professional formatting. Use markdown-style headers (# ## ###).",
            'txt': "Generate plain text content. Clear, readable, well-organized.",
            'markdown': "Generate well-formatted markdown with headers, lists, code blocks where appropriate.",
            'json': "Generate valid JSON. Use proper indentation and structure.",
            'csv': "Generate CSV with header row and data rows. Use commas as delimiters.",
            'html': "Generate complete, valid HTML with proper structure, head, body, and styling.",
            'python': "Generate clean, production-quality Python code with docstrings and type hints.",
            'javascript': "Generate clean JavaScript/Node.js code with proper error handling.",
            'typescript': "Generate TypeScript code with proper types and interfaces.",
            'react': "Generate a React component with proper hooks and JSX.",
            'yaml': "Generate valid YAML configuration.",
            'css': "Generate clean CSS with proper selectors and responsive design.",
            'sql': "Generate SQL with proper syntax and comments.",
            'bash': "Generate a bash script with proper error handling and comments.",
            'xml': "Generate well-formed XML with proper nesting.",
        }

        instruction = format_instructions.get(file_type, "Generate the requested content.")

        full_prompt = (
            f"Create a file called '{filename}' with the following requirements:\n\n"
            f"{prompt}\n\n"
            f"Format: {instruction}\n"
            f"Output ONLY the file content — no explanations, no markdown code fences."
        )

        try:
            if use_kimi:
                from llm_orchestrator.factory import get_kimi_client
                client = get_kimi_client()
            else:
                from llm_orchestrator.factory import get_llm_for_task
                client = get_llm_for_task("code" if file_type in ('python', 'javascript', 'typescript', 'react', 'css', 'html', 'sql', 'bash') else "reason")

            return client.chat(
                messages=[
                    {"role": "system", "content": f"You are generating a {file_type} file. Output only the file content."},
                    {"role": "user", "content": full_prompt},
                ],
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return None

    def _format_as_pdf_text(self, content: str, title: str) -> str:
        """Format content as a structured text document (PDF-style)."""
        lines = [
            "=" * 60,
            f"  {title.upper()}",
            f"  Generated by Grace AI — {datetime.utcnow().strftime('%B %d, %Y')}",
            "=" * 60,
            "",
            content,
            "",
            "=" * 60,
            f"  Document generated autonomously by Grace AI",
            f"  Timestamp: {datetime.utcnow().isoformat()}",
            "=" * 60,
        ]
        return "\n".join(lines)


_generator = None

def get_file_generator() -> FileGenerator:
    global _generator
    if _generator is None:
        _generator = FileGenerator()
    return _generator
