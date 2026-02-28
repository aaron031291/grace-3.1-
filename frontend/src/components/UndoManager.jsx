/**
 * UndoManager — Global undo system. Tracks reversible actions,
 * shows floating undo toast, supports Ctrl+Z.
 */
import { useState, useEffect, useCallback } from 'react';

const MAX_STACK = 30;
let _undoStack = [];
let _listeners = [];

export function pushUndo(action) {
  _undoStack.push({ ...action, ts: Date.now() });
  if (_undoStack.length > MAX_STACK) _undoStack.shift();
  _listeners.forEach(fn => fn([..._undoStack]));
}

export function useUndo() {
  const [stack, setStack] = useState([..._undoStack]);

  useEffect(() => {
    _listeners.push(setStack);
    return () => { _listeners = _listeners.filter(fn => fn !== setStack); };
  }, []);

  const undo = useCallback(async () => {
    if (_undoStack.length === 0) return null;
    const action = _undoStack.pop();
    _listeners.forEach(fn => fn([..._undoStack]));
    if (action.undoFn) {
      try { await action.undoFn(); } catch { /* skip */ }
    }
    return action;
  }, []);

  return { stack, undo, canUndo: stack.length > 0 };
}

export default function UndoToast() {
  const { stack, undo, canUndo } = useUndo();
  const [lastUndo, setLastUndo] = useState(null);
  const [show, setShow] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        handleUndo();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [canUndo]);

  const handleUndo = async () => {
    const action = await undo();
    if (action) {
      setLastUndo(action);
      setShow(true);
      setTimeout(() => setShow(false), 3000);
    }
  };

  if (!canUndo && !show) return null;

  return (
    <div style={{
      position: 'fixed', bottom: 72, right: 16, zIndex: 999,
      display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end',
    }}>
      {show && lastUndo && (
        <div style={{
          padding: '8px 16px', background: '#4caf50', color: '#fff',
          borderRadius: 8, fontSize: 12, fontWeight: 600,
          boxShadow: '0 4px 12px rgba(0,0,0,.3)',
          animation: 'fadeIn .2s ease',
        }}>
          Undone: {lastUndo.label || lastUndo.type || 'action'}
        </div>
      )}
      {canUndo && (
        <button onClick={handleUndo} title="Undo last action (Ctrl+Z)" style={{
          padding: '6px 12px', background: '#16213e', color: '#aaa',
          border: '1px solid #333', borderRadius: 6, fontSize: 11,
          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
        }}>
          ↩ Undo {stack.length > 0 ? `(${stack[stack.length - 1]?.label?.substring(0, 20) || ''})` : ''}
        </button>
      )}
    </div>
  );
}
