import { useState } from "react";
import "./GitTree.css";

export default function GitTree({ treeData, onFolderClick, onBackClick }) {
  const [expandedPaths, setExpandedPaths] = useState(new Set());

  const togglePath = (path) => {
    const newExpanded = new Set(expandedPaths);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
      // Trigger folder click to fetch contents
      if (onFolderClick) {
        onFolderClick(path);
      }
    }
    setExpandedPaths(newExpanded);
  };

  const handleBackClick = () => {
    const currentPath = treeData.path || "/";
    if (currentPath !== "/" && currentPath !== "") {
      const parentPath = currentPath.substring(0, currentPath.lastIndexOf("/"));
      if (onBackClick) {
        onBackClick(parentPath);
      }
    }
  };

  const canGoBack =
    treeData.path && treeData.path !== "" && treeData.path !== "/";

  const renderTreeNode = (node, depth = 0, _parentPath = "") => {
    if (!node.children) return null;

    return (
      <div
        className="tree-node-container"
        style={{ marginLeft: `${depth * 16}px` }}
      >
        {node.children.map((child, _idx) => {
          const isDir = child.type === "tree";
          const isExpanded = expandedPaths.has(child.path);
          const hasChildren =
            isDir && child.children && child.children.length > 0;

          return (
            <div key={child.path} className="tree-node">
              <div className="tree-node-header">
                {isDir && (
                  <button
                    className={`tree-toggle ${isExpanded ? "expanded" : ""}`}
                    onClick={() => togglePath(child.path)}
                  >
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 12 12"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <polyline points="3 5 6 8 9 5" />
                    </svg>
                  </button>
                )}
                {!isDir && <div className="tree-toggle-placeholder" />}

                <span className={`tree-icon ${isDir ? "dir" : "file"}`}>
                  {isDir ? (
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
                    </svg>
                  ) : (
                    <svg
                      width="14"
                      height="14"
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

                <span className="tree-name">{child.name}</span>
              </div>

              {isExpanded && isDir && hasChildren && (
                <div className="tree-children">
                  {renderTreeNode(child, depth + 1, child.path)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="git-tree">
      <div className="tree-header">
        <div className="tree-header-left">
          {canGoBack && (
            <button
              className="tree-back-button"
              onClick={handleBackClick}
              title="Go to parent directory"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M19 12H5M12 19l-7-7 7-7" />
              </svg>
              Back
            </button>
          )}
        </div>
        <div className="tree-header-center">
          <h3>File Tree</h3>
        </div>
        <div className="tree-header-right">
          <span className="tree-path">{treeData.path || "/"}</span>
        </div>
      </div>

      <div className="tree-content">
        {treeData.children && treeData.children.length > 0 ? (
          renderTreeNode(treeData, 0)
        ) : (
          <div className="tree-empty">Empty directory</div>
        )}
      </div>

      <svg
        className="tree-background"
        viewBox="0 0 200 600"
        preserveAspectRatio="none"
      >
        <defs>
          <pattern
            id="grid"
            x="0"
            y="0"
            width="20"
            height="20"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M 20 0 L 0 0 0 20"
              fill="none"
              stroke="#333"
              strokeWidth="0.5"
              opacity="0.2"
            />
          </pattern>
        </defs>
        <rect width="200" height="600" fill="url(#grid)" />
      </svg>
    </div>
  );
}
