"""
Re-ingest missing files from ai research folder.
These files were uploaded but failed to ingest before the 5GB limit update.
"""

import os
import sys
import sqlite3
import json
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.service import TextIngestionService
from embedding import get_embedding_model
from file_manager.file_handler import extract_file_text
from database.session import initialize_session_factory
from database.connection import DatabaseConnection
from database.config import DatabaseConfig
from models.database_models import Document


def get_missing_files():
    """Identify files that are uploaded but not ingested."""
    # Read metadata
    metadata_path = Path(__file__).parent / "knowledge_base" / ".metadata.json"
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Get ingested files from database
    conn = sqlite3.connect('data/grace.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT file_path
        FROM documents
        WHERE file_path LIKE '%ai research%'
    ''')
    ingested_paths = [row[0] for row in cursor.fetchall()]
    conn.close()

    ingested_files = set(os.path.basename(p) for p in ingested_paths)

    # Find missing files
    missing_files = []
    for key, info in metadata.items():
        if 'ai research' in key.lower():
            filename = info.get('filename', '')
            if filename and filename not in ingested_files:
                # Construct full path
                file_path = key.replace('files:', '').replace('\\\\', os.sep)
                full_path = Path(__file__).parent / "knowledge_base" / file_path

                if full_path.exists():
                    size_mb = info.get('size', 0) / (1024 * 1024)
                    missing_files.append({
                        'filename': filename,
                        'path': file_path,
                        'full_path': str(full_path),
                        'size_mb': size_mb
                    })

    return missing_files


async def ingest_file(file_info: dict, ingestion_service: TextIngestionService, session_factory):
    """Ingest a single file."""
    try:
        print(f"\nProcessing: {file_info['filename']} ({file_info['size_mb']:.2f} MB)")

        # Extract text from file (returns tuple of (text, error))
        result = extract_file_text(file_info['full_path'])

        if isinstance(result, tuple):
            text, error = result
            if error:
                print(f"  [ERROR] Extraction error: {error}")
                return False
        else:
            text = result

        if not text or len(text.strip()) == 0:
            print(f"  [WARN] No text extracted from {file_info['filename']}")
            return False

        print(f"  [OK] Extracted {len(text)} characters")

        # Create document record
        db = session_factory()

        try:
            # Check if document already exists
            existing = db.query(Document).filter(
                Document.file_path == file_info['path']
            ).first()

            if existing:
                print(f"  [WARN] Document already exists in database, skipping")
                return True

            # Create new document
            doc = Document(
                file_path=file_info['path'],
                text_content=text,
                char_count=len(text)
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            print(f"  [OK] Created document record (ID: {doc.id})")

            # Ingest into vector database
            await ingestion_service.ingest_text(
                text=text,
                metadata={
                    "source": file_info['path'],
                    "filename": file_info['filename'],
                    "document_id": doc.id
                },
                document_id=doc.id
            )

            print(f"  [OK] Ingested into vector database")
            return True

        except Exception as e:
            db.rollback()
            print(f"  [ERROR] Error: {e}")
            return False
        finally:
            db.close()

    except Exception as e:
        print(f"  [ERROR] Failed to process {file_info['filename']}: {e}")
        return False


async def main():
    """Main re-ingestion process."""
    print("=" * 80)
    print("Re-ingesting Missing Files from AI Research Folder")
    print("=" * 80)

    # Get missing files
    print("\n[1/4] Identifying missing files...")
    missing_files = get_missing_files()

    if not missing_files:
        print("[OK] No missing files found - all files are already ingested!")
        return

    print(f"[OK] Found {len(missing_files)} missing files")

    # Sort by size (smallest first to test the process)
    missing_files.sort(key=lambda x: x['size_mb'])

    # Show summary
    print(f"\n[2/4] Missing files summary:")
    print(f"  Total files: {len(missing_files)}")
    print(f"  Total size: {sum(f['size_mb'] for f in missing_files):.2f} MB")
    print(f"  Smallest: {missing_files[0]['filename']} ({missing_files[0]['size_mb']:.2f} MB)")
    print(f"  Largest: {missing_files[-1]['filename']} ({missing_files[-1]['size_mb']:.2f} MB)")

    # Initialize database
    print(f"\n[3/5] Initializing database...")
    db_config = DatabaseConfig(
        db_type='sqlite',
        database='grace',
        database_path='data/grace.db'
    )
    DatabaseConnection.initialize(db_config)
    session_factory = initialize_session_factory()
    print("[OK] Database initialized")

    # Initialize ingestion service
    print(f"\n[4/5] Initializing ingestion service...")
    embedding_model = get_embedding_model()
    ingestion_service = TextIngestionService(
        collection_name="documents",
        chunk_size=512,
        chunk_overlap=50,
        embedding_model=embedding_model,
    )
    print("[OK] Ingestion service ready")

    # Process files
    print(f"\n[5/5] Processing {len(missing_files)} files...")
    print("=" * 80)

    success_count = 0
    failed_files = []

    for i, file_info in enumerate(missing_files, 1):
        print(f"\n[{i}/{len(missing_files)}] ", end="")

        success = await ingest_file(file_info, ingestion_service, session_factory)

        if success:
            success_count += 1
        else:
            failed_files.append(file_info['filename'])

    # Summary
    print("\n" + "=" * 80)
    print("Re-ingestion Complete")
    print("=" * 80)
    print(f"[OK] Successfully ingested: {success_count}/{len(missing_files)} files")

    if failed_files:
        print(f"\n[WARN] Failed files ({len(failed_files)}):")
        for filename in failed_files:
            print(f"  - {filename}")
    else:
        print("\n[SUCCESS] All files successfully ingested!")


if __name__ == "__main__":
    asyncio.run(main())
