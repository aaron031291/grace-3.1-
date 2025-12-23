import { useState } from "react";
import "./CommitTimeline.css";

export default function CommitTimeline({
  commits,
  selectedCommit,
  onSelectCommit,
  onRevert,
}) {
  const [expandedCommit, setExpandedCommit] = useState(null);

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  return (
    <div className="commit-timeline">
      <div className="timeline-header">
        <h4>Commit History</h4>
        <span className="commit-count">{commits.length} commits</span>
      </div>

      <div className="timeline-items">
        {commits.length === 0 ? (
          <div className="no-commits">No commits found</div>
        ) : (
          commits.map((commit, index) => (
            <div
              key={commit.sha}
              className={`timeline-item ${
                selectedCommit?.sha === commit.sha ? "selected" : ""
              }`}
              onClick={() => {
                onSelectCommit(commit);
                setExpandedCommit(
                  expandedCommit === commit.sha ? null : commit.sha
                );
              }}
            >
              <div className="timeline-dot">
                {index === 0 && (
                  <div
                    className="timeline-dot-inner latest"
                    title="Latest commit"
                  />
                )}
                {index > 0 && <div className="timeline-dot-inner" />}
              </div>

              <div className="timeline-content">
                <div className="commit-message-line">
                  <span className="commit-sha monospace">
                    {commit.sha.substring(0, 7)}
                  </span>
                  <span className="commit-message">
                    {commit.message.split("\n")[0]}
                  </span>
                </div>

                <div className="commit-meta">
                  <span className="meta-author" title={commit.author}>
                    {commit.author.split(" ")[0]}
                  </span>
                  <span className="meta-time">
                    {formatDate(commit.timestamp)}
                  </span>
                </div>

                {expandedCommit === commit.sha && (
                  <div className="commit-expanded">
                    <div className="expanded-section">
                      <span className="section-label">Full SHA:</span>
                      <span className="section-value monospace">
                        {commit.sha}
                      </span>
                    </div>
                    {commit.message &&
                      commit.message.split("\n").length > 1 && (
                        <div className="expanded-section">
                          <span className="section-label">Full Message:</span>
                          <span className="section-value pre">
                            {commit.message}
                          </span>
                        </div>
                      )}
                    <div className="expanded-section">
                      <span className="section-label">Committer:</span>
                      <span className="section-value">{commit.committer}</span>
                    </div>
                    {selectedCommit?.sha === commit.sha && (
                      <div className="expanded-actions">
                        <button
                          className="expanded-action-btn danger"
                          onClick={(e) => {
                            e.stopPropagation();
                            onRevert();
                          }}
                        >
                          Revert to this commit
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {index < commits.length - 1 && <div className="timeline-line" />}
            </div>
          ))
        )}
      </div>

      <svg
        className="timeline-background"
        viewBox="0 0 40 500"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="dots"
            x="0"
            y="0"
            width="20"
            height="20"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="10" cy="10" r="1" fill="#444" />
          </pattern>
        </defs>
        <rect width="40" height="500" fill="url(#dots)" opacity="0.1" />
      </svg>
    </div>
  );
}
