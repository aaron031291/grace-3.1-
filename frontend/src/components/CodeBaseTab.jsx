import React, { useState, useEffect } from 'react';
import './CodeBaseTab.css';

const CodeBaseTab = () => {
  const [view, setView] = useState('browse'); // browse, search, history, analysis
  const [loading, setLoading] = useState(true);
  const [repositories, setRepositories] = useState([]);
  const [currentRepo, setCurrentRepo] = useState(null);
  const [currentPath, setCurrentPath] = useState('/');
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [commitHistory, setCommitHistory] = useState([]);
  const [codeAnalysis, setCodeAnalysis] = useState(null);

  useEffect(() => {
    fetchRepositories();
  }, []);

  useEffect(() => {
    if (currentRepo) {
      fetchFiles(currentRepo, currentPath);
    }
  }, [currentRepo, currentPath]);

  const fetchRepositories = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/codebase/repositories');
      if (response.ok) {
        const data = await response.json();
        setRepositories(data.repositories || []);
      } else {
        // Demo data
        setRepositories([
          {
            id: 'grace-main',
            name: 'grace_3',
            path: 'c:\\Users\\aaron\\grace_3',
            branch: 'main',
            lastCommit: '2025-01-11T10:30:00Z',
            commitCount: 156,
            contributors: 2,
            language: 'Python',
            size: '45.2 MB',
          },
          {
            id: 'grace-ml',
            name: 'ml_intelligence',
            path: 'c:\\Users\\aaron\\grace_3\\backend\\ml_intelligence',
            branch: 'main',
            lastCommit: '2025-01-11T09:15:00Z',
            commitCount: 42,
            contributors: 1,
            language: 'Python',
            size: '12.8 MB',
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching repositories:', error);
      // Demo data on error
      setRepositories([
        {
          id: 'grace-main',
          name: 'grace_3',
          path: 'c:\\Users\\aaron\\grace_3',
          branch: 'main',
          lastCommit: '2025-01-11T10:30:00Z',
          commitCount: 156,
          contributors: 2,
          language: 'Python',
          size: '45.2 MB',
        },
      ]);
    }
    setLoading(false);
  };

  const fetchFiles = async (repo, path) => {
    try {
      const response = await fetch(`/api/codebase/files?repo=${repo.id}&path=${encodeURIComponent(path)}`);
      if (response.ok) {
        const data = await response.json();
        setFiles(data.files || []);
      } else {
        // Demo file structure
        if (path === '/') {
          setFiles([
            { name: 'backend', type: 'directory', size: null, modified: '2025-01-11T10:00:00Z' },
            { name: 'frontend', type: 'directory', size: null, modified: '2025-01-11T09:30:00Z' },
            { name: 'docs', type: 'directory', size: null, modified: '2025-01-10T15:00:00Z' },
            { name: 'requirements.txt', type: 'file', size: '2.4 KB', modified: '2025-01-09T12:00:00Z', language: 'text' },
            { name: 'README.md', type: 'file', size: '8.6 KB', modified: '2025-01-08T10:00:00Z', language: 'markdown' },
            { name: 'main.py', type: 'file', size: '4.2 KB', modified: '2025-01-11T10:30:00Z', language: 'python' },
            { name: '.env.example', type: 'file', size: '1.1 KB', modified: '2025-01-05T09:00:00Z', language: 'env' },
          ]);
        } else if (path === '/backend') {
          setFiles([
            { name: '..', type: 'directory', size: null, modified: null },
            { name: 'api', type: 'directory', size: null, modified: '2025-01-11T10:00:00Z' },
            { name: 'librarian', type: 'directory', size: null, modified: '2025-01-11T09:00:00Z' },
            { name: 'ml_intelligence', type: 'directory', size: null, modified: '2025-01-11T10:30:00Z' },
            { name: 'cognitive', type: 'directory', size: null, modified: '2025-01-10T14:00:00Z' },
            { name: '__init__.py', type: 'file', size: '0 B', modified: '2025-01-05T09:00:00Z', language: 'python' },
          ]);
        } else {
          setFiles([
            { name: '..', type: 'directory', size: null, modified: null },
          ]);
        }
      }
    } catch (error) {
      console.error('Error fetching files:', error);
    }
  };

  const fetchFileContent = async (file) => {
    try {
      const response = await fetch(`/api/codebase/file?repo=${currentRepo.id}&path=${encodeURIComponent(currentPath + '/' + file.name)}`);
      if (response.ok) {
        const data = await response.json();
        setFileContent(data.content || '');
      } else {
        // Demo content
        if (file.name === 'main.py') {
          setFileContent(`"""
Grace AI System - Main Entry Point

This is the main entry point for the Grace AI system.
It initializes all components and starts the server.
"""

import asyncio
import logging
from backend.api import create_app
from backend.ml_intelligence import initialize_ml_components
from backend.librarian import initialize_librarian

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Initialize and run Grace AI system."""
    logger.info("Starting Grace AI System...")

    # Initialize ML components
    await initialize_ml_components()

    # Initialize Librarian
    await initialize_librarian()

    # Create and run the app
    app = create_app()

    logger.info("Grace AI System initialized successfully")
    return app

if __name__ == "__main__":
    asyncio.run(main())
`);
        } else if (file.name === 'README.md') {
          setFileContent(`# Grace AI System

An intelligent AI assistant with self-learning capabilities.

## Features

- **Neuro-Symbolic Reasoning**: Combines neural networks with symbolic logic
- **Self-Learning**: Continuously improves from interactions
- **Human-in-the-Loop**: Governance and approval workflows
- **Knowledge Management**: Intelligent tagging and organization

## Getting Started

1. Install dependencies: \`pip install -r requirements.txt\`
2. Configure environment: \`cp .env.example .env\`
3. Run the system: \`python main.py\`

## Architecture

Grace uses a modular architecture with the following components:

- **Frontend**: React-based UI
- **Backend**: Python/FastAPI server
- **ML Intelligence**: Machine learning components
- **Librarian**: Knowledge organization system
`);
        } else {
          setFileContent('// File content not available in demo mode');
        }
      }
    } catch (error) {
      console.error('Error fetching file content:', error);
      setFileContent('// Error loading file content');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/codebase/search?q=${encodeURIComponent(searchQuery)}&repo=${currentRepo?.id || ''}`);
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.results || []);
      } else {
        // Demo search results
        setSearchResults([
          {
            file: 'backend/ml_intelligence/kpi_tracker.py',
            line: 25,
            content: 'class KPI:',
            context: '    """Key Performance Indicator for a component."""',
            matchType: 'definition',
          },
          {
            file: 'backend/ml_intelligence/trust_engine.py',
            line: 142,
            content: 'def calculate_trust_score(self, component_name: str) -> float:',
            context: '        """Calculate trust score for a component."""',
            matchType: 'function',
          },
          {
            file: 'backend/api/librarian_api.py',
            line: 89,
            content: '@router.get("/tags")',
            context: 'async def get_all_tags():',
            matchType: 'endpoint',
          },
        ]);
      }
    } catch (error) {
      console.error('Error searching codebase:', error);
    }
    setLoading(false);
  };

  const fetchCommitHistory = async () => {
    if (!currentRepo) return;

    try {
      const response = await fetch(`/api/codebase/commits?repo=${currentRepo.id}`);
      if (response.ok) {
        const data = await response.json();
        setCommitHistory(data.commits || []);
      } else {
        // Demo commit history
        setCommitHistory([
          {
            hash: '1a058d9',
            message: 'claude 1',
            author: 'aaron',
            date: '2025-01-11T10:30:00Z',
            filesChanged: 5,
          },
          {
            hash: 'efc12c3',
            message: 'claude',
            author: 'aaron',
            date: '2025-01-11T09:15:00Z',
            filesChanged: 12,
          },
          {
            hash: 'cd56f42',
            message: 'Added neuro-symbolic reasoning engine',
            author: 'aaron',
            date: '2025-01-10T16:00:00Z',
            filesChanged: 8,
          },
          {
            hash: '268ca00',
            message: 'Fix: ignore Windows reserved filenames',
            author: 'aaron',
            date: '2025-01-10T14:00:00Z',
            filesChanged: 2,
          },
          {
            hash: 'a9383d6',
            message: 'Added cognitive retrieval endpoint, file upload progress indicator, and Genesis Key panel',
            author: 'aaron',
            date: '2025-01-09T11:00:00Z',
            filesChanged: 15,
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching commit history:', error);
    }
  };

  const fetchCodeAnalysis = async () => {
    if (!currentRepo) return;

    try {
      const response = await fetch(`/api/codebase/analysis?repo=${currentRepo.id}`);
      if (response.ok) {
        const data = await response.json();
        setCodeAnalysis(data);
      } else {
        // Demo analysis
        setCodeAnalysis({
          totalFiles: 156,
          totalLines: 24580,
          languages: [
            { name: 'Python', files: 89, lines: 18420, percentage: 75 },
            { name: 'JavaScript', files: 42, lines: 4890, percentage: 20 },
            { name: 'CSS', files: 18, lines: 980, percentage: 4 },
            { name: 'Other', files: 7, lines: 290, percentage: 1 },
          ],
          complexity: {
            average: 4.2,
            highest: { file: 'backend/cognitive/reasoning.py', score: 12 },
            lowest: { file: 'backend/__init__.py', score: 1 },
          },
          dependencies: {
            total: 45,
            direct: 28,
            dev: 17,
          },
          testCoverage: 68,
          issues: [
            { type: 'warning', message: 'Unused import in api/routes.py', line: 12 },
            { type: 'info', message: 'Consider adding type hints in utils.py', line: 45 },
          ],
        });
      }
    } catch (error) {
      console.error('Error fetching code analysis:', error);
    }
  };

  const handleFileClick = (file) => {
    if (file.type === 'directory') {
      if (file.name === '..') {
        const parts = currentPath.split('/').filter(p => p);
        parts.pop();
        setCurrentPath('/' + parts.join('/'));
      } else {
        setCurrentPath(currentPath === '/' ? `/${file.name}` : `${currentPath}/${file.name}`);
      }
      setSelectedFile(null);
      setFileContent('');
    } else {
      setSelectedFile(file);
      fetchFileContent(file);
    }
  };

  const handleRepoSelect = (repo) => {
    setCurrentRepo(repo);
    setCurrentPath('/');
    setSelectedFile(null);
    setFileContent('');
  };

  const getFileIcon = (file) => {
    if (file.type === 'directory') return '📁';
    const ext = file.name.split('.').pop().toLowerCase();
    const icons = {
      'py': '🐍',
      'js': '📜',
      'jsx': '⚛️',
      'ts': '📘',
      'tsx': '📘',
      'css': '🎨',
      'html': '🌐',
      'md': '📝',
      'json': '📋',
      'txt': '📄',
      'env': '⚙️',
      'yml': '⚙️',
      'yaml': '⚙️',
    };
    return icons[ext] || '📄';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatRelativeDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  if (loading && repositories.length === 0) {
    return (
      <div className="codebase-tab">
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading repositories...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="codebase-tab">
      <div className="codebase-header">
        <div className="header-left">
          <h2>Code Base</h2>
          <p>Browse, search, and analyze your codebase</p>
        </div>
        <div className="header-stats">
          <div className="stat-item">
            <span className="stat-value">{repositories.length}</span>
            <span className="stat-label">Repos</span>
          </div>
          {currentRepo && (
            <>
              <div className="stat-item">
                <span className="stat-value">{currentRepo.commitCount}</span>
                <span className="stat-label">Commits</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{currentRepo.size}</span>
                <span className="stat-label">Size</span>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="codebase-toolbar">
        <div className="view-tabs">
          <button
            className={view === 'browse' ? 'active' : ''}
            onClick={() => setView('browse')}
          >
            Browse
          </button>
          <button
            className={view === 'search' ? 'active' : ''}
            onClick={() => setView('search')}
          >
            Search
          </button>
          <button
            className={view === 'history' ? 'active' : ''}
            onClick={() => { setView('history'); fetchCommitHistory(); }}
          >
            History
          </button>
          <button
            className={view === 'analysis' ? 'active' : ''}
            onClick={() => { setView('analysis'); fetchCodeAnalysis(); }}
          >
            Analysis
          </button>
        </div>

        {currentRepo && (
          <div className="repo-info">
            <span className="repo-badge">{currentRepo.name}</span>
            <span className="branch-badge">🌿 {currentRepo.branch}</span>
          </div>
        )}
      </div>

      <div className="codebase-content">
        {/* Repository Selector */}
        {!currentRepo && view === 'browse' && (
          <div className="repo-selector">
            <h4>Select a Repository</h4>
            <div className="repo-list">
              {repositories.map((repo) => (
                <div
                  key={repo.id}
                  className="repo-card"
                  onClick={() => handleRepoSelect(repo)}
                >
                  <div className="repo-card-header">
                    <span className="repo-icon">📦</span>
                    <div className="repo-title">
                      <h5>{repo.name}</h5>
                      <span className="repo-path">{repo.path}</span>
                    </div>
                    <span className={`language-badge lang-${repo.language.toLowerCase()}`}>
                      {repo.language}
                    </span>
                  </div>
                  <div className="repo-card-stats">
                    <span>🌿 {repo.branch}</span>
                    <span>📝 {repo.commitCount} commits</span>
                    <span>👥 {repo.contributors} contributors</span>
                    <span>💾 {repo.size}</span>
                  </div>
                  <div className="repo-card-footer">
                    <span className="last-commit">Last commit: {formatRelativeDate(repo.lastCommit)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* File Browser */}
        {currentRepo && view === 'browse' && (
          <div className="file-browser">
            <div className="browser-sidebar">
              <div className="breadcrumb">
                <button onClick={() => { setCurrentRepo(null); setFiles([]); }}>Repos</button>
                <span>/</span>
                <button onClick={() => { setCurrentPath('/'); }}>{currentRepo.name}</button>
                {currentPath !== '/' && currentPath.split('/').filter(p => p).map((part, idx, arr) => (
                  <React.Fragment key={idx}>
                    <span>/</span>
                    <button onClick={() => setCurrentPath('/' + arr.slice(0, idx + 1).join('/'))}>
                      {part}
                    </button>
                  </React.Fragment>
                ))}
              </div>

              <div className="file-list">
                {files.map((file, idx) => (
                  <div
                    key={idx}
                    className={`file-item ${file.type} ${selectedFile?.name === file.name ? 'selected' : ''}`}
                    onClick={() => handleFileClick(file)}
                  >
                    <span className="file-icon">{getFileIcon(file)}</span>
                    <span className="file-name">{file.name}</span>
                    {file.size && <span className="file-size">{file.size}</span>}
                  </div>
                ))}
              </div>
            </div>

            <div className="file-viewer">
              {selectedFile ? (
                <>
                  <div className="viewer-header">
                    <span className="viewer-filename">
                      {getFileIcon(selectedFile)} {selectedFile.name}
                    </span>
                    <span className="viewer-meta">
                      {selectedFile.size} • Modified: {formatDate(selectedFile.modified)}
                    </span>
                  </div>
                  <div className="viewer-content">
                    <pre><code>{fileContent}</code></pre>
                  </div>
                </>
              ) : (
                <div className="viewer-empty">
                  <p>Select a file to view its contents</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Search View */}
        {view === 'search' && (
          <div className="search-view">
            <div className="search-bar">
              <input
                type="text"
                placeholder="Search code... (e.g., function names, class definitions, imports)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button onClick={handleSearch} className="btn-search">Search</button>
            </div>

            <div className="search-filters">
              <label>
                <input type="checkbox" defaultChecked /> Include definitions
              </label>
              <label>
                <input type="checkbox" defaultChecked /> Include references
              </label>
              <label>
                <input type="checkbox" /> Case sensitive
              </label>
              <label>
                <input type="checkbox" /> Regex
              </label>
            </div>

            <div className="search-results">
              {searchResults.length === 0 ? (
                <div className="empty-state">
                  <p>Enter a search query to find code</p>
                </div>
              ) : (
                searchResults.map((result, idx) => (
                  <div key={idx} className="search-result">
                    <div className="result-header">
                      <span className="result-file">{result.file}</span>
                      <span className="result-line">Line {result.line}</span>
                      <span className={`result-type type-${result.matchType}`}>{result.matchType}</span>
                    </div>
                    <div className="result-content">
                      <code>{result.content}</code>
                    </div>
                    {result.context && (
                      <div className="result-context">
                        <code>{result.context}</code>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* History View */}
        {view === 'history' && (
          <div className="history-view">
            <h4>Commit History {currentRepo && `- ${currentRepo.name}`}</h4>
            {!currentRepo ? (
              <div className="empty-state">
                <p>Select a repository to view commit history</p>
              </div>
            ) : (
              <div className="commit-list">
                {commitHistory.map((commit, idx) => (
                  <div key={idx} className="commit-item">
                    <div className="commit-hash">{commit.hash}</div>
                    <div className="commit-info">
                      <p className="commit-message">{commit.message}</p>
                      <div className="commit-meta">
                        <span className="commit-author">👤 {commit.author}</span>
                        <span className="commit-date">📅 {formatRelativeDate(commit.date)}</span>
                        <span className="commit-files">📄 {commit.filesChanged} files changed</span>
                      </div>
                    </div>
                    <div className="commit-actions">
                      <button className="btn-view">View</button>
                      <button className="btn-diff">Diff</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Analysis View */}
        {view === 'analysis' && (
          <div className="analysis-view">
            {!currentRepo ? (
              <div className="empty-state">
                <p>Select a repository to view analysis</p>
              </div>
            ) : !codeAnalysis ? (
              <div className="loading-state">
                <div className="spinner"></div>
                <p>Analyzing codebase...</p>
              </div>
            ) : (
              <>
                <div className="analysis-overview">
                  <div className="stat-card">
                    <span className="stat-value">{codeAnalysis.totalFiles}</span>
                    <span className="stat-label">Total Files</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-value">{codeAnalysis.totalLines.toLocaleString()}</span>
                    <span className="stat-label">Lines of Code</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-value">{codeAnalysis.testCoverage}%</span>
                    <span className="stat-label">Test Coverage</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-value">{codeAnalysis.dependencies.total}</span>
                    <span className="stat-label">Dependencies</span>
                  </div>
                </div>

                <div className="analysis-sections">
                  <div className="analysis-section">
                    <h4>Languages</h4>
                    <div className="language-breakdown">
                      {codeAnalysis.languages.map((lang, idx) => (
                        <div key={idx} className="language-item">
                          <div className="language-header">
                            <span className="language-name">{lang.name}</span>
                            <span className="language-stats">{lang.files} files • {lang.lines.toLocaleString()} lines</span>
                          </div>
                          <div className="language-bar">
                            <div
                              className={`language-fill lang-${lang.name.toLowerCase()}`}
                              style={{ width: `${lang.percentage}%` }}
                            ></div>
                          </div>
                          <span className="language-percent">{lang.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="analysis-section">
                    <h4>Complexity</h4>
                    <div className="complexity-stats">
                      <div className="complexity-item">
                        <span className="complexity-label">Average Complexity</span>
                        <span className="complexity-value">{codeAnalysis.complexity.average}</span>
                      </div>
                      <div className="complexity-item">
                        <span className="complexity-label">Highest</span>
                        <span className="complexity-file">{codeAnalysis.complexity.highest.file}</span>
                        <span className="complexity-score">{codeAnalysis.complexity.highest.score}</span>
                      </div>
                    </div>
                  </div>

                  <div className="analysis-section">
                    <h4>Issues ({codeAnalysis.issues.length})</h4>
                    <div className="issues-list">
                      {codeAnalysis.issues.map((issue, idx) => (
                        <div key={idx} className={`issue-item issue-${issue.type}`}>
                          <span className="issue-type">{issue.type}</span>
                          <span className="issue-message">{issue.message}</span>
                          <span className="issue-line">Line {issue.line}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CodeBaseTab;
