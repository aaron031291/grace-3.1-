"""
Seed Default Categorization Rules

Creates a comprehensive set of default rules for automatic file categorization.
These rules cover common file types, naming patterns, and directory structures.

Run this script after migration to populate the rules table:
    python backend/librarian/seed_default_rules.py

Key Methods:
- `seed_rules()`
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.config import DatabaseConfig
from database.connection import DatabaseConnection
from database.session import initialize_session_factory
from librarian.rule_categorizer import RuleBasedCategorizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Default rules organized by category
DEFAULT_RULES = [
    # ==================== Extension-Based Rules ====================
    {
        "name": "PDF Documents",
        "description": "PDF document files",
        "pattern_type": "extension",
        "pattern_value": r"\.pdf$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["document", "pdf"]},
        "priority": 10
    },
    {
        "name": "Markdown Documentation",
        "description": "Markdown documentation files",
        "pattern_type": "extension",
        "pattern_value": r"\.md$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["documentation", "markdown"]},
        "priority": 10
    },
    {
        "name": "Python Code",
        "description": "Python source code files",
        "pattern_type": "extension",
        "pattern_value": r"\.py$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "python"]},
        "priority": 10
    },
    {
        "name": "JavaScript Code",
        "description": "JavaScript/TypeScript files",
        "pattern_type": "extension",
        "pattern_value": r"\.(js|jsx|ts|tsx)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "javascript"]},
        "priority": 10
    },
    {
        "name": "JSON Data",
        "description": "JSON data files",
        "pattern_type": "extension",
        "pattern_value": r"\.json$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["data", "json"]},
        "priority": 10
    },
    {
        "name": "YAML Configuration",
        "description": "YAML configuration files",
        "pattern_type": "extension",
        "pattern_value": r"\.(yaml|yml)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["configuration", "yaml"]},
        "priority": 10
    },
    {
        "name": "Text Files",
        "description": "Plain text files",
        "pattern_type": "extension",
        "pattern_value": r"\.txt$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["document", "text"]},
        "priority": 10
    },
    {
        "name": "CSV Data",
        "description": "CSV data files",
        "pattern_type": "extension",
        "pattern_value": r"\.csv$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["data", "csv"]},
        "priority": 10
    },
    {
        "name": "Excel Spreadsheets",
        "description": "Excel spreadsheet files",
        "pattern_type": "extension",
        "pattern_value": r"\.(xlsx|xls)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["document", "spreadsheet", "excel"]},
        "priority": 10
    },
    {
        "name": "Word Documents",
        "description": "Microsoft Word documents",
        "pattern_type": "extension",
        "pattern_value": r"\.(docx|doc)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["document", "word"]},
        "priority": 10
    },
    {
        "name": "PowerPoint Presentations",
        "description": "PowerPoint presentation files",
        "pattern_type": "extension",
        "pattern_value": r"\.(pptx|ppt)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["document", "presentation", "powerpoint"]},
        "priority": 10
    },
    {
        "name": "Image Files",
        "description": "Image files (PNG, JPG, GIF, etc.)",
        "pattern_type": "extension",
        "pattern_value": r"\.(png|jpg|jpeg|gif|bmp|svg|webp)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["media", "image"]},
        "priority": 10
    },
    {
        "name": "Audio Files",
        "description": "Audio files (MP3, WAV, etc.)",
        "pattern_type": "extension",
        "pattern_value": r"\.(mp3|wav|m4a|flac|ogg|aac)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["media", "audio"]},
        "priority": 10
    },
    {
        "name": "Video Files",
        "description": "Video files (MP4, AVI, etc.)",
        "pattern_type": "extension",
        "pattern_value": r"\.(mp4|avi|mov|mkv|webm|flv)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["media", "video"]},
        "priority": 10
    },
    {
        "name": "HTML Files",
        "description": "HTML web page files",
        "pattern_type": "extension",
        "pattern_value": r"\.(html|htm)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "html", "web"]},
        "priority": 10
    },
    {
        "name": "CSS Stylesheets",
        "description": "CSS stylesheet files",
        "pattern_type": "extension",
        "pattern_value": r"\.(css|scss|sass|less)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "css", "web"]},
        "priority": 10
    },
    {
        "name": "Shell Scripts",
        "description": "Shell script files",
        "pattern_type": "extension",
        "pattern_value": r"\.(sh|bash)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "script", "shell"]},
        "priority": 10
    },
    {
        "name": "SQL Scripts",
        "description": "SQL database scripts",
        "pattern_type": "extension",
        "pattern_value": r"\.sql$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "sql", "database"]},
        "priority": 10
    },
    {
        "name": "Java Code",
        "description": "Java source code files",
        "pattern_type": "extension",
        "pattern_value": r"\.java$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "java"]},
        "priority": 10
    },
    {
        "name": "C/C++ Code",
        "description": "C and C++ source code files",
        "pattern_type": "extension",
        "pattern_value": r"\.(c|cpp|cc|h|hpp)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "c++"]},
        "priority": 10
    },
    {
        "name": "Rust Code",
        "description": "Rust source code files",
        "pattern_type": "extension",
        "pattern_value": r"\.rs$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "rust"]},
        "priority": 10
    },
    {
        "name": "Go Code",
        "description": "Go source code files",
        "pattern_type": "extension",
        "pattern_value": r"\.go$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["code", "golang"]},
        "priority": 10
    },

    # ==================== Path-Based Rules ====================
    {
        "name": "AI Research Folder",
        "description": "Files in AI research directories",
        "pattern_type": "path",
        "pattern_value": r"ai[_\s\-]research",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["ai", "research"]},
        "priority": 20,
        "case_sensitive": False
    },
    {
        "name": "Systems Thinking Folder",
        "description": "Files in systems thinking directories",
        "pattern_type": "path",
        "pattern_value": r"systems[_\s\-]thinking",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["systems", "architecture"]},
        "priority": 20,
        "case_sensitive": False
    },
    {
        "name": "Learning Memory Folder",
        "description": "Files in learning memory directories",
        "pattern_type": "path",
        "pattern_value": r"learning[_\s\-]memory",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["learning", "memory"]},
        "priority": 20,
        "case_sensitive": False
    },
    {
        "name": "Documentation Folder",
        "description": "Files in documentation directories",
        "pattern_type": "path",
        "pattern_value": r"/(docs?|documentation)/",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["documentation"]},
        "priority": 20,
        "case_sensitive": False
    },
    {
        "name": "Test Files Folder",
        "description": "Files in test directories",
        "pattern_type": "path",
        "pattern_value": r"/(tests?|testing|__tests__)/",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["test", "testing"]},
        "priority": 20,
        "case_sensitive": False
    },
    {
        "name": "Examples Folder",
        "description": "Files in examples directories",
        "pattern_type": "path",
        "pattern_value": r"/(examples?|samples?)/",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["example", "tutorial"]},
        "priority": 20,
        "case_sensitive": False
    },
    {
        "name": "Configuration Folder",
        "description": "Files in config directories",
        "pattern_type": "path",
        "pattern_value": r"/(config|configuration|settings)/",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["configuration"]},
        "priority": 20,
        "case_sensitive": False
    },
    {
        "name": "Scripts Folder",
        "description": "Files in scripts directories",
        "pattern_type": "path",
        "pattern_value": r"/scripts?/",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["script"]},
        "priority": 20,
        "case_sensitive": False
    },

    # ==================== Filename-Based Rules ====================
    {
        "name": "README Files",
        "description": "README documentation files",
        "pattern_type": "filename",
        "pattern_value": r"^README",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["documentation", "readme"]},
        "priority": 15,
        "case_sensitive": False
    },
    {
        "name": "License Files",
        "description": "License files",
        "pattern_type": "filename",
        "pattern_value": r"^LICENSE",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["legal", "license"]},
        "priority": 15,
        "case_sensitive": False
    },
    {
        "name": "Changelog Files",
        "description": "Changelog files",
        "pattern_type": "filename",
        "pattern_value": r"^(CHANGELOG|HISTORY)",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["documentation", "changelog"]},
        "priority": 15,
        "case_sensitive": False
    },
    {
        "name": "Contributing Guide",
        "description": "Contributing guidelines",
        "pattern_type": "filename",
        "pattern_value": r"^CONTRIBUTING",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["documentation", "contributing"]},
        "priority": 15,
        "case_sensitive": False
    },
    {
        "name": "Test Files",
        "description": "Test files (test_*.py pattern)",
        "pattern_type": "filename",
        "pattern_value": r"^test_.*\.py$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["test", "python"]},
        "priority": 15,
        "case_sensitive": True
    },
    {
        "name": "Configuration Files",
        "description": "Common configuration filenames",
        "pattern_type": "filename",
        "pattern_value": r"^(config|settings|\.env|\.ini)",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["configuration"]},
        "priority": 15,
        "case_sensitive": False
    },
    {
        "name": "Package Files",
        "description": "Package definition files",
        "pattern_type": "filename",
        "pattern_value": r"^(package\.json|requirements\.txt|Pipfile|setup\.py|pyproject\.toml|Cargo\.toml|go\.mod)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["configuration", "dependencies"]},
        "priority": 15,
        "case_sensitive": True
    },
    {
        "name": "Docker Files",
        "description": "Docker-related files",
        "pattern_type": "filename",
        "pattern_value": r"^(Dockerfile|docker-compose)",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["devops", "docker", "configuration"]},
        "priority": 15,
        "case_sensitive": False
    },
    {
        "name": "CI/CD Files",
        "description": "CI/CD configuration files",
        "pattern_type": "filename",
        "pattern_value": r"^(\.github|\.gitlab-ci|\.travis|jenkinsfile|\.circleci)",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["devops", "ci-cd", "configuration"]},
        "priority": 15,
        "case_sensitive": False
    },
    {
        "name": "Makefile",
        "description": "Build automation files",
        "pattern_type": "filename",
        "pattern_value": r"^(Makefile|makefile)$",
        "action_type": "assign_tag",
        "action_params": {"tag_names": ["build", "automation"]},
        "priority": 15,
        "case_sensitive": True
    }
]


def seed_rules():
    """Seed default categorization rules into database."""
    logger.info("=" * 60)
    logger.info("Seeding Default Categorization Rules")
    logger.info("=" * 60)

    # Initialize database connection
    config = DatabaseConfig.from_env()
    DatabaseConnection.initialize(config)

    # Initialize session factory
    SessionLocal = initialize_session_factory()

    # Create session and categorizer
    db = SessionLocal()
    categorizer = RuleBasedCategorizer(db)

    rules_created = 0
    rules_skipped = 0
    errors = []

    logger.info(f"\nProcessing {len(DEFAULT_RULES)} default rules...\n")

    for rule_data in DEFAULT_RULES:
        try:
            # Check if rule already exists (by name)
            existing_rules = categorizer.list_rules()
            if any(r["name"] == rule_data["name"] for r in existing_rules):
                logger.info(f"✓ Rule '{rule_data['name']}' already exists, skipping...")
                rules_skipped += 1
                continue

            # Create rule
            rule = categorizer.create_rule(**rule_data)
            logger.info(f"✓ Created rule: {rule_data['name']} (ID: {rule.id}, Priority: {rule_data.get('priority', 0)})")
            rules_created += 1

        except Exception as e:
            error_msg = f"✗ Failed to create rule '{rule_data['name']}': {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            continue

    logger.info("")
    logger.info("=" * 60)
    logger.info("Seeding Summary")
    logger.info("=" * 60)
    logger.info(f"Created: {rules_created} rules")
    logger.info(f"Skipped: {rules_skipped} rules (already exist)")

    if errors:
        logger.info(f"Errors: {len(errors)}")
        for error in errors:
            logger.error(f"  {error}")

    logger.info("")
    logger.info("Default rules have been seeded!")
    logger.info("You can now use the RuleBasedCategorizer to automatically tag documents.")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Test rules: Use categorizer.test_rule_against_documents(rule_id)")
    logger.info("  2. Process documents: Use LibrarianEngine to process existing documents")
    logger.info("  3. Add custom rules: Use categorizer.create_rule() or API endpoints")

    db.close()


if __name__ == "__main__":
    seed_rules()
