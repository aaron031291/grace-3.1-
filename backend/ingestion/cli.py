#!/usr/bin/env python3
"""
Command-line utility for managing file-based document ingestion.
Provides commands to scan, watch, and manage knowledge base files.
"""

import sys
import os
import logging
import argparse
from pathlib import Path
from typing import Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.file_manager import IngestionFileManager
from embedding.embedder import get_embedding_model
from api.ingest import get_ingestion_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FileIngestionCLI:
    """Command-line interface for file ingestion management."""
    
    def __init__(self, knowledge_base_path: str = "backend/knowledge_base"):
        """Initialize CLI."""
        self.knowledge_base_path = knowledge_base_path
        self.file_manager: Optional[IngestionFileManager] = None
    
    def init_manager(self) -> bool:
        """Initialize file manager."""
        try:
            if self.file_manager is None:
                logger.info("Initializing file ingestion manager...")
                embedding_model = get_embedding_model()
                ingestion_service = get_ingestion_service()
                self.file_manager = IngestionFileManager(
                    knowledge_base_path=self.knowledge_base_path,
                    embedding_model=embedding_model,
                    ingestion_service=ingestion_service,
                )
                logger.info("✓ File manager initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize file manager: {e}")
            return False
    
    def scan(self, args: argparse.Namespace) -> int:
        """Scan knowledge base for changes."""
        if not self.init_manager():
            return 1
        
        try:
            logger.info(f"Scanning knowledge base: {self.knowledge_base_path}")
            results = self.file_manager.scan_directory()
            
            if not results:
                logger.info("No changes detected")
                return 0
            
            successful = sum(1 for r in results if r.success)
            failed = sum(1 for r in results if not r.success)
            
            print(f"\n{'='*80}")
            print(f"SCAN RESULTS: {len(results)} changes processed")
            print(f"  ✓ Successful: {successful}")
            print(f"  ✗ Failed: {failed}")
            print(f"{'='*80}\n")
            
            for result in results:
                status = "✓" if result.success else "✗"
                print(f"{status} [{result.change_type.upper()}] {result.filepath}")
                if result.document_id:
                    print(f"    Document ID: {result.document_id}")
                if result.message:
                    print(f"    Message: {result.message}")
                if result.error:
                    print(f"    Error: {result.error}")
            
            print()
            return 0 if failed == 0 else 1
        
        except Exception as e:
            logger.error(f"Error scanning knowledge base: {e}", exc_info=True)
            return 1
    
    def watch(self, args: argparse.Namespace) -> int:
        """Watch knowledge base for changes (continuous mode)."""
        if not self.init_manager():
            return 1
        
        try:
            interval = args.interval or 5
            logger.info(f"Watching knowledge base (scan interval: {interval}s)")
            logger.info("Press Ctrl+C to stop\n")
            
            self.file_manager.watch_and_process(continuous=True)
            return 0
        
        except KeyboardInterrupt:
            logger.info("\nWatcher stopped")
            return 0
        except Exception as e:
            logger.error(f"Error in watch mode: {e}", exc_info=True)
            return 1
    
    def init_git(self, args: argparse.Namespace) -> int:
        """Initialize git repository."""
        if not self.init_manager():
            return 1
        
        try:
            logger.info("Initializing git repository...")
            success = self.file_manager.git_tracker.initialize_git()
            
            if success:
                logger.info("✓ Git repository initialized")
                return 0
            else:
                logger.error("Failed to initialize git repository")
                return 1
        
        except Exception as e:
            logger.error(f"Error initializing git: {e}")
            return 1
    
    def list_tracked(self, args: argparse.Namespace) -> int:
        """List tracked files."""
        if not self.init_manager():
            return 1
        
        try:
            tracked = self.file_manager.file_states
            
            print(f"\nTracked Files: {len(tracked)}")
            print("="*80)
            
            if not tracked:
                print("No tracked files")
            else:
                for filepath in sorted(tracked.keys()):
                    hash_val = tracked[filepath]
                    print(f"  {filepath}")
                    print(f"    Hash: {hash_val}")
            
            print()
            return 0
        
        except Exception as e:
            logger.error(f"Error listing tracked files: {e}")
            return 1
    
    def clear_state(self, args: argparse.Namespace) -> int:
        """Clear tracking state."""
        if not self.init_manager():
            return 1
        
        try:
            count = len(self.file_manager.file_states)
            
            if count == 0:
                logger.info("No tracked files to clear")
                return 0
            
            if not args.force:
                response = input(f"Clear {count} tracked files? [y/N] ")
                if response.lower() != 'y':
                    logger.info("Cancelled")
                    return 0
            
            logger.info(f"Clearing {count} tracked files...")
            self.file_manager.file_states.clear()
            self.file_manager._save_state()
            logger.info("✓ Tracking state cleared")
            return 0
        
        except Exception as e:
            logger.error(f"Error clearing state: {e}")
            return 1
    
    def status(self, args: argparse.Namespace) -> int:
        """Show file manager status."""
        if not self.init_manager():
            return 1
        
        try:
            git_dir = self.file_manager.knowledge_base_path / ".git"
            tracked_count = len(self.file_manager.file_states)
            
            print(f"\nFile Manager Status")
            print("="*80)
            print(f"Knowledge Base: {self.file_manager.knowledge_base_path}")
            print(f"Tracked Files: {tracked_count}")
            print(f"Git Initialized: {'Yes' if git_dir.exists() else 'No'}")
            print(f"State File: {self.file_manager.state_file}")
            print()
            
            return 0
        
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage file-based document ingestion for knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan knowledge base for changes
  python -m ingestion.cli scan
  
  # Watch knowledge base for changes (continuous)
  python -m ingestion.cli watch --interval 5
  
  # Initialize git repository
  python -m ingestion.cli init-git
  
  # List tracked files
  python -m ingestion.cli list-tracked
  
  # Clear tracking state
  python -m ingestion.cli clear-state --force
  
  # Show status
  python -m ingestion.cli status
        """
    )
    
    parser.add_argument(
        "--kb-path",
        default="backend/knowledge_base",
        help="Path to knowledge base directory (default: backend/knowledge_base)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Scan command
    subparsers.add_parser(
        "scan",
        help="Scan knowledge base for file changes and process them"
    )
    
    # Watch command
    watch_parser = subparsers.add_parser(
        "watch",
        help="Watch knowledge base for changes (continuous mode)"
    )
    watch_parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Scan interval in seconds (default: 5)"
    )
    
    # Init-git command
    subparsers.add_parser(
        "init-git",
        help="Initialize git repository for tracking"
    )
    
    # List-tracked command
    subparsers.add_parser(
        "list-tracked",
        help="List all tracked files"
    )
    
    # Clear-state command
    clear_parser = subparsers.add_parser(
        "clear-state",
        help="Clear file tracking state"
    )
    clear_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    # Status command
    subparsers.add_parser(
        "status",
        help="Show file manager status"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if command was provided
    if not args.command:
        parser.print_help()
        return 1
    
    # Create CLI instance
    cli = FileIngestionCLI(knowledge_base_path=args.kb_path)
    
    # Dispatch command
    if args.command == "scan":
        return cli.scan(args)
    elif args.command == "watch":
        return cli.watch(args)
    elif args.command == "init-git":
        return cli.init_git(args)
    elif args.command == "list-tracked":
        return cli.list_tracked(args)
    elif args.command == "clear-state":
        return cli.clear_state(args)
    elif args.command == "status":
        return cli.status(args)
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
