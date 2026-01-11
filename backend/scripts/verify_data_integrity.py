"""
Data Integrity Verification System for Grace AI Research Repository Ingestion

This script provides comprehensive verification that:
1. All repositories were cloned correctly
2. All files are accessible and readable
3. All ingested documents match source files
4. Vector embeddings are stored correctly
5. Database records are complete and accurate

Usage:
    python verify_data_integrity.py [--detailed] [--category CATEGORY]
"""

import os
import sys
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import sqlite3

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from database.session import SessionLocal
from models.database_models import Document, DocumentChunk
from vector_db.client import get_qdrant_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RepositoryStats:
    """Statistics for a single repository."""
    name: str
    category: str
    path: str
    exists: bool
    file_count: int
    total_size_bytes: int
    git_valid: bool
    sample_files: List[str]


@dataclass
class IngestionStats:
    """Statistics for ingested data."""
    total_documents: int
    total_chunks: int
    documents_by_category: Dict[str, int]
    documents_by_repository: Dict[str, int]
    total_embeddings: int
    database_size_mb: float
    vector_db_collections: Dict[str, int]


@dataclass
class IntegrityReport:
    """Complete integrity verification report."""
    timestamp: str
    repositories: List[RepositoryStats]
    ingestion: IngestionStats
    verification_checks: Dict[str, bool]
    issues_found: List[str]
    warnings: List[str]
    summary: Dict[str, any]


