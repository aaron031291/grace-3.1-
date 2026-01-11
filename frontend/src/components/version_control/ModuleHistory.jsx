import { useState } from "react";
import "./ModuleHistory.css";

export default function ModuleHistory({ moduleStats, commits }) {
  const [selectedModule, setSelectedModule] = useState(null);
  const [expandedModule, setExpandedModule] = useState(null);

  const getModuleCommitCount = (moduleName) => {
    return commits.filter((commit) =>
      commit.message.toLowerCase().includes(moduleName.toLowerCase())
    ).length;
  };

  const toggleModuleExpand = (moduleName) => {
    setExpandedModule(expandedModule === moduleName ? null : moduleName);
    setSelectedModule(moduleName);
  };

  return (
    <div className="module-history">
      <div className="module-header">
        <h3>Module History</h3>
        <div className="module-meta">
          <span className="meta-item">
            <span className="meta-label">Modules:</span>
            <span className="meta-value">{moduleStats.modules.length}</span>
          </span>
        </div>
      </div>

      <div className="modules-list">
        {moduleStats.modules.length === 0 ? (
          <div className="modules-empty">No modules found</div>
        ) : (
          moduleStats.modules.map((module, idx) => {
            const commitCount = getModuleCommitCount(module.name);
            const isExpanded = expandedModule === module.name;

            return (
              <div
                key={idx}
                className={`module-item ${
                  selectedModule === module.name ? "selected" : ""
                }`}
                onClick={() => toggleModuleExpand(module.name)}
              >
                <div className="module-header-row">
                  <div className="module-info">
                    <span className="module-icon">
                      {module.is_dir ? (
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
                        </svg>
                      ) : (
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                          <polyline points="13 2 13 9 20 9" />
                        </svg>
                      )}
                    </span>
                    <span className="module-name">{module.name}</span>
                  </div>

                  <div className="module-badge">
                    <span className="badge-value">{commitCount}</span>
                    <span className="badge-label">commits</span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="module-expanded">
                    <div className="expanded-content">
                      <svg className="module-icon-large" viewBox="0 0 48 48">
                        {module.is_dir ? (
                          <path
                            d="M20 8H6c-2.2 0-4 1.8-4 4v24c0 2.2 1.8 4 4 4h36c2.2 0 4-1.8 4-4V16c0-2.2-1.8-4-4-4h-16l-4-4z"
                            fill="currentColor"
                            opacity="0.2"
                          />
                        ) : (
                          <path
                            d="M26 4H12c-2.2 0-4 1.8-4 4v32c0 2.2 1.8 4 4 4h24c2.2 0 4-1.8 4-4V14l-14-10z"
                            fill="currentColor"
                            opacity="0.2"
                          />
                        )}
                        <circle
                          cx="24"
                          cy="28"
                          r="8"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          opacity="0.5"
                        />
                      </svg>

                      <div className="expanded-stats">
                        <div className="stat-row">
                          <span className="stat-label">Type:</span>
                          <span className="stat-value">
                            {module.is_dir ? "Directory" : "File"}
                          </span>
                        </div>

                        <div className="stat-row">
                          <span className="stat-label">Commits:</span>
                          <span className="stat-value stat-number">
                            {commitCount}
                          </span>
                        </div>

                        {commitCount > 0 && (
                          <div className="recent-commits">
                            <span className="stat-label">Recent changes:</span>
                            <div className="commits-list">
                              {commits
                                .filter((commit) =>
                                  commit.message
                                    .toLowerCase()
                                    .includes(module.name.toLowerCase())
                                )
                                .slice(0, 3)
                                .map((commit, cidx) => (
                                  <div key={cidx} className="commit-item">
                                    <span className="commit-sha">
                                      {commit.sha.substring(0, 7)}
                                    </span>
                                    <span className="commit-msg">
                                      {commit.message.split("\n")[0]}
                                    </span>
                                  </div>
                                ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <svg
        className="module-background"
        viewBox="0 0 300 600"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="modules-pattern"
            x="0"
            y="0"
            width="30"
            height="30"
            patternUnits="userSpaceOnUse"
          >
            <rect
              x="0"
              y="0"
              width="30"
              height="30"
              fill="none"
              stroke="#333"
              strokeWidth="0.5"
              opacity="0.2"
            />
          </pattern>
        </defs>
        <rect width="300" height="600" fill="url(#modules-pattern)" />
      </svg>
    </div>
  );
}
