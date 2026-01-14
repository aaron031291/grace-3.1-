"""
Script to ingest all AI research repositories into Grace's training data.

This script processes the cloned repositories in data/ai_research and ingests
relevant documentation and code files into the knowledge base.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Set

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from ingestion.service import TextIngestionService
from embedding import get_embedding_model
from file_manager.file_handler import FileHandler
from database.connection import DatabaseConnection
from database.config import DatabaseConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIResearchIngestionManager:
    """Manages ingestion of AI research repositories."""

    # File extensions to ingest
    SUPPORTED_EXTENSIONS = {
        # Documentation
        '.md', '.rst', '.txt', '.adoc',
        # Code
        '.py', '.js', '.ts', '.tsx', '.jsx',
        '.java', '.go', '.rs', '.cpp', '.c', '.h',
        '.rb', '.php', '.scala', '.kt',
        # Configuration and data
        '.json', '.yaml', '.yml', '.toml', '.xml',
    }

    # Directories to skip
    SKIP_DIRS = {
        '.git', '__pycache__', 'node_modules', 'venv', 'env',
        '.pytest_cache', '.mypy_cache', 'dist', 'build',
        '.next', '.nuxt', 'coverage', '.tox',
        'vendor', 'target', 'bin', 'obj',
        # Skip docs build artifacts
        '_build', '.doctrees', 'site',
    }

    def __init__(self, ai_research_path: str):
        """
        Initialize ingestion manager.

        Args:
            ai_research_path: Path to ai_research directory
        """
        self.ai_research_path = Path(ai_research_path)

        # Initialize database
        logger.info("Initializing database connection...")
        db_config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(db_config)
        logger.info("Database initialized successfully")

        # Initialize services
        logger.info("Initializing embedding model...")
        self.embedding_model = get_embedding_model()

        logger.info("Initializing ingestion service...")
        self.ingestion_service = TextIngestionService(
            collection_name="documents",
            chunk_size=512,
            chunk_overlap=50,
            embedding_model=self.embedding_model,
        )

    def should_ingest_file(self, filepath: Path) -> bool:
        """
        Check if file should be ingested.

        Args:
            filepath: Path to file

        Returns:
            bool: True if file should be ingested
        """
        # Check extension
        if filepath.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return False

        # Skip hidden files
        if filepath.name.startswith('.'):
            return False

        # Skip very large files (>1MB)
        try:
            if filepath.stat().st_size > 1_000_000:
                logger.debug(f"Skipping large file: {filepath} ({filepath.stat().st_size} bytes)")
                return False
        except Exception:
            return False

        return True

    def read_file_content(self, filepath: Path) -> str:
        """
        Read file content with proper encoding handling.

        Args:
            filepath: Path to file

        Returns:
            File content or None if unreadable
        """
        try:
            file_ext = filepath.suffix.lower()

            # For PDFs and complex formats, use specialized extractors
            if file_ext in ['.pdf', '.docx', '.doc']:
                text, error = FileHandler.extract_text(str(filepath))
                if error:
                    logger.warning(f"Extraction failed for {filepath}: {error}")
                    return None
                return text

            # For text files, read directly
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                try:
                    with open(filepath, 'r', encoding='latin-1') as f:
                        return f.read()
                except Exception as e:
                    logger.warning(f"Could not read file {filepath}: {e}")
                    return None
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return None

    def ingest_repository(self, repo_path: Path, category: str) -> dict:
        """
        Ingest a single repository.

        Args:
            repo_path: Path to repository
            category: Category (frameworks, enterprise, infrastructure, references)

        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Ingesting repository: {repo_path.name}")
        logger.info(f"Category: {category}")
        logger.info(f"{'='*80}\n")

        stats = {
            'repo_name': repo_path.name,
            'category': category,
            'files_processed': 0,
            'files_succeeded': 0,
            'files_failed': 0,
            'files_skipped': 0,
        }

        # Walk through repository
        for root, dirs, files in os.walk(repo_path):
            root_path = Path(root)

            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]

            for filename in files:
                filepath = root_path / filename

                # Check if should ingest
                if not self.should_ingest_file(filepath):
                    stats['files_skipped'] += 1
                    continue

                stats['files_processed'] += 1

                # Compute relative path for metadata
                rel_path = filepath.relative_to(self.ai_research_path)

                logger.info(f"Processing: {rel_path}")

                try:
                    # Read content
                    content = self.read_file_content(filepath)
                    if not content:
                        logger.warning(f"Could not read content from {rel_path}")
                        stats['files_failed'] += 1
                        continue

                    # Skip empty files
                    if len(content.strip()) < 50:
                        logger.debug(f"Skipping empty/tiny file: {rel_path}")
                        stats['files_skipped'] += 1
                        stats['files_processed'] -= 1
                        continue

                    # Ingest
                    doc_id, message = self.ingestion_service.ingest_text_fast(
                        text_content=content,
                        filename=str(rel_path),
                        source=f"ai_research/{category}",
                        upload_method="batch-import",
                        source_type="official_docs" if category == "references" else "verified_tutorial",
                        description=f"AI Research: {repo_path.name} - {filepath.name}",
                        tags=[category, repo_path.name, filepath.suffix[1:]],
                        metadata={
                            "category": category,
                            "repository": repo_path.name,
                            "file_path": str(rel_path),
                            "file_extension": filepath.suffix,
                        },
                    )

                    if doc_id:
                        stats['files_succeeded'] += 1
                        logger.info(f"✓ Ingested: {rel_path} (doc_id={doc_id})")
                    else:
                        stats['files_failed'] += 1
                        logger.error(f"✗ Failed: {rel_path} - {message}")

                except Exception as e:
                    stats['files_failed'] += 1
                    logger.error(f"✗ Error processing {rel_path}: {e}")

        # Print statistics
        logger.info(f"\n{'='*80}")
        logger.info(f"Repository: {repo_path.name} - COMPLETE")
        logger.info(f"  Processed: {stats['files_processed']}")
        logger.info(f"  Succeeded: {stats['files_succeeded']}")
        logger.info(f"  Failed: {stats['files_failed']}")
        logger.info(f"  Skipped: {stats['files_skipped']}")
        logger.info(f"{'='*80}\n")

        return stats

    def ingest_all_repositories(self) -> dict:
        """
        Ingest all repositories in ai_research directory.

        Returns:
            Dictionary with overall statistics
        """
        logger.info(f"\n{'#'*80}")
        logger.info(f"# AI Research Repository Ingestion")
        logger.info(f"# Path: {self.ai_research_path}")
        logger.info(f"{'#'*80}\n")

        overall_stats = {
            'total_repos': 0,
            'total_files_processed': 0,
            'total_files_succeeded': 0,
            'total_files_failed': 0,
            'total_files_skipped': 0,
            'repositories': [],
        }

        # Process each category
        for category_dir in self.ai_research_path.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name
            logger.info(f"\n{'*'*80}")
            logger.info(f"* Category: {category.upper()}")
            logger.info(f"{'*'*80}\n")

            # Process each repository in category
            for repo_dir in category_dir.iterdir():
                if not repo_dir.is_dir():
                    continue

                overall_stats['total_repos'] += 1

                # Ingest repository
                stats = self.ingest_repository(repo_dir, category)
                overall_stats['repositories'].append(stats)

                # Update totals
                overall_stats['total_files_processed'] += stats['files_processed']
                overall_stats['total_files_succeeded'] += stats['files_succeeded']
                overall_stats['total_files_failed'] += stats['files_failed']
                overall_stats['total_files_skipped'] += stats['files_skipped']

        # Print overall statistics
        logger.info(f"\n{'#'*80}")
        logger.info(f"# OVERALL STATISTICS")
        logger.info(f"{'#'*80}")
        logger.info(f"Total Repositories: {overall_stats['total_repos']}")
        logger.info(f"Total Files Processed: {overall_stats['total_files_processed']}")
        logger.info(f"Total Files Succeeded: {overall_stats['total_files_succeeded']}")
        logger.info(f"Total Files Failed: {overall_stats['total_files_failed']}")
        logger.info(f"Total Files Skipped: {overall_stats['total_files_skipped']}")
        logger.info(f"{'#'*80}\n")

        return overall_stats


def main():
    """Main entry point."""
    # Get paths
    project_root = Path(__file__).parent.parent.parent
    ai_research_path = project_root / "data" / "ai_research"

    if not ai_research_path.exists():
        logger.error(f"AI research directory not found: {ai_research_path}")
        sys.exit(1)

    # Create manager and run ingestion
    manager = AIResearchIngestionManager(str(ai_research_path))
    stats = manager.ingest_all_repositories()

    logger.info("Ingestion complete!")
    return stats


if __name__ == "__main__":
    main()
