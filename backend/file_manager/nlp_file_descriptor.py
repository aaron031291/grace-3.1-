"""
NLP File Descriptor - Makes every file and folder in the filesystem "no-code friendly"
by generating natural language descriptions using NLP.

This system processes all files and folders, extracts their content/purpose,
and generates human-readable descriptions that non-technical users can understand.
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

from file_manager.file_handler import FileHandler
from ollama_client.client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class FileDescription:
    """Natural language description of a file."""
    path: str
    name: str
    type: str  # 'file' or 'folder'
    description: str  # Natural language description
    purpose: str  # What this file/folder is used for
    key_points: List[str]  # Key points about the file
    technical_level: str  # 'beginner', 'intermediate', 'advanced'
    related_files: List[str]  # Paths to related files
    generated_at: str
    file_size: Optional[int] = None
    extension: Optional[str] = None
    line_count: Optional[int] = None
    word_count: Optional[int] = None
    metadata: Dict[str, Any] = None


@dataclass
class FolderDescription:
    """Natural language description of a folder."""
    path: str
    name: str
    description: str  # What this folder contains
    purpose: str  # What this folder is used for
    file_count: int
    folder_count: int
    main_topics: List[str]  # Main topics/themes in this folder
    key_files: List[str]  # Important files in this folder
    generated_at: str
    metadata: Dict[str, Any] = None


class NLPFileDescriptor:
    """
    Processes all files and folders through NLP to generate natural language descriptions.
    Makes the filesystem accessible to non-technical users.
    """

    def __init__(
        self,
        root_path: str,
        ollama_client: Optional[OllamaClient] = None,
        file_handler: Optional[FileHandler] = None,
        storage_path: Optional[str] = None
    ):
        """
        Initialize NLP File Descriptor.

        Args:
            root_path: Root directory to process
            ollama_client: Ollama client for NLP (optional)
            file_handler: File handler for text extraction (optional)
            storage_path: Path to store descriptions JSON (default: root_path/.nlp_descriptions.json)
        """
        self.root_path = Path(root_path)
        self.ollama_client = ollama_client
        self.file_handler = file_handler or FileHandler()
        
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = self.root_path / ".nlp_descriptions.json"
        
        # Cache of descriptions
        self.descriptions_cache: Dict[str, Any] = {}
        self._load_cache()
        
        # Files/folders to skip
        self.skip_patterns = {
            '.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache',
            '.mypy_cache', '.idea', '.vscode', 'dist', 'build', '.eggs',
            '*.pyc', '*.pyo', '*.pyd', '.DS_Store', 'Thumbs.db'
        }
        
        logger.info(f"[NLP-DESCRIPTOR] Initialized for root: {self.root_path}")

    def _load_cache(self):
        """Load descriptions from storage."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.descriptions_cache = json.load(f)
                logger.info(f"[NLP-DESCRIPTOR] Loaded {len(self.descriptions_cache)} descriptions from cache")
        except Exception as e:
            logger.warning(f"[NLP-DESCRIPTOR] Could not load cache: {e}")
            self.descriptions_cache = {}

    def _save_cache(self):
        """Save descriptions to storage."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.descriptions_cache, f, indent=2, ensure_ascii=False)
            logger.info(f"[NLP-DESCRIPTOR] Saved {len(self.descriptions_cache)} descriptions to cache")
        except Exception as e:
            logger.error(f"[NLP-DESCRIPTOR] Could not save cache: {e}")

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path)
        for pattern in self.skip_patterns:
            if pattern in path_str:
                return True
        return False

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate file hash for change detection."""
        try:
            if not file_path.is_file():
                return ""
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def _is_file_changed(self, file_path: Path, cached_desc: Dict) -> bool:
        """Check if file has changed since last description."""
        current_hash = self._get_file_hash(file_path)
        cached_hash = cached_desc.get('file_hash', '')
        return current_hash != cached_hash

    def process_all_files(
        self,
        max_workers: int = 4,
        force_regenerate: bool = False,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process all files and folders in the filesystem.

        Args:
            max_workers: Number of parallel workers
            force_regenerate: Force regeneration even if cached
            progress_callback: Callback function(current, total, path)

        Returns:
            Dict with processing statistics
        """
        logger.info(f"[NLP-DESCRIPTOR] Starting full filesystem processing...")
        
        # Collect all files and folders
        all_items = []
        for root, dirs, files in os.walk(self.root_path):
            root_path = Path(root)
            
            # Skip directories
            if self._should_skip(root_path):
                dirs[:] = []  # Don't traverse into skipped dirs
                continue
            
            # Add folders
            for dir_name in dirs:
                dir_path = root_path / dir_name
                if not self._should_skip(dir_path):
                    all_items.append(('folder', dir_path))
            
            # Add files
            for file_name in files:
                file_path = root_path / file_name
                if not self._should_skip(file_path):
                    all_items.append(('file', file_path))
        
        total = len(all_items)
        logger.info(f"[NLP-DESCRIPTOR] Found {total} items to process")
        
        processed = 0
        failed = 0
        skipped = 0
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            for item_type, item_path in all_items:
                # Check cache
                rel_path = str(item_path.relative_to(self.root_path))
                cached = self.descriptions_cache.get(rel_path)
                
                if cached and not force_regenerate:
                    # Check if file changed
                    if item_type == 'file' and self._is_file_changed(item_path, cached):
                        # File changed, regenerate
                        pass
                    else:
                        # Use cached version
                        skipped += 1
                        processed += 1
                        if progress_callback:
                            progress_callback(processed, total, rel_path)
                        continue
                
                # Submit for processing
                future = executor.submit(
                    self._process_item,
                    item_type,
                    item_path
                )
                futures[future] = (item_type, item_path)
            
            # Collect results
            for future in as_completed(futures):
                item_type, item_path = futures[future]
                rel_path = str(item_path.relative_to(self.root_path))
                
                try:
                    result = future.result()
                    if result:
                        self.descriptions_cache[rel_path] = result
                        processed += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"[NLP-DESCRIPTOR] Error processing {rel_path}: {e}")
                    failed += 1
                
                if progress_callback:
                    progress_callback(processed + skipped, total, rel_path)
        
        # Save cache
        self._save_cache()
        
        stats = {
            'total': total,
            'processed': processed,
            'failed': failed,
            'skipped': skipped,
            'cached': len(self.descriptions_cache)
        }
        
        logger.info(f"[NLP-DESCRIPTOR] Processing complete: {stats}")
        return stats

    def _process_item(self, item_type: str, item_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single file or folder."""
        try:
            if item_type == 'file':
                return self._process_file(item_path)
            else:
                return self._process_folder(item_path)
        except Exception as e:
            logger.error(f"[NLP-DESCRIPTOR] Error processing {item_path}: {e}")
            return None

    def _process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a file and generate description."""
        try:
            rel_path = str(file_path.relative_to(self.root_path))
            
            # Extract content
            content = None
            try:
                text, error = FileHandler.extract_text(str(file_path))
                if not error and text:
                    content = text[:10000]  # Limit content for NLP
            except Exception as e:
                logger.debug(f"[NLP-DESCRIPTOR] Could not extract content from {file_path}: {e}")
            
            # Generate description using NLP
            description_data = self._generate_file_description(
                file_path=file_path,
                content=content
            )
            
            # Add metadata
            file_hash = self._get_file_hash(file_path)
            description_data['file_hash'] = file_hash
            description_data['path'] = rel_path
            description_data['type'] = 'file'
            description_data['generated_at'] = datetime.utcnow().isoformat()
            
            return description_data
            
        except Exception as e:
            logger.error(f"[NLP-DESCRIPTOR] Error processing file {file_path}: {e}")
            return None

    def _process_folder(self, folder_path: Path) -> Optional[Dict[str, Any]]:
        """Process a folder and generate description."""
        try:
            rel_path = str(folder_path.relative_to(self.root_path))
            
            # Collect folder info
            files = []
            subfolders = []
            total_size = 0
            
            try:
                for item in folder_path.iterdir():
                    if self._should_skip(item):
                        continue
                    if item.is_file():
                        files.append(item.name)
                        try:
                            total_size += item.stat().st_size
                        except:
                            pass
                    elif item.is_dir():
                        subfolders.append(item.name)
            except Exception as e:
                logger.debug(f"[NLP-DESCRIPTOR] Could not list folder {folder_path}: {e}")
            
            # Get descriptions of files in folder
            file_descriptions = []
            for file_name in files[:20]:  # Limit to 20 files
                file_rel_path = f"{rel_path}/{file_name}" if rel_path else file_name
                file_desc = self.descriptions_cache.get(file_rel_path)
                if file_desc:
                    file_descriptions.append(file_desc.get('description', ''))
            
            # Generate folder description
            description_data = self._generate_folder_description(
                folder_path=folder_path,
                files=files,
                subfolders=subfolders,
                file_descriptions=file_descriptions
            )
            
            # Add metadata
            description_data['path'] = rel_path
            description_data['type'] = 'folder'
            description_data['file_count'] = len(files)
            description_data['folder_count'] = len(subfolders)
            description_data['total_size'] = total_size
            description_data['generated_at'] = datetime.utcnow().isoformat()
            
            return description_data
            
        except Exception as e:
            logger.error(f"[NLP-DESCRIPTOR] Error processing folder {folder_path}: {e}")
            return None

    def _generate_file_description(
        self,
        file_path: Path,
        content: Optional[str]
    ) -> Dict[str, Any]:
        """Generate natural language description for a file."""
        
        file_name = file_path.name
        extension = file_path.suffix.lower()
        
        # Build context
        context_parts = [f"File name: {file_name}"]
        if extension:
            context_parts.append(f"Extension: {extension}")
        if content:
            # Use first 2000 chars for context
            content_sample = content[:2000]
            context_parts.append(f"Content preview:\n{content_sample}")
        else:
            context_parts.append("(Binary or unreadable file)")
        
        context = "\n".join(context_parts)
        
        # Generate description using LLM if available
        if self.ollama_client and self.ollama_client.is_running():
            try:
                prompt = f"""Analyze this file and provide a natural language description that a non-technical person can understand.

{context}

Provide:
1. A clear, simple description of what this file is (2-3 sentences)
2. What this file is used for (1-2 sentences)
3. 3-5 key points about this file
4. Technical level: beginner, intermediate, or advanced

Format your response as JSON:
{{
  "description": "...",
  "purpose": "...",
  "key_points": ["...", "..."],
  "technical_level": "..."
}}"""

                response = self.ollama_client.generate(
                    model="qwen2.5:latest",
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.3
                )
                
                response_text = response.get('response', '').strip()
                
                # Try to parse JSON from response
                try:
                    # Extract JSON from response (might have markdown code blocks)
                    if '```json' in response_text:
                        json_start = response_text.find('```json') + 7
                        json_end = response_text.find('```', json_start)
                        response_text = response_text[json_start:json_end].strip()
                    elif '```' in response_text:
                        json_start = response_text.find('```') + 3
                        json_end = response_text.find('```', json_start)
                        response_text = response_text[json_start:json_end].strip()
                    
                    result = json.loads(response_text)
                    return {
                        'name': file_name,
                        'description': result.get('description', ''),
                        'purpose': result.get('purpose', ''),
                        'key_points': result.get('key_points', []),
                        'technical_level': result.get('technical_level', 'intermediate'),
                        'extension': extension,
                        'file_size': file_path.stat().st_size if file_path.exists() else None,
                        'metadata': {}
                    }
                except json.JSONDecodeError:
                    # Fallback: extract description from text
                    return self._parse_description_from_text(response_text, file_name, extension)
                    
            except Exception as e:
                logger.debug(f"[NLP-DESCRIPTOR] LLM generation failed: {e}, using fallback")
        
        # Fallback: rule-based description
        return self._generate_fallback_description(file_path, content)

    def _generate_folder_description(
        self,
        folder_path: Path,
        files: List[str],
        subfolders: List[str],
        file_descriptions: List[str]
    ) -> Dict[str, Any]:
        """Generate natural language description for a folder."""
        
        folder_name = folder_path.name
        
        # Build context
        context_parts = [
            f"Folder name: {folder_name}",
            f"Contains {len(files)} files and {len(subfolders)} subfolders"
        ]
        
        if files:
            context_parts.append(f"Files: {', '.join(files[:10])}")
        if subfolders:
            context_parts.append(f"Subfolders: {', '.join(subfolders[:10])}")
        if file_descriptions:
            context_parts.append(f"File descriptions: {'; '.join(file_descriptions[:5])}")
        
        context = "\n".join(context_parts)
        
        # Generate description using LLM if available
        if self.ollama_client and self.ollama_client.is_running():
            try:
                prompt = f"""Analyze this folder and provide a natural language description.

{context}

Provide:
1. A clear description of what this folder contains (2-3 sentences)
2. What this folder is used for (1-2 sentences)
3. Main topics/themes in this folder (3-5 items)
4. Key files in this folder (3-5 file names)

Format your response as JSON:
{{
  "description": "...",
  "purpose": "...",
  "main_topics": ["...", "..."],
  "key_files": ["...", "..."]
}}"""

                response = self.ollama_client.generate(
                    model="qwen2.5:latest",
                    prompt=prompt,
                    max_tokens=400,
                    temperature=0.3
                )
                
                response_text = response.get('response', '').strip()
                
                # Try to parse JSON
                try:
                    if '```json' in response_text:
                        json_start = response_text.find('```json') + 7
                        json_end = response_text.find('```', json_start)
                        response_text = response_text[json_start:json_end].strip()
                    elif '```' in response_text:
                        json_start = response_text.find('```') + 3
                        json_end = response_text.find('```', json_start)
                        response_text = response_text[json_start:json_end].strip()
                    
                    result = json.loads(response_text)
                    return {
                        'name': folder_name,
                        'description': result.get('description', ''),
                        'purpose': result.get('purpose', ''),
                        'main_topics': result.get('main_topics', []),
                        'key_files': result.get('key_files', []),
                        'metadata': {}
                    }
                except json.JSONDecodeError:
                    return self._parse_folder_description_from_text(response_text, folder_name)
                    
            except Exception as e:
                logger.debug(f"[NLP-DESCRIPTOR] LLM generation failed: {e}, using fallback")
        
        # Fallback: rule-based description
        return self._generate_fallback_folder_description(folder_path, files, subfolders)

    def _parse_description_from_text(self, text: str, file_name: str, extension: str) -> Dict[str, Any]:
        """Parse description from LLM text response (fallback)."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        description = lines[0] if lines else f"This is a {extension or 'file'} file named {file_name}."
        
        return {
            'name': file_name,
            'description': description,
            'purpose': description,
            'key_points': lines[1:4] if len(lines) > 1 else [],
            'technical_level': 'intermediate',
            'extension': extension,
            'metadata': {}
        }

    def _parse_folder_description_from_text(self, text: str, folder_name: str) -> Dict[str, Any]:
        """Parse folder description from LLM text response (fallback)."""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        description = lines[0] if lines else f"This folder contains files and subfolders."
        
        return {
            'name': folder_name,
            'description': description,
            'purpose': description,
            'main_topics': [],
            'key_files': [],
            'metadata': {}
        }

    def _generate_fallback_description(self, file_path: Path, content: Optional[str]) -> Dict[str, Any]:
        """Generate fallback description when LLM is unavailable."""
        file_name = file_path.name
        extension = file_path.suffix.lower()
        
        # Simple heuristics
        if extension == '.py':
            description = f"Python code file: {file_name}. Contains Python programming code."
            purpose = "Used to implement Python functionality."
            technical_level = "intermediate"
        elif extension == '.js':
            description = f"JavaScript code file: {file_name}. Contains JavaScript code."
            purpose = "Used for web development and client-side scripting."
            technical_level = "intermediate"
        elif extension == '.md':
            description = f"Markdown document: {file_name}. Contains formatted text documentation."
            purpose = "Used for documentation and formatted text."
            technical_level = "beginner"
        elif extension == '.json':
            description = f"JSON data file: {file_name}. Contains structured data."
            purpose = "Used to store and exchange data."
            technical_level = "beginner"
        elif extension == '.txt':
            description = f"Text file: {file_name}. Contains plain text."
            purpose = "Used to store text information."
            technical_level = "beginner"
        else:
            description = f"File: {file_name}. {extension or 'Unknown'} file type."
            purpose = "File storage."
            technical_level = "intermediate"
        
        key_points = [
            f"File extension: {extension or 'none'}",
            f"File name: {file_name}"
        ]
        
        if content:
            word_count = len(content.split())
            key_points.append(f"Contains approximately {word_count} words")
        
        return {
            'name': file_name,
            'description': description,
            'purpose': purpose,
            'key_points': key_points,
            'technical_level': technical_level,
            'extension': extension,
            'file_size': file_path.stat().st_size if file_path.exists() else None,
            'metadata': {}
        }

    def _generate_fallback_folder_description(
        self,
        folder_path: Path,
        files: List[str],
        subfolders: List[str]
    ) -> Dict[str, Any]:
        """Generate fallback folder description."""
        folder_name = folder_path.name
        
        description = f"Folder: {folder_name}. Contains {len(files)} files"
        if subfolders:
            description += f" and {len(subfolders)} subfolders"
        description += "."
        
        purpose = f"Organizes {len(files)} files and related content."
        
        # Infer topics from file names
        main_topics = []
        extensions = [Path(f).suffix.lower() for f in files]
        if '.py' in extensions:
            main_topics.append("Python code")
        if '.js' in extensions or '.ts' in extensions:
            main_topics.append("JavaScript/TypeScript")
        if '.md' in extensions:
            main_topics.append("Documentation")
        
        key_files = files[:5]  # First 5 files
        
        return {
            'name': folder_name,
            'description': description,
            'purpose': purpose,
            'main_topics': main_topics,
            'key_files': key_files,
            'metadata': {}
        }

    def get_description(self, path: str) -> Optional[Dict[str, Any]]:
        """Get description for a specific path."""
        return self.descriptions_cache.get(path)

    def get_all_descriptions(self) -> Dict[str, Any]:
        """Get all descriptions."""
        return self.descriptions_cache.copy()

    def search_descriptions(self, query: str) -> List[Dict[str, Any]]:
        """Search descriptions by keyword."""
        results = []
        query_lower = query.lower()
        
        for path, desc in self.descriptions_cache.items():
            if query_lower in path.lower():
                results.append({'path': path, **desc})
            elif query_lower in desc.get('description', '').lower():
                results.append({'path': path, **desc})
            elif query_lower in desc.get('purpose', '').lower():
                results.append({'path': path, **desc})
        
        return results
