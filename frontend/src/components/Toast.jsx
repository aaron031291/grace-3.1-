/**
 * Toast Notification System
 * =========================
 * Global toast/snackbar notifications for user feedback.
 */

import React, { createContext, useContext, useState, useCallback } from 'react';
import { Snackbar, Alert, AlertTitle, Slide, IconButton, Box } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import InfoIcon from '@mui/icons-material/Info';

// Toast Context
const ToastContext = createContext(null);

// Toast types
export const TOAST_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info'
};

// Slide transition
function SlideTransition(props) {
  return <Slide {...props} direction="up" />;
}

/**
 * Toast Provider - Wrap your app with this
 */
export function ToastProvider({ children, maxToasts = 3 }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, options = {}) => {
    const id = Date.now() + Math.random().toString(36).substr(2, 9);
    const toast = {
      id,
      message,
      type: options.type || TOAST_TYPES.INFO,
      title: options.title,
      duration: options.duration ?? 5000,
      action: options.action,
      persistent: options.persistent || false
    };

    setToasts(prev => {
      const newToasts = [...prev, toast];
      // Limit max toasts
      if (newToasts.length > maxToasts) {
        return newToasts.slice(-maxToasts);
      }
      return newToasts;
    });

    return id;
  }, [maxToasts]);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  // Convenience methods
  const success = useCallback((message, options = {}) => {
    return addToast(message, { ...options, type: TOAST_TYPES.SUCCESS });
  }, [addToast]);

  const error = useCallback((message, options = {}) => {
    return addToast(message, { ...options, type: TOAST_TYPES.ERROR, duration: options.duration ?? 7000 });
  }, [addToast]);

  const warning = useCallback((message, options = {}) => {
    return addToast(message, { ...options, type: TOAST_TYPES.WARNING });
  }, [addToast]);

  const info = useCallback((message, options = {}) => {
    return addToast(message, { ...options, type: TOAST_TYPES.INFO });
  }, [addToast]);

  const value = {
    toasts,
    addToast,
    removeToast,
    clearAll,
    success,
    error,
    warning,
    info
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </ToastContext.Provider>
  );
}

/**
 * Toast Container - Renders all active toasts
 */
function ToastContainer({ toasts, onClose }) {
  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 24,
        right: 24,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        maxWidth: 400
      }}
    >
      {toasts.map((toast, index) => (
        <ToastItem
          key={toast.id}
          toast={toast}
          onClose={() => onClose(toast.id)}
          index={index}
        />
      ))}
    </Box>
  );
}

/**
 * Individual Toast Item
 */
function ToastItem({ toast, onClose, index }) {
  const [open, setOpen] = useState(true);

  const handleClose = (event, reason) => {
    if (reason === 'clickaway') return;
    setOpen(false);
    setTimeout(onClose, 300); // Wait for animation
  };

  const getIcon = () => {
    switch (toast.type) {
      case TOAST_TYPES.SUCCESS:
        return <CheckCircleIcon />;
      case TOAST_TYPES.ERROR:
        return <ErrorIcon />;
      case TOAST_TYPES.WARNING:
        return <WarningIcon />;
      default:
        return <InfoIcon />;
    }
  };

  return (
    <Snackbar
      open={open}
      autoHideDuration={toast.persistent ? null : toast.duration}
      onClose={handleClose}
      TransitionComponent={SlideTransition}
      sx={{
        position: 'relative',
        transform: 'none !important',
        top: 'auto !important',
        left: 'auto !important',
        right: 'auto !important',
        bottom: 'auto !important'
      }}
    >
      <Alert
        severity={toast.type}
        icon={getIcon()}
        onClose={handleClose}
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {toast.action}
            <IconButton
              size="small"
              color="inherit"
              onClick={handleClose}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        }
        sx={{
          width: '100%',
          boxShadow: 3,
          '& .MuiAlert-message': {
            width: '100%'
          }
        }}
      >
        {toast.title && <AlertTitle>{toast.title}</AlertTitle>}
        {toast.message}
      </Alert>
    </Snackbar>
  );
}

/**
 * Hook to use toast notifications
 */
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

/**
 * Standalone toast function (requires ToastProvider in tree)
 */
let toastRef = null;

export function setToastRef(ref) {
  toastRef = ref;
}

export function toast(message, options) {
  if (toastRef) {
    return toastRef.addToast(message, options);
  }
  console.warn('Toast: No ToastProvider found');
}

toast.success = (message, options) => toast(message, { ...options, type: TOAST_TYPES.SUCCESS });
toast.error = (message, options) => toast(message, { ...options, type: TOAST_TYPES.ERROR });
toast.warning = (message, options) => toast(message, { ...options, type: TOAST_TYPES.WARNING });
toast.info = (message, options) => toast(message, { ...options, type: TOAST_TYPES.INFO });

export default ToastProvider;
