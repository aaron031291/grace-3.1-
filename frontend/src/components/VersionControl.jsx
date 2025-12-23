import { useState, useEffect } from "react";
import "./VersionControl.css";
import CommitTimeline from "./version_control/CommitTimeline";
import GitTree from "./version_control/GitTree";
import DiffViewer from "./version_control/DiffViewer";
import ModuleHistory from "./version_control/ModuleHistory";
import RevertModal from "./version_control/RevertModal";

export default function VersionControl() {
  const [activeView, setActiveView] = useState("timeline");
  const [commits, setCommits] = useState([]);
  const [selectedCommit, setSelectedCommit] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [treeData, setTreeData] = useState(null);
  const [moduleStats, setModuleStats] = useState(null);
  const [showRevertModal, setShowRevertModal] = useState(false);
  const [diffData, setDiffData] = useState(null);

  useEffect(() => {
    fetchCommits();
    fetchModuleStatistics();
  }, []);

  useEffect(() => {
    if (selectedCommit && activeView === "diff") {
      fetchCommitDiff(selectedCommit.sha);
    }
    if (selectedCommit && activeView === "tree") {
      fetchTreeStructure(selectedCommit.sha);
    }
  }, [selectedCommit, activeView]);

  const fetchCommits = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8000/api/version-control/commits?limit=100"
      );
      if (!response.ok) throw new Error("Failed to fetch commits");
      const data = await response.json();
      setCommits(data.commits);
      if (data.commits.length > 0) {
        setSelectedCommit(data.commits[0]);
      }
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error("Error fetching commits:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCommitDiff = async (sha) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/version-control/commits/${sha}/diff`
      );
      if (!response.ok) throw new Error("Failed to fetch diff");
      const data = await response.json();
      setDiffData(data);
    } catch (err) {
      setError(err.message);
      console.error("Error fetching diff:", err);
    }
  };

  const fetchTreeStructure = async (sha, path = "") => {
    try {
      const params = new URLSearchParams();
      if (sha) params.append("commit_sha", sha);
      if (path) params.append("path", path);
      const response = await fetch(
        `http://localhost:8000/api/version-control/tree?${params.toString()}`
      );
      if (!response.ok) throw new Error("Failed to fetch tree");
      const data = await response.json();
      setTreeData(data);
    } catch (err) {
      setError(err.message);
      console.error("Error fetching tree:", err);
    }
  };

  const fetchModuleStatistics = async () => {
    try {
      const response = await fetch(
        "http://localhost:8000/api/version-control/modules/statistics"
      );
      if (!response.ok) throw new Error("Failed to fetch module statistics");
      const data = await response.json();
      setModuleStats(data);
    } catch (err) {
      console.error("Error fetching module statistics:", err);
    }
  };

  const handleRevert = async (commitSha) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/version-control/revert?commit_sha=${commitSha}`,
        {
          method: "POST",
        }
      );
      if (!response.ok) throw new Error("Failed to revert");
      const data = await response.json();
      setShowRevertModal(false);
      fetchCommits();
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error("Error reverting:", err);
    }
  };

  return (
    <div className="version-control">
      <div className="vc-header">
        <h2>Version Control</h2>
        <div className="vc-stats">
          {moduleStats && (
            <>
              <span className="stat-item">
                <span className="stat-label">Total Commits:</span>
                <span className="stat-value">{moduleStats.total_commits}</span>
              </span>
              {moduleStats.last_commit_date && (
                <span className="stat-item">
                  <span className="stat-label">Last Commit:</span>
                  <span className="stat-value">
                    {new Date(
                      moduleStats.last_commit_date
                    ).toLocaleDateString()}
                  </span>
                </span>
              )}
            </>
          )}
        </div>
      </div>

      {error && <div className="vc-error">Error: {error}</div>}

      <div className="vc-navigation">
        <button
          className={`vc-nav-button ${
            activeView === "timeline" ? "active" : ""
          }`}
          onClick={() => setActiveView("timeline")}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M12 2v20M2 12h20" />
            <circle cx="12" cy="12" r="1" />
          </svg>
          Timeline
        </button>
        <button
          className={`vc-nav-button ${activeView === "tree" ? "active" : ""}`}
          onClick={() => setActiveView("tree")}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M12 2l5 3v5l-5 3-5-3V5l5-3z" />
            <path d="M7 10v5l5 3 5-3v-5" />
          </svg>
          Tree
        </button>
        <button
          className={`vc-nav-button ${activeView === "diff" ? "active" : ""}`}
          onClick={() => setActiveView("diff")}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M6 9l6 6 6-6" />
            <line x1="3" y1="12" x2="21" y2="12" />
          </svg>
          Uncommited Changes
        </button>
        <button
          className={`vc-nav-button ${
            activeView === "modules" ? "active" : ""
          }`}
          onClick={() => setActiveView("modules")}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
          </svg>
          Modules
        </button>
      </div>

      <div className="vc-content">
        {loading && (
          <div className="vc-loading">Loading version history...</div>
        )}

        {activeView === "timeline" && !loading && (
          <div className="vc-view">
            <div className="vc-timeline-container">
              <CommitTimeline
                commits={commits}
                selectedCommit={selectedCommit}
                onSelectCommit={setSelectedCommit}
                onRevert={() => setShowRevertModal(true)}
              />
            </div>
            {selectedCommit && (
              <div className="vc-commit-details">
                <h3>Commit Details</h3>
                <div className="commit-info">
                  <div className="info-row">
                    <span className="info-label">SHA:</span>
                    <span className="info-value monospace">
                      {selectedCommit.sha.substring(0, 7)}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Message:</span>
                    <span className="info-value">{selectedCommit.message}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Author:</span>
                    <span className="info-value">{selectedCommit.author}</span>
                  </div>
                  <div className="info-row">
                    <span className="info-label">Date:</span>
                    <span className="info-value">
                      {new Date(selectedCommit.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeView === "tree" && !loading && treeData && (
          <div className="vc-view">
            <GitTree
              treeData={treeData}
              onFolderClick={(path) =>
                fetchTreeStructure(selectedCommit?.sha, path)
              }
              onBackClick={(path) =>
                fetchTreeStructure(selectedCommit?.sha, path)
              }
            />
          </div>
        )}

        {activeView === "diff" && !loading && diffData && (
          <div className="vc-view">
            <DiffViewer diffData={diffData} />
          </div>
        )}

        {activeView === "modules" && !loading && moduleStats && (
          <div className="vc-view">
            <ModuleHistory moduleStats={moduleStats} commits={commits} />
          </div>
        )}
      </div>

      {showRevertModal && selectedCommit && (
        <RevertModal
          commit={selectedCommit}
          onConfirm={() => handleRevert(selectedCommit.sha)}
          onCancel={() => setShowRevertModal(false)}
        />
      )}
    </div>
  );
}
