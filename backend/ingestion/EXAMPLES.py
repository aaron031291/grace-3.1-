"""
Examples and integration patterns for the File-Based Ingestion Manager.
Shows how to use the manager in different contexts.

Key Methods:
- `example_basic_scan()`
- `example_continuous_watch()`
- `example_process_specific_actions()`
- `example_fastapi_integration()`
- `example_error_handling()`
- `example_batch_import()`
- `example_state_management()`
- `example_git_operations()`
- `example_custom_processing()`
- `example_monitoring_logging()`
"""

# ==================== Example 1: Basic File Scanning ====================

def example_basic_scan():
    """Basic example: Scan for changes and process them."""
    from ingestion.file_manager import IngestionFileManager
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    
    # Initialize
    embedding_model = get_embedding_model()
    ingestion_service = get_ingestion_service()
    
    manager = IngestionFileManager(
        knowledge_base_path="backend/knowledge_base",
        embedding_model=embedding_model,
        ingestion_service=ingestion_service,
    )
    
    # Scan for changes
    results = manager.scan_directory()
    
    # Process results
    for result in results:
        if result.success:
            print(f"✓ {result.change_type.upper()}: {result.filepath}")
            print(f"  Document ID: {result.document_id}")
            print(f"  Message: {result.message}\n")
        else:
            print(f"✗ {result.change_type.upper()}: {result.filepath}")
            print(f"  Error: {result.error}\n")


# ==================== Example 2: Continuous Watching ====================

def example_continuous_watch():
    """Example: Watch directory continuously for changes."""
    from ingestion.file_manager import IngestionFileManager
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    
    embedding_model = get_embedding_model()
    ingestion_service = get_ingestion_service()
    
    manager = IngestionFileManager(
        knowledge_base_path="backend/knowledge_base",
        embedding_model=embedding_model,
        ingestion_service=ingestion_service,
    )
    
    # Watch continuously (checks every 5 seconds)
    # Press Ctrl+C to stop
    manager.watch_and_process(continuous=True)


# ==================== Example 3: Processing Specific Actions ====================

def example_process_specific_actions():
    """Example: Handle specific file actions manually."""
    from pathlib import Path
    from ingestion.file_manager import IngestionFileManager
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    
    embedding_model = get_embedding_model()
    ingestion_service = get_ingestion_service()
    
    manager = IngestionFileManager(
        knowledge_base_path="backend/knowledge_base",
        embedding_model=embedding_model,
        ingestion_service=ingestion_service,
    )
    
    kb_path = Path("backend/knowledge_base")
    
    # Process new file
    print("Processing new file...")
    result = manager.process_new_file(kb_path / "new_guide.md")
    print(f"  Success: {result.success}")
    print(f"  Document ID: {result.document_id}")
    
    # Process modified file
    print("\nProcessing modified file...")
    result = manager.process_modified_file(kb_path / "existing_guide.md")
    print(f"  Success: {result.success}")
    
    # Process deleted file
    print("\nProcessing deleted file...")
    result = manager.process_deleted_file("backend/knowledge_base/old_guide.md")
    print(f"  Success: {result.success}")


# ==================== Example 4: Integration with FastAPI ====================

def example_fastapi_integration():
    """
    Example: Using the file manager with FastAPI.
    This shows how it's integrated in app.py
    """
    from fastapi import FastAPI, BackgroundTasks, Depends
    from ingestion.file_manager import IngestionFileManager
    from api.file_ingestion import get_file_manager
    
    app = FastAPI()
    
    # Endpoint 1: Synchronous scan
    @app.post("/api/scan-knowledge-base")
    async def scan_files(file_manager: IngestionFileManager = Depends(get_file_manager)):
        """Scan and process all changes."""
        results = file_manager.scan_directory()
        return {
            "total": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
        }
    
    # Endpoint 2: Background scan
    @app.post("/api/scan-background")
    async def scan_background(
        background_tasks: BackgroundTasks,
        file_manager: IngestionFileManager = Depends(get_file_manager),
    ):
        """Start background scan (non-blocking)."""
        def scan_task():
            results = file_manager.scan_directory()
            print(f"Background scan complete: {len(results)} changes")
        
        background_tasks.add_task(scan_task)
        return {"status": "scan started"}
    
    # Endpoint 3: Get status
    @app.get("/api/ingestion-status")
    async def get_status(file_manager: IngestionFileManager = Depends(get_file_manager)):
        """Get manager status."""
        git_dir = file_manager.knowledge_base_path / ".git"
        return {
            "initialized": True,
            "tracked_files": len(file_manager.file_states),
            "git_initialized": git_dir.exists(),
        }


# ==================== Example 5: Error Handling ====================

def example_error_handling():
    """Example: Proper error handling when using the manager."""
    from ingestion.file_manager import IngestionFileManager
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    from pathlib import Path
    
    try:
        embedding_model = get_embedding_model()
        ingestion_service = get_ingestion_service()
        
        manager = IngestionFileManager(
            knowledge_base_path="backend/knowledge_base",
            embedding_model=embedding_model,
            ingestion_service=ingestion_service,
        )
        
        # Scan with error handling
        results = manager.scan_directory()
        
        # Analyze results
        errors = [r for r in results if not r.success]
        if errors:
            print(f"\nEncountered {len(errors)} errors:")
            for error_result in errors:
                print(f"  - {error_result.filepath}")
                print(f"    Change: {error_result.change_type}")
                print(f"    Error: {error_result.error}")
        
        # Get success summary
        successes = [r for r in results if r.success]
        if successes:
            print(f"\nSuccessfully processed {len(successes)} files:")
            for success_result in successes:
                print(f"  - {success_result.filepath} (ID: {success_result.document_id})")
    
    except Exception as e:
        print(f"Failed to initialize manager: {e}")
        # Fallback handling


