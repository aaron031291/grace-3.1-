import os
import ast
import uuid
import logging
from sqlalchemy.orm import Session
from database.models.braille_node import BrailleSandboxNode

logger = logging.getLogger(__name__)

class BrailleIngestor:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.ignored_dirs = {"__pycache__", ".venv", "venv", "node_modules", ".git", ".fix_backups"}
        self.sequence_counter = {
            "OP": 1, "SE": 1, "AI": 1, "ML": 1, "DL": 1, 
            "DS": 1, "SR": 1, "GR": 1, "HO": 1, "LN": 1, 
            "CG": 1, "GV": 1, "OR": 1
        }

    def determine_category_and_loop(self, file_path: str, content: str):
        """
        Infers the best Braille specification category and loop assignment 
        based on the file path and content.
        """
        if "cognitive" in file_path or "brain" in file_path:
            return "CG", "COGNITION", "●●●●●● 1mm ○"
        elif "self_healing" in file_path or "error" in file_path or "healing" in file_path:
            return "HO", "HOMEOSTASIS", "●●●●●● 1mm □"
        elif "learning" in file_path or "knowledge" in file_path:
            return "LN", "LEARNING", "●●●●●● 2mm □"
        elif "governance" in file_path or "trust" in file_path:
            return "GV", "GOVERNANCE", "●●●●●● 3mm △"
        elif "orchestrator" in file_path or "tasks" in file_path or "agent" in file_path:
            return "OR", "ORCHESTRATION", "●●●●●● 3mm □"
        else:
            return "SE", "ORCHESTRATION", "●●●●●● 1mm □△" # Default software engineering fallback

    def _generate_genesis_key(self, category: str):
        count = self.sequence_counter.get(category, 1)
        self.sequence_counter[category] = count + 1
        return f"GRACE-{category}-{count:03d}"

    def run_ingestion(self, root_dir: str):
        logger.info(f"Starting Braille Sandbox ingestion from {root_dir}")
        nodes_created = 0

        for r, d, f in os.walk(root_dir):
            d[:] = [sub for sub in d if sub not in self.ignored_dirs]
            for file in f:
                if file.endswith(".py"):
                    full_path = os.path.join(r, file)
                    try:
                        with open(full_path, "r", encoding="utf-8") as py_file:
                            content = py_file.read()
                        
                        # Verify it's valid python AST before ingesting
                        ast.parse(content)

                        # Determine mapping
                        cat, loop, braille = self.determine_category_and_loop(full_path, content)
                        gen_key = self._generate_genesis_key(cat)

                        # Create or update node
                        existing_node = self.db.query(BrailleSandboxNode).filter_by(file_path=full_path).first()
                        if existing_node:
                            existing_node.ast_content = content
                            existing_node.genesis_key = gen_key
                            existing_node.braille_encoding = braille
                            existing_node.master_loop = loop
                        else:
                            new_node = BrailleSandboxNode(
                                genesis_key=gen_key,
                                braille_encoding=braille,
                                master_loop=loop,
                                file_path=full_path,
                                ast_content=content,
                                is_active=True
                            )
                            self.db.add(new_node)
                        
                        nodes_created += 1

                    except Exception as e:
                        logger.warning(f"Failed to ingest Python file {full_path}: {str(e)}")
                        continue
        
        try:
            self.db.commit()
            logger.info(f"Successfully ingested {nodes_created} Python files into BrailleSandboxNodes.")
            return nodes_created
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to copy sandbox nodes to database: {e}")
            raise e
