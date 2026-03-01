/**
 * UploadProgress — visual progress indicator for chunked uploads.
 * Shows phase, percentage bar, speed, and cancel button.
 */

const PHASE_LABELS = {
  hashing: 'Computing file hash...',
  initiating: 'Starting upload...',
  uploading: 'Uploading chunks...',
  assembling: 'Assembling file...',
  complete: 'Upload complete!',
};

const COLORS = {
  bg: '#1a1a2e',
  bar: '#4caf50',
  barHash: '#2196f3',
  barAssemble: '#ff9800',
  text: '#eee',
  textMuted: '#aaa',
  border: '#333',
  cancel: '#e94560',
};

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

export default function UploadProgress({ progress, onCancel, filename }) {
  if (!progress) return null;

  const { phase, percent, bytesUploaded, totalBytes, speedDisplay, elapsed } = progress;
  const label = PHASE_LABELS[phase] || phase;
  const isComplete = phase === 'complete';

  let barColor = COLORS.bar;
  if (phase === 'hashing') barColor = COLORS.barHash;
  if (phase === 'assembling') barColor = COLORS.barAssemble;

  const eta = percent > 0 && percent < 100 && elapsed
    ? Math.round((elapsed / percent) * (100 - percent))
    : null;

  return (
    <div style={{
      background: COLORS.bg,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 6,
      padding: '10px 14px',
      marginBottom: 8,
    }}>
      {filename && (
        <div style={{ fontSize: 12, color: COLORS.text, marginBottom: 4, fontWeight: 500 }}>
          {filename}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <div style={{ flex: 1 }}>
          <div style={{
            height: 8,
            background: '#222',
            borderRadius: 4,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${Math.min(percent || 0, 100)}%`,
              background: barColor,
              borderRadius: 4,
              transition: 'width 0.3s ease',
            }} />
          </div>
        </div>
        <span style={{ fontSize: 12, color: COLORS.text, minWidth: 42, textAlign: 'right' }}>
          {(percent || 0).toFixed(0)}%
        </span>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: COLORS.textMuted }}>
          {label}
          {phase === 'uploading' && totalBytes ? ` • ${formatBytes(bytesUploaded || 0)} / ${formatBytes(totalBytes)}` : ''}
          {speedDisplay && phase === 'uploading' ? ` • ${speedDisplay}` : ''}
          {eta && !isComplete ? ` • ~${eta}s remaining` : ''}
        </span>
        {!isComplete && onCancel && (
          <button
            onClick={onCancel}
            style={{
              fontSize: 11,
              color: COLORS.cancel,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '2px 6px',
            }}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