# ==================== Example 6: Batch Import ====================

def example_batch_import():
    """Example: Batch import documents from external source."""
    import shutil
    from pathlib import Path
    from ingestion.file_manager import IngestionFileManager
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    
    # Copy files to knowledge base
    source_dir = Path("external_documents")
    dest_dir = Path("backend/knowledge_base/imported")
    
    if source_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all supported files
        for file in source_dir.rglob("*"):
            if file.is_file():
                relative = file.relative_to(source_dir)
                dest_file = dest_dir / relative
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, dest_file)
                print(f"Copied: {relative}")
    
    # Now scan and ingest
    print("\nScanning and ingesting...")
    embedding_model = get_embedding_model()
    ingestion_service = get_ingestion_service()
    
    manager = IngestionFileManager(
        knowledge_base_path="backend/knowledge_base",
        embedding_model=embedding_model,
        ingestion_service=ingestion_service,
    )
    
    results = manager.scan_directory()
    
    # Report
    successful = sum(1 for r in results if r.success)
    print(f"\nImport complete: {successful}/{len(results)} successful")


# ==================== Example 7: State Management ====================

def example_state_management():
    """Example: Managing ingestion state."""
    from ingestion.file_manager import IngestionFileManager
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    import json
    
    embedding_model = get_embedding_model()
    ingestion_service = get_ingestion_service()
    
    manager = IngestionFileManager(
        knowledge_base_path="backend/knowledge_base",
        embedding_model=embedding_model,
        ingestion_service=ingestion_service,
    )
    
    # View current state
    print(f"Tracking {len(manager.file_states)} files")
    
    # Export state to JSON
    with open("ingestion_state_backup.json", "w") as f:
        json.dump(manager.file_states, f, indent=2)
    print("State backed up to ingestion_state_backup.json")
    
    # Clear state (forces re-ingestion on next scan)
    old_count = len(manager.file_states)
    manager.file_states.clear()
    manager._save_state()
    print(f"Cleared {old_count} tracked files")
    
    # Reload state
    manager._load_state()
    print(f"Reloaded {len(manager.file_states)} files")


# ==================== Example 8: Git Operations ====================

def example_git_operations():
    """Example: Direct git operations."""
    from ingestion.file_manager import IngestionFileManager
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    
    embedding_model = get_embedding_model()
    ingestion_service = get_ingestion_service()
    
    manager = IngestionFileManager(
        knowledge_base_path="backend/knowledge_base",
        embedding_model=embedding_model,
        ingestion_service=ingestion_service,
    )
    
    tracker = manager.git_tracker
    
    # Initialize git
    tracker.initialize_git()
    print("✓ Git initialized")
    
    # Get untracked files
    untracked = tracker.get_untracked_files()
    print(f"Untracked files: {len(untracked)}")
    
    # Stage specific file
    tracker.add_file("documents/guide.md")
    print("✓ File staged")
    
    # Commit changes
    tracker.commit_changes("Manual ingestion of document")
    print("✓ Changes committed")


# ==================== Example 9: Custom Processing ====================

def example_custom_processing():
    """Example: Custom processing logic on top of manager."""
    from pathlib import Path
    from ingestion.file_manager import IngestionFileManager, IngestionResult
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    
    class CustomIngestionManager(IngestionFileManager):
        """Extended manager with custom logic."""
        
        def process_new_file(self, filepath: Path):
            """Override with custom logic."""
            print(f"[CUSTOM] Processing new file: {filepath}")
            
            # Add custom pre-processing
            content = self._read_file_content(filepath)
            if content and "SKIP" in content:
                print("[CUSTOM] Skipping file marked with SKIP")
                return IngestionResult(
                    success=True,
                    filepath=str(filepath),
                    change_type="added",
                    message="Skipped as requested"
                )
            
            # Call parent implementation
            return super().process_new_file(filepath)
    
    # Use custom manager
    embedding_model = get_embedding_model()
    ingestion_service = get_ingestion_service()
    
    manager = CustomIngestionManager(
        knowledge_base_path="backend/knowledge_base",
        embedding_model=embedding_model,
        ingestion_service=ingestion_service,
    )
    
    results = manager.scan_directory()


# ==================== Example 10: Monitoring and Logging ====================

def example_monitoring_logging():
    """Example: Set up monitoring and advanced logging."""
    import logging
    from ingestion.file_manager import IngestionFileManager
    from embedding import get_embedding_model
    from api.ingest import get_ingestion_service
    
    # Set up detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("ingestion.log"),
            logging.StreamHandler(),
        ]
    )
    
    logger = logging.getLogger("ingestion_monitor")
    
    embedding_model = get_embedding_model()
    ingestion_service = get_ingestion_service()
    
    manager = IngestionFileManager(
        knowledge_base_path="backend/knowledge_base",
        embedding_model=embedding_model,
        ingestion_service=ingestion_service,
    )
    
    # Scan with monitoring
    logger.info("Starting ingestion scan")
    results = manager.scan_directory()
    
    # Detailed metrics
    by_type = {}
    for result in results:
        change_type = result.change_type
        by_type[change_type] = by_type.get(change_type, 0) + 1
    
    logger.info(f"Scan complete. Results by type: {by_type}")
    
    # Log any failures
    failures = [r for r in results if not r.success]
    if failures:
        logger.warning(f"Encountered {len(failures)} failures")
        for failure in failures:
            logger.error(f"  {failure.filepath}: {failure.error}")


if __name__ == "__main__":
    # Run examples (comment out as needed)
    # example_basic_scan()
    # example_batch_import()
    # example_state_management()
    print("See function definitions above for usage examples")