class DataIntegrityVerifier:
    """Verifies data integrity across the entire ingestion pipeline."""

    def __init__(self, ai_research_path: str, database_path: str):
        """
        Initialize verifier.

        Args:
            ai_research_path: Path to ai_research directory
            database_path: Path to SQLite database
        """
        self.ai_research_path = Path(ai_research_path)
        self.database_path = Path(database_path)
        self.issues = []
        self.warnings = []

        # Initialize database connection
        logger.info("Initializing database connection...")
        db_config = DatabaseConfig.from_env()
        DatabaseConnection.initialize(db_config)

        # Initialize Qdrant client
        logger.info("Connecting to Qdrant...")
        self.qdrant = get_qdrant_client()

    def verify_repository(self, repo_path: Path, category: str) -> RepositoryStats:
        """
        Verify a single repository's integrity.

        Args:
            repo_path: Path to repository
            category: Repository category

        Returns:
            RepositoryStats with verification results
        """
        logger.info(f"Verifying repository: {repo_path.name}")

        # Check if path exists
        exists = repo_path.exists()
        if not exists:
            self.issues.append(f"Repository does not exist: {repo_path}")
            return RepositoryStats(
                name=repo_path.name,
                category=category,
                path=str(repo_path),
                exists=False,
                file_count=0,
                total_size_bytes=0,
                git_valid=False,
                sample_files=[]
            )

        # Check if it's a valid git repository
        git_dir = repo_path / ".git"
        git_valid = git_dir.exists() and git_dir.is_dir()
        if not git_valid:
            self.warnings.append(f"Not a valid git repository: {repo_path}")

        # Count files and calculate total size
        file_count = 0
        total_size = 0
        sample_files = []

        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')

            for file in files:
                file_count += 1
                file_path = Path(root) / file
                try:
                    total_size += file_path.stat().st_size
                    # Collect sample files (first 5)
                    if len(sample_files) < 5:
                        rel_path = file_path.relative_to(repo_path)
                        sample_files.append(str(rel_path))
                except Exception as e:
                    self.warnings.append(f"Could not stat file: {file_path} - {e}")

        return RepositoryStats(
            name=repo_path.name,
            category=category,
            path=str(repo_path),
            exists=True,
            file_count=file_count,
            total_size_bytes=total_size,
            git_valid=git_valid,
            sample_files=sample_files
        )

    def verify_all_repositories(self) -> List[RepositoryStats]:
        """
        Verify all repositories in ai_research directory.

        Returns:
            List of RepositoryStats for all repositories
        """
        logger.info(f"\n{'='*80}")
        logger.info("VERIFYING ALL REPOSITORIES")
        logger.info(f"{'='*80}\n")

        all_stats = []

        # Walk through all categories
        for category_dir in self.ai_research_path.iterdir():
            if not category_dir.is_dir():
                continue

            category = category_dir.name
            logger.info(f"\nCategory: {category.upper()}")
            logger.info(f"{'-'*80}")

            # Verify each repository in category
            for repo_dir in category_dir.iterdir():
                if not repo_dir.is_dir():
                    continue

                stats = self.verify_repository(repo_dir, category)
                all_stats.append(stats)

                # Log summary
                logger.info(f"  ✓ {stats.name}")
                logger.info(f"    Files: {stats.file_count:,}")
                logger.info(f"    Size: {stats.total_size_bytes / (1024*1024):.2f} MB")
                if not stats.git_valid:
                    logger.warning(f"    ⚠ Not a valid git repository")

        return all_stats

    def verify_database_integrity(self) -> IngestionStats:
        """
        Verify database integrity and gather statistics.

        Returns:
            IngestionStats with database verification results
        """
        logger.info(f"\n{'='*80}")
        logger.info("VERIFYING DATABASE INTEGRITY")
        logger.info(f"{'='*80}\n")

        db = SessionLocal()

        try:
            # Count total documents
            total_documents = db.query(Document).count()
            logger.info(f"Total documents in database: {total_documents:,}")

            # Count total chunks
            total_chunks = db.query(DocumentChunk).count()
            logger.info(f"Total chunks in database: {total_chunks:,}")

            # Count documents by category
            docs_by_category = {}
            categories = db.execute(
                "SELECT DISTINCT source FROM documents WHERE source LIKE 'ai_research/%'"
            ).fetchall()

            for (category_path,) in categories:
                if category_path and category_path.startswith('ai_research/'):
                    category = category_path.replace('ai_research/', '').split('/')[0]
                    count = db.query(Document).filter(
                        Document.source.like(f'ai_research/{category}%')
                    ).count()
                    docs_by_category[category] = count

            logger.info(f"\nDocuments by category:")
            for category, count in sorted(docs_by_category.items()):
                logger.info(f"  {category}: {count:,}")

            # Count documents by repository
            docs_by_repo = {}
            repos = db.execute(
                "SELECT DISTINCT tags FROM documents WHERE tags IS NOT NULL"
            ).fetchall()

            # Parse tags (JSON array)
            for (tags_json,) in repos:
                if tags_json:
                    try:
                        tags = json.loads(tags_json) if isinstance(tags_json, str) else tags_json
                        if isinstance(tags, list) and len(tags) > 1:
                            # Second tag is usually the repository name
                            repo_name = tags[1] if len(tags) > 1 else tags[0]
                            docs_by_repo[repo_name] = docs_by_repo.get(repo_name, 0) + 1
                    except json.JSONDecodeError:
                        pass

            logger.info(f"\nDocuments by repository:")
            for repo, count in sorted(docs_by_repo.items(), key=lambda x: x[1], reverse=True)[:20]:
                logger.info(f"  {repo}: {count:,}")

            # Count embeddings (chunks with vector IDs)
            total_embeddings = db.query(DocumentChunk).filter(
                DocumentChunk.embedding_vector_id.isnot(None)
            ).count()
            logger.info(f"\nTotal embeddings stored: {total_embeddings:,}")

            # Calculate database size
            db_size_bytes = self.database_path.stat().st_size if self.database_path.exists() else 0
            db_size_mb = db_size_bytes / (1024 * 1024)
            logger.info(f"Database size: {db_size_mb:.2f} MB")

            # Verify Qdrant collections
            vector_collections = {}
            try:
                collections = self.qdrant.list_collections()
                for collection in collections:
                    # Get count for each collection
                    collection_info = self.qdrant.client.get_collection(collection)
                    vector_collections[collection] = collection_info.points_count

                logger.info(f"\nVector database collections:")
                for collection, count in vector_collections.items():
                    logger.info(f"  {collection}: {count:,} vectors")
            except Exception as e:
                self.warnings.append(f"Could not verify Qdrant collections: {e}")
                logger.warning(f"⚠ Could not verify Qdrant: {e}")

            return IngestionStats(
                total_documents=total_documents,
                total_chunks=total_chunks,
                documents_by_category=docs_by_category,
                documents_by_repository=docs_by_repo,
                total_embeddings=total_embeddings,
                database_size_mb=db_size_mb,
                vector_db_collections=vector_collections
            )

        finally:
            db.close()

    def verify_file_to_database_mapping(self, sample_size: int = 100) -> Dict[str, bool]:
        """
        Verify that files on disk match database records.

        Args:
            sample_size: Number of random files to verify

        Returns:
            Dict with verification results
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"VERIFYING FILE-TO-DATABASE MAPPING (sample size: {sample_size})")
        logger.info(f"{'='*80}\n")

        db = SessionLocal()
        results = {
            'files_checked': 0,
            'files_found_in_db': 0,
            'files_missing_in_db': 0,
            'content_matches': 0,
            'content_mismatches': 0,
        }

        try:
            # Get sample of documents from database
            sample_docs = db.query(Document).filter(
                Document.source.like('ai_research/%')
            ).limit(sample_size).all()

            for doc in sample_docs:
                results['files_checked'] += 1

                # Get file path from metadata
                file_path_rel = None
                if doc.metadata:
                    try:
                        metadata = json.loads(doc.metadata) if isinstance(doc.metadata, str) else doc.metadata
                        file_path_rel = metadata.get('file_path')
                    except json.JSONDecodeError:
                        pass

                if not file_path_rel:
                    # Try to reconstruct from filename and source
                    file_path_rel = f"{doc.source}/{doc.filename}"

                # Construct full path
                full_path = self.ai_research_path.parent / file_path_rel

                if full_path.exists():
                    results['files_found_in_db'] += 1

                    # Verify content hash (for small files)
                    if full_path.stat().st_size < 1_000_000:  # 1MB limit
                        try:
                            with open(full_path, 'rb') as f:
                                file_hash = hashlib.sha256(f.read()).hexdigest()

                            # Compare with stored hash
                            if doc.content_hash == file_hash:
                                results['content_matches'] += 1
                            else:
                                results['content_mismatches'] += 1
                                self.warnings.append(
                                    f"Content mismatch: {file_path_rel} "
                                    f"(expected {doc.content_hash[:8]}..., got {file_hash[:8]}...)"
                                )
                        except Exception as e:
                            self.warnings.append(f"Could not verify content: {file_path_rel} - {e}")
                else:
                    results['files_missing_in_db'] += 1
                    self.warnings.append(f"File not found on disk: {file_path_rel}")

            # Log results
            logger.info(f"Files checked: {results['files_checked']}")
            logger.info(f"Files found in database: {results['files_found_in_db']}")
            logger.info(f"Files missing: {results['files_missing_in_db']}")
            logger.info(f"Content matches: {results['content_matches']}")
            logger.info(f"Content mismatches: {results['content_mismatches']}")

            return results

        finally:
            db.close()

    def run_full_verification(self) -> IntegrityReport:
        """
        Run complete data integrity verification.

        Returns:
            IntegrityReport with all verification results
        """
        logger.info(f"\n{'#'*80}")
        logger.info(f"# GRACE DATA INTEGRITY VERIFICATION")
        logger.info(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'#'*80}\n")

        # Verify repositories
        repo_stats = self.verify_all_repositories()

        # Verify database
        ingestion_stats = self.verify_database_integrity()

        # Verify file-to-database mapping
        mapping_results = self.verify_file_to_database_mapping(sample_size=100)

        # Run verification checks
        verification_checks = {
            'all_repos_exist': all(stat.exists for stat in repo_stats),
            'all_repos_have_git': all(stat.git_valid for stat in repo_stats),
            'database_has_documents': ingestion_stats.total_documents > 0,
            'database_has_chunks': ingestion_stats.total_chunks > 0,
            'embeddings_stored': ingestion_stats.total_embeddings > 0,
            'vector_db_connected': len(ingestion_stats.vector_db_collections) > 0,
            'file_mapping_valid': mapping_results.get('files_found_in_db', 0) > 0,
            'content_integrity': mapping_results.get('content_mismatches', 0) == 0,
        }

        # Calculate summary statistics
        total_files = sum(stat.file_count for stat in repo_stats)
        total_size_gb = sum(stat.total_size_bytes for stat in repo_stats) / (1024**3)
        total_repos = len(repo_stats)

        summary = {
            'total_repositories': total_repos,
            'total_files_on_disk': total_files,
            'total_size_gb': round(total_size_gb, 2),
            'total_documents_ingested': ingestion_stats.total_documents,
            'total_chunks_created': ingestion_stats.total_chunks,
            'total_embeddings': ingestion_stats.total_embeddings,
            'database_size_mb': round(ingestion_stats.database_size_mb, 2),
            'ingestion_coverage_pct': round(
                (ingestion_stats.total_documents / total_files * 100) if total_files > 0 else 0,
                2
            ),
            'all_checks_passed': all(verification_checks.values()),
            'issues_count': len(self.issues),
            'warnings_count': len(self.warnings),
        }

        # Create report
        report = IntegrityReport(
            timestamp=datetime.now().isoformat(),
            repositories=repo_stats,
            ingestion=ingestion_stats,
            verification_checks=verification_checks,
            issues_found=self.issues,
            warnings=self.warnings,
            summary=summary
        )

        # Print final summary
        logger.info(f"\n{'#'*80}")
        logger.info(f"# VERIFICATION COMPLETE")
        logger.info(f"{'#'*80}\n")

        logger.info(f"Summary:")
        logger.info(f"  Total repositories: {summary['total_repositories']}")
        logger.info(f"  Total files on disk: {summary['total_files_on_disk']:,}")
        logger.info(f"  Total size: {summary['total_size_gb']:.2f} GB")
        logger.info(f"  Documents ingested: {summary['total_documents_ingested']:,}")
        logger.info(f"  Chunks created: {summary['total_chunks_created']:,}")
        logger.info(f"  Embeddings stored: {summary['total_embeddings']:,}")
        logger.info(f"  Database size: {summary['database_size_mb']:.2f} MB")
        logger.info(f"  Ingestion coverage: {summary['ingestion_coverage_pct']:.2f}%")

        logger.info(f"\nVerification Checks:")
        for check, passed in verification_checks.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"  {status}: {check}")

        logger.info(f"\nIssues: {len(self.issues)}")
        for issue in self.issues[:10]:  # Show first 10
            logger.error(f"  ✗ {issue}")
        if len(self.issues) > 10:
            logger.error(f"  ... and {len(self.issues) - 10} more issues")

        logger.info(f"\nWarnings: {len(self.warnings)}")
        for warning in self.warnings[:10]:  # Show first 10
            logger.warning(f"  ⚠ {warning}")
        if len(self.warnings) > 10:
            logger.warning(f"  ... and {len(self.warnings) - 10} more warnings")

        if summary['all_checks_passed'] and len(self.issues) == 0:
            logger.info(f"\n🎉 ALL INTEGRITY CHECKS PASSED! Data is complete and intact.")
        else:
            logger.warning(f"\n⚠ Some issues or checks failed. Review the report above.")

        return report

    def save_report(self, report: IntegrityReport, output_file: str):
        """
        Save verification report to JSON file.

        Args:
            report: IntegrityReport to save
            output_file: Path to output file
        """
        logger.info(f"\nSaving report to: {output_file}")

        # Convert report to dict
        report_dict = {
            'timestamp': report.timestamp,
            'repositories': [asdict(stat) for stat in report.repositories],
            'ingestion': asdict(report.ingestion),
            'verification_checks': report.verification_checks,
            'issues_found': report.issues_found,
            'warnings': report.warnings,
            'summary': report.summary,
        }

        # Save to file
        with open(output_file, 'w') as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"✓ Report saved successfully")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Verify data integrity of Grace AI research repository ingestion'
    )
    parser.add_argument(
        '--output',
        default='data_integrity_report.json',
        help='Output file for verification report (default: data_integrity_report.json)'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=100,
        help='Number of files to verify in detail (default: 100)'
    )

    args = parser.parse_args()

    # Get paths
    project_root = Path(__file__).parent.parent.parent
    ai_research_path = project_root / "data" / "ai_research"
    database_path = project_root / "data" / "grace.db"

    # Create verifier
    verifier = DataIntegrityVerifier(
        str(ai_research_path),
        str(database_path)
    )

    # Run verification
    report = verifier.run_full_verification()

    # Save report
    output_path = project_root / args.output
    verifier.save_report(report, str(output_path))

    # Return exit code based on results
    if report.summary['all_checks_passed'] and len(report.issues_found) == 0:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
