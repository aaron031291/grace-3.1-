import { useState, useEffect, useCallback } from 'react';
import './WebScraper.css';
import { API_BASE_URL } from '../config/api';

export default function WebScraper() {
  const [url, setUrl] = useState('');
  const [depth, setDepth] = useState(1);
  const [maxPages, setMaxPages] = useState(100);
  const [sameDomainOnly, setSameDomainOnly] = useState(true);
  const [folderPath, setFolderPath] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [scraping, setScraping] = useState(false);
  const [error, setError] = useState(null);

  const API_BASE = API_BASE_URL;

  // Restore session from localStorage on mount
  useEffect(() => {
    const savedSession = localStorage.getItem('scrapingSession');
    if (savedSession) {
      try {
        const session = JSON.parse(savedSession);
        setJobId(session.jobId);
        setStatus(session.status);
        setResults(session.results);
        setScraping(session.scraping);

        // If scraping is still in progress, resume polling
        if (session.scraping && session.jobId) {
          // The polling useEffect will handle this
        }
      } catch (err) {
        console.error('Failed to restore session:', err);
        localStorage.removeItem('scrapingSession');
      }
    }
  }, []);

  // Save session to localStorage whenever it changes
  useEffect(() => {
    if (jobId) {
      const session = {
        jobId,
        status,
        results,
        scraping
      };
      localStorage.setItem('scrapingSession', JSON.stringify(session));
    }
  }, [jobId, status, results, scraping]);

  // Poll for status updates
  useEffect(() => {
    if (!jobId || !scraping) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/scrape/status/${jobId}`);
        if (!response.ok) throw new Error('Failed to fetch status');

        const data = await response.json();
        setStatus(data);

        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          setScraping(false);
          clearInterval(interval);

          // Fetch results if completed
          if (data.status === 'completed') {
            fetchResults(jobId);
          }
        }
      } catch (err) {
        console.error('Failed to fetch status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [jobId, scraping, API_BASE, fetchResults]);

  const fetchResults = useCallback(async (id) => {
    try {
      const response = await fetch(`${API_BASE}/scrape/results/${id}`);
      if (!response.ok) throw new Error('Failed to fetch results');

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error('Failed to fetch results:', err);
      setError('Failed to fetch scraping results');
    }
  }, [API_BASE]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResults(null);

    // Validate URL
    if (!url.trim()) {
      setError('Please enter a URL');
      return;
    }

    // Validate URL format
    try {
      new URL(url);
    } catch {
      setError('Please enter a valid URL (including http:// or https://)');
      return;
    }

    // Show scraping UI immediately
    setScraping(true);
    setStatus({
      status: 'pending',
      progress_percentage: 0,
      pages_scraped: 0,
      total_pages: 1,
      pages_failed: 0,
      pages_filtered: 0,
      pages_downloaded: 0
    });

    try {
      const response = await fetch(`${API_BASE}/scrape/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url.trim(),
          depth: depth,
          max_pages: maxPages,
          same_domain_only: sameDomainOnly,
          folder_path: folderPath || undefined
        })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to start scraping');
      }

      const data = await response.json();
      setJobId(data.job_id);

    } catch (err) {
      setError(err.message);
      setScraping(false);
      setStatus(null);
    }
  };

  const handleCancel = async () => {
    if (!jobId) return;

    try {
      const response = await fetch(`${API_BASE}/scrape/cancel/${jobId}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to cancel job');

      setScraping(false);
      setStatus(prev => ({ ...prev, status: 'cancelled' }));
    } catch {
      setError('Failed to cancel scraping job');
    }
  };

  const handleReset = () => {
    setJobId(null);
    setStatus(null);
    setResults(null);
    setScraping(false);
    setError(null);
  };

  const getDepthDescription = (d) => {
    switch (d) {
      case 0: return 'Only this page';
      case 1: return 'This page + direct links';
      case 2: return 'Recursive (2 levels deep)';
      case 3: return 'Recursive (3 levels deep)';
      case 4: return 'Recursive (4 levels deep)';
      case 5: return 'Recursive (5 levels deep)';
      default: return '';
    }
  };

  return (
    <div className="web-scraper">
      <div className="scraper-header">
        <h2>🌐 Web Scraper</h2>
        <p className="scraper-description">
          Extract content from websites with depth control and semantic filtering
        </p>
      </div>

      {!scraping && !results && (
        <form onSubmit={handleSubmit} className="scraper-form">
          <div className="form-group">
            <label htmlFor="url">URL to Scrape</label>
            <input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="url-input"
              required
            />
            <span className="input-hint">
              Enter a website URL to scrape content from
            </span>
          </div>

          <div className="form-group">
            <label htmlFor="depth">
              Crawl Depth: <strong>{depth}</strong>
            </label>
            <input
              id="depth"
              type="range"
              min="0"
              max="5"
              value={depth}
              onChange={(e) => setDepth(parseInt(e.target.value))}
              className="depth-slider"
            />
            <div className="depth-hints">
              <span className="depth-hint">{getDepthDescription(depth)}</span>
            </div>
            <div className="depth-labels">
              <span>0</span>
              <span>1</span>
              <span>2</span>
              <span>3</span>
              <span>4</span>
              <span>5</span>
            </div>
          </div>

          <div className="advanced-section">
            <button
              type="button"
              className="advanced-toggle"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? '▼' : '▶'} Advanced Options
            </button>

            {showAdvanced && (
              <div className="advanced-options">
                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={sameDomainOnly}
                      onChange={(e) => setSameDomainOnly(e.target.checked)}
                    />
                    <span>Stay on same domain</span>
                  </label>
                  <span className="input-hint">
                    Only scrape pages from the same domain as the starting URL
                  </span>
                </div>

                <div className="form-group">
                  <label htmlFor="maxPages">Max Pages</label>
                  <input
                    id="maxPages"
                    type="number"
                    min="1"
                    max="1000"
                    value={maxPages}
                    onChange={(e) => setMaxPages(parseInt(e.target.value))}
                    className="number-input"
                  />
                  <span className="input-hint">
                    Maximum number of pages to scrape (1-1000)
                  </span>
                </div>

                <div className="form-group">
                  <label htmlFor="folderPath">Save to Folder (optional)</label>
                  <input
                    id="folderPath"
                    type="text"
                    value={folderPath}
                    onChange={(e) => setFolderPath(e.target.value)}
                    placeholder="scraped/my-website"
                    className="text-input"
                  />
                  <span className="input-hint">
                    Custom folder path for scraped content
                  </span>
                </div>
              </div>
            )}
          </div>

          <button type="submit" className="submit-button">
            🚀 Start Scraping
          </button>
        </form>
      )}

      {error && (
        <div className="error-message">
          <div className="error-content">
            <strong>Error:</strong> {error}
          </div>
          <button className="error-close" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}

      {scraping && status && (
        <div className="scraping-progress">
          <div className="progress-header">
            <h3>Scraping in Progress...</h3>
            <button onClick={handleCancel} className="cancel-button">
              Cancel
            </button>
          </div>

          <div className="loading-container">
            <div className="loading-spinner"></div>
            <div className="loading-text">
              {status.status === 'running' && `Discovering and scraping pages...`}
              {status.status === 'pending' && 'Initializing scraper...'}
            </div>
          </div>

          <div className="progress-stats">
            <div className="stat">
              <div className="stat-label">Pages Scraped</div>
              <div className="stat-value">{status.pages_scraped || 0}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Failed</div>
              <div className="stat-value error-text">{status.pages_failed || 0}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Filtered</div>
              <div className="stat-value" style={{ color: '#f59e0b' }}>{status.pages_filtered || 0}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Downloaded</div>
              <div className="stat-value" style={{ color: '#10b981' }}>{status.pages_downloaded || 0}</div>
            </div>
          </div>
        </div>
      )}

      {results && (
        <div className="scraping-results">
          <div className="results-header">
            <h3>Scraping Complete!</h3>
            <button onClick={handleReset} className="reset-button">
              Start New Scrape
            </button>
          </div>

          <div className="results-summary">
            <div className="summary-card">
              <div className="summary-icon">✓</div>
              <div className="summary-content">
                <div className="summary-value">{results.summary.successful}</div>
                <div className="summary-label">Pages Scraped</div>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-icon">✗</div>
              <div className="summary-content">
                <div className="summary-value">{results.summary.failed}</div>
                <div className="summary-label">Failed</div>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-icon">🔍</div>
              <div className="summary-content">
                <div className="summary-value">{results.summary.filtered || 0}</div>
                <div className="summary-label">Filtered</div>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-icon">📥</div>
              <div className="summary-content">
                <div className="summary-value">{results.summary.downloaded || 0}</div>
                <div className="summary-label">Downloaded</div>
              </div>
            </div>

            <div className="summary-card">
              <div className="summary-icon">📄</div>
              <div className="summary-content">
                <div className="summary-value">
                  {(results.summary.total_content_size / 1024).toFixed(1)} KB
                </div>
                <div className="summary-label">Total Content</div>
              </div>
            </div>
          </div>

          <div className="results-list">
            <h4>Scraped Pages</h4>
            {results.pages.length === 0 ? (
              <p className="empty-results">No pages were scraped</p>
            ) : (
              <div className="pages-table">
                {results.pages.map((page, idx) => (
                  <div key={idx} className={`page-row ${page.status}`}>
                    <div className="page-icon">
                      {page.status === 'success' ? '✓' :
                        page.status === 'downloaded' ? '📥' :
                          page.status === 'filtered' ? '🔍' : '✗'}
                    </div>
                    <div className="page-info">
                      <div className="page-title">
                        {page.status === 'downloaded' && page.file_type ?
                          `${page.file_type.toUpperCase()}` :
                          (page.title || 'Untitled')}
                      </div>
                      <div className="page-url">{page.url}</div>
                      {page.status === 'failed' && page.error_message && (
                        <div className="page-error">
                          <span className="error-icon">⚠️</span>
                          <span className="error-text">{page.error_message}</span>
                        </div>
                      )}
                      <div className="page-meta">
                        <span className="depth-badge">Depth {page.depth_level}</span>
                        {page.status === 'downloaded' && page.file_size && (
                          <span className="size-badge">
                            {(page.file_size / 1024).toFixed(1)} KB
                          </span>
                        )}
                        {page.status !== 'downloaded' && page.content_length > 0 && (
                          <span className="size-badge">
                            {(page.content_length / 1024).toFixed(1)} KB
                          </span>
                        )}
                        {page.similarity_score && (
                          <span className="similarity-badge">
                            Similarity: {(page.similarity_score * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
