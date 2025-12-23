import "./RevertModal.css";

export default function RevertModal({ commit, onConfirm, onCancel }) {
  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString();
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Revert to Commit</h2>
          <button className="modal-close" onClick={onCancel}>
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="modal-body">
          <div className="warning-message">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
            </svg>
            <span>
              Are you sure you want to revert to this commit? This will change
              all files in your working directory.
            </span>
          </div>

          <div className="commit-preview">
            <div className="preview-section">
              <span className="preview-label">SHA:</span>
              <span className="preview-value monospace">{commit.sha}</span>
            </div>

            <div className="preview-section">
              <span className="preview-label">Message:</span>
              <span className="preview-value">{commit.message}</span>
            </div>

            <div className="preview-section">
              <span className="preview-label">Author:</span>
              <span className="preview-value">{commit.author}</span>
            </div>

            <div className="preview-section">
              <span className="preview-label">Date:</span>
              <span className="preview-value">
                {formatDate(commit.timestamp)}
              </span>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="modal-button secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className="modal-button danger" onClick={onConfirm}>
            Revert to this commit
          </button>
        </div>
      </div>
    </div>
  );
}
