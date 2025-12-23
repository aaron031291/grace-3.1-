"""
Version control service using Dulwich for Git operations.
Provides functionality to track, retrieve, and visualize code versions.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dulwich.repo import Repo
from dulwich.objects import Commit
from pathlib import Path


class GitService:
    """Service for managing Git operations using Dulwich."""

    def __init__(self, repo_path: str):
        """
        Initialize Git service for a repository.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = repo_path
        self.repo = None
        self._initialize_repo()

    def _initialize_repo(self):
        """Initialize or open the git repository."""
        try:
            if os.path.exists(os.path.join(self.repo_path, ".git")):
                self.repo = Repo(self.repo_path)
            else:
                self.repo = Repo.init(self.repo_path)
        except Exception as e:
            raise Exception(f"Failed to initialize repository: {e}")

    def get_commits(self, limit: int = 100, skip: int = 0) -> List[Dict]:
        """
        Get commit history.
        
        Args:
            limit: Maximum number of commits to retrieve
            skip: Number of commits to skip
            
        Returns:
            List of commit information dictionaries
        """
        try:
            commits = []
            try:
                head = self.repo.head()
                walker = self.repo.get_walker(head)
                for idx, entry in enumerate(walker):
                    if idx < skip:
                        continue
                    if idx >= skip + limit:
                        break
                    
                    # entry.commit is bytes, convert to actual commit object
                    commit_sha = entry.commit if isinstance(entry.commit, bytes) else entry.commit.id
                    commit = self.repo[commit_sha]
                    commits.append(self._format_commit(commit))
            except Exception:
                # Repository might be empty or HEAD doesn't exist
                pass
            
            return commits
        except Exception as e:
            raise Exception(f"Failed to get commits: {e}")

    def get_commit_details(self, commit_sha: str) -> Dict:
        """
        Get detailed information about a specific commit.
        
        Args:
            commit_sha: SHA of the commit
            
        Returns:
            Detailed commit information
        """
        try:
            commit_obj = self.repo[commit_sha.encode() if isinstance(commit_sha, str) else commit_sha]
            
            if not isinstance(commit_obj, Commit):
                raise ValueError("Object is not a commit")
            
            return self._format_commit(commit_obj)
        except Exception as e:
            raise Exception(f"Failed to get commit details: {e}")

    def get_commit_diff(self, commit_sha: str) -> Dict:
        """
        Get the diff/changes for a specific commit.
        
        Args:
            commit_sha: SHA of the commit
            
        Returns:
            Dictionary with file changes and diffs
        """
        try:
            commit_obj = self.repo[commit_sha.encode() if isinstance(commit_sha, str) else commit_sha]
            
            if not isinstance(commit_obj, Commit):
                raise ValueError("Object is not a commit")
            
            diff_result = {
                "commit_sha": commit_sha,
                "files_changed": [],
                "stats": {
                    "additions": 0,
                    "deletions": 0,
                    "files_modified": 0
                }
            }
            
            # Get diff between this commit and its parent
            if commit_obj.parents:
                parent_commit = self.repo[commit_obj.parents[0]]
                parent_tree = self.repo[parent_commit.tree]
                commit_tree = self.repo[commit_obj.tree]
                
                # Get all files in both trees
                parent_files = self._get_tree_files_with_content(parent_tree)
                commit_files = self._get_tree_files_with_content(commit_tree)
                
                # Find changes
                all_files = set(parent_files.keys()) | set(commit_files.keys())
                for file_path in all_files:
                    if file_path not in parent_files:
                        # File added
                        status = "added"
                        additions = len(commit_files[file_path].get("content", "").split("\n"))
                        deletions = 0
                    elif file_path not in commit_files:
                        # File deleted
                        status = "deleted"
                        additions = 0
                        deletions = len(parent_files[file_path].get("content", "").split("\n"))
                    else:
                        # File modified - count line differences
                        status = "modified"
                        parent_content = parent_files[file_path].get("content", "")
                        commit_content = commit_files[file_path].get("content", "")
                        parent_lines = parent_content.split("\n") if parent_content else []
                        commit_lines = commit_content.split("\n") if commit_content else []
                        
                        # Simple line count difference (not a perfect diff, but good enough)
                        additions = max(0, len(commit_lines) - len(parent_lines))
                        deletions = max(0, len(parent_lines) - len(commit_lines))
                    
                    file_info = {
                        "path": file_path,
                        "status": status,
                        "additions": additions,
                        "deletions": deletions
                    }
                    diff_result["files_changed"].append(file_info)
                    diff_result["stats"]["files_modified"] += 1
                    diff_result["stats"]["additions"] += additions
                    diff_result["stats"]["deletions"] += deletions
            else:
                # Initial commit - all files are added
                commit_tree = self.repo[commit_obj.tree]
                commit_files = self._get_tree_files_with_content(commit_tree)
                for file_path in commit_files:
                    additions = len(commit_files[file_path].get("content", "").split("\n"))
                    file_info = {
                        "path": file_path,
                        "status": "added",
                        "additions": additions,
                        "deletions": 0
                    }
                    diff_result["files_changed"].append(file_info)
                    diff_result["stats"]["files_modified"] += 1
                    diff_result["stats"]["additions"] += additions
            
            return diff_result
        except Exception as e:
            raise Exception(f"Failed to get commit diff: {e}")

    def get_file_history(self, file_path: str, limit: int = 50) -> List[Dict]:
        """
        Get commit history for a specific file.
        
        Args:
            file_path: Path to the file
            limit: Maximum number of commits to retrieve
            
        Returns:
            List of commits affecting the file
        """
        try:
            commits = []
            try:
                head = self.repo.head()
                walker = self.repo.get_walker(head, paths=[file_path.encode()])
                for idx, entry in enumerate(walker):
                    if idx >= limit:
                        break
                    commit_sha = entry.commit if isinstance(entry.commit, bytes) else entry.commit.id
                    commit = self.repo[commit_sha]
                    commits.append(self._format_commit(commit))
            except Exception:
                # File might not exist or repo is empty
                pass
            
            return commits
        except Exception as e:
            raise Exception(f"Failed to get file history: {e}")

    def get_tree_structure(self, commit_sha: Optional[str] = None, path: str = "") -> Dict:
        """
        Get the file tree structure at a specific commit.
        
        Args:
            commit_sha: SHA of the commit (uses HEAD if not specified)
            path: Subdirectory path
            
        Returns:
            Tree structure dictionary
        """
        try:
            if commit_sha:
                commit = self.repo[commit_sha.encode() if isinstance(commit_sha, str) else commit_sha]
                tree_obj = self.repo[commit.tree]
            else:
                try:
                    head = self.repo.head()
                    head_commit = self.repo[head]
                    tree_obj = self.repo[head_commit.tree]
                except Exception:
                    # Repository might be empty
                    return {"type": "tree", "path": path, "children": []}
            
            # Navigate to the specified path if provided
            if path:
                path_parts = path.split("/")
                for part in path_parts:
                    if not part:  # Skip empty parts
                        continue
                    # Find the child with this name
                    found = False
                    for item in tree_obj.items():
                        name = item.path.decode() if isinstance(item.path, bytes) else item.path
                        if name == part:
                            # Check if it's a tree (directory)
                            if (item.mode & 0o40000) == 0o40000:
                                tree_obj = self.repo[item.sha]
                                found = True
                                break
                    if not found:
                        # Path not found, return empty tree
                        return {"type": "tree", "path": path, "children": []}
            
            return self._build_tree_dict(tree_obj, path)
        except Exception as e:
            raise Exception(f"Failed to get tree structure: {e}")

    def get_module_statistics(self) -> Dict:
        """
        Get statistics about modules/directories in the repository.
        
        Returns:
            Dictionary with module statistics
        """
        try:
            stats = {
                "modules": [],
                "total_commits": 0,
                "last_commit_date": None
            }
            
            try:
                head = self.repo.head()
                walker = self.repo.get_walker(head)
                commits_list = list(walker)
                stats["total_commits"] = len(commits_list)
                
                if commits_list:
                    commit_sha = commits_list[0].commit if isinstance(commits_list[0].commit, bytes) else commits_list[0].commit.id
                    latest_commit = self.repo[commit_sha]
                    stats["last_commit_date"] = datetime.fromtimestamp(
                        latest_commit.commit_time
                    ).isoformat()
                
                # Get modules (subdirectories of backend folder only)
                head_commit = self.repo[head]
                tree_obj = self.repo[head_commit.tree]
                
                # Find the backend folder in the root tree
                backend_sha = None
                for item in tree_obj.items():
                    name = item.path.decode() if isinstance(item.path, bytes) else item.path
                    if name == "backend" and (item.mode & 0o40000) == 0o40000:
                        backend_sha = item.sha
                        break
                
                # If backend folder exists, get its contents
                if backend_sha:
                    backend_tree = self.repo[backend_sha]
                    for item in backend_tree.items():
                        name = item.path.decode() if isinstance(item.path, bytes) else item.path
                        # Only include directories (modules), skip files and hidden items
                        is_dir = (item.mode & 0o40000) == 0o40000
                        if is_dir and not name.startswith(".") and not name.startswith("__"):
                            stats["modules"].append({
                                "name": name,
                                "is_dir": is_dir
                            })
            except Exception:
                # Repository might be empty
                pass
            
            return stats
        except Exception as e:
            raise Exception(f"Failed to get module statistics: {e}")

    def revert_to_commit(self, commit_sha: str) -> Dict:
        """
        Revert the working directory to a specific commit.
        
        Args:
            commit_sha: SHA of the commit to revert to
            
        Returns:
            Dictionary with revert result
        """
        try:
            commit = self.repo[commit_sha.encode() if isinstance(commit_sha, str) else commit_sha]
            self.repo.reset_index(commit.tree)
            
            return {
                "success": True,
                "message": f"Successfully reverted to commit {commit_sha}",
                "commit_sha": commit_sha
            }
        except Exception as e:
            raise Exception(f"Failed to revert to commit: {e}")

    def _format_commit(self, commit: Commit) -> Dict:
        """
        Format a commit object into a dictionary.
        
        Args:
            commit: Dulwich Commit object
            
        Returns:
            Formatted commit dictionary
        """
        # Parse author and committer - format is "Name <email>"
        author_str = commit.author.decode() if isinstance(commit.author, bytes) else commit.author
        committer_str = commit.committer.decode() if isinstance(commit.committer, bytes) else commit.committer
        
        # Extract email from author string
        author_email = ""
        author_name = author_str
        if "<" in author_str and ">" in author_str:
            author_name = author_str[:author_str.index("<")].strip()
            author_email = author_str[author_str.index("<")+1:author_str.index(">")]
        
        # Extract email from committer string
        committer_email = ""
        committer_name = committer_str
        if "<" in committer_str and ">" in committer_str:
            committer_name = committer_str[:committer_str.index("<")].strip()
            committer_email = committer_str[committer_str.index("<")+1:committer_str.index(">")]
        
        return {
            "sha": commit.id.decode() if isinstance(commit.id, bytes) else commit.id,
            "message": commit.message.decode() if isinstance(commit.message, bytes) else commit.message,
            "author": author_name,
            "author_email": author_email,
            "committer": committer_name,
            "timestamp": datetime.fromtimestamp(commit.commit_time).isoformat(),
            "parent_shas": [p.decode() if isinstance(p, bytes) else p for p in commit.parents]
        }

    def _build_tree_dict(self, tree_obj, path: str = "") -> Dict:
        """
        Build a tree structure dictionary recursively.
        
        Args:
            tree_obj: Dulwich Tree object
            path: Current path in tree
            
        Returns:
            Tree structure dictionary
        """
        tree_data = {
            "type": "tree",
            "path": path,
            "children": []
        }
        
        try:
            for item in tree_obj.items():
                # Dulwich returns TreeEntry namedtuples with (path, mode, sha)
                name = item.path.decode() if isinstance(item.path, bytes) else item.path
                item_mode = item.mode
                
                is_dir = (item_mode & 0o40000) == 0o40000
                
                child_path = f"{path}/{name}" if path else name
                
                child_node = {
                    "type": "tree" if is_dir else "blob",
                    "name": name,
                    "path": child_path,
                    "mode": item_mode
                }
                
                tree_data["children"].append(child_node)
        except Exception:
            pass
        
        return tree_data

    def _get_tree_files(self, tree_obj, prefix: str = "") -> Dict[str, str]:
        """
        Recursively get all files in a tree.
        
        Args:
            tree_obj: Dulwich Tree object
            prefix: Path prefix
            
        Returns:
            Dictionary mapping file paths to SHAs
        """
        files = {}
        try:
            for item in tree_obj.items():
                name = item.path.decode() if isinstance(item.path, bytes) else item.path
                file_path = f"{prefix}/{name}" if prefix else name
                is_dir = (item.mode & 0o40000) == 0o40000
                
                if is_dir:
                    # Recursively get files from subdirectory
                    sub_tree = self.repo[item.sha]
                    files.update(self._get_tree_files(sub_tree, file_path))
                else:
                    # It's a file
                    files[file_path] = item.sha
        except Exception:
            pass
        
        return files

    def _get_tree_files_with_content(self, tree_obj, prefix: str = "") -> Dict[str, Dict]:
        """
        Recursively get all files in a tree with their content.
        
        Args:
            tree_obj: Dulwich Tree object
            prefix: Path prefix
            
        Returns:
            Dictionary mapping file paths to {sha, content}
        """
        files = {}
        try:
            for item in tree_obj.items():
                name = item.path.decode() if isinstance(item.path, bytes) else item.path
                file_path = f"{prefix}/{name}" if prefix else name
                is_dir = (item.mode & 0o40000) == 0o40000
                
                if is_dir:
                    # Recursively get files from subdirectory
                    sub_tree = self.repo[item.sha]
                    files.update(self._get_tree_files_with_content(sub_tree, file_path))
                else:
                    # It's a file - read content
                    try:
                        blob = self.repo[item.sha]
                        content = blob.data.decode('utf-8', errors='ignore') if hasattr(blob, 'data') else ""
                        files[file_path] = {
                            "sha": item.sha,
                            "content": content
                        }
                    except Exception:
                        # If we can't read the file, just skip it
                        files[file_path] = {
                            "sha": item.sha,
                            "content": ""
                        }
        except Exception:
            pass
        
        return files

    def get_diff_between_commits(self, sha1: str, sha2: str) -> Dict:
        """
        Get the difference between two commits.
        
        Args:
            sha1: First commit SHA
            sha2: Second commit SHA
            
        Returns:
            Dictionary with differences
        """
        try:
            commit1 = self.repo[sha1.encode() if isinstance(sha1, str) else sha1]
            commit2 = self.repo[sha2.encode() if isinstance(sha2, str) else sha2]
            
            diff_result = {
                "from_commit": sha1,
                "to_commit": sha2,
                "files_changed": [],
                "stats": {
                    "additions": 0,
                    "deletions": 0,
                    "files_modified": 0
                }
            }
            
            tree1 = self.repo[commit1.tree]
            tree2 = self.repo[commit2.tree]
            
            # Get all files in both trees
            files1 = self._get_tree_files(tree1)
            files2 = self._get_tree_files(tree2)
            
            # Find changes
            all_files = set(files1.keys()) | set(files2.keys())
            for file_path in all_files:
                if file_path not in files1:
                    status = "added"
                elif file_path not in files2:
                    status = "deleted"
                else:
                    status = "modified"
                
                file_info = {
                    "path": file_path,
                    "status": status,
                    "additions": 0,
                    "deletions": 0
                }
                diff_result["files_changed"].append(file_info)
                diff_result["stats"]["files_modified"] += 1
            
            return diff_result
        except Exception as e:
            raise Exception(f"Failed to get diff between commits: {e}")
