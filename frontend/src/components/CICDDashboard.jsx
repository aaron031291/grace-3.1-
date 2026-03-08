/**
 * CI/CD Dashboard Component
 * =========================
 * View and trigger Genesis CI/CD pipelines.
 * Supports autonomous actions from the knowledge base.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  LinearProgress,
  Alert,
  Collapse,
  Tooltip,
  Tab,
  Tabs,
  CircularProgress,
  Divider
} from '@mui/material';
import { API_BASE_URL } from '../config/api';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Schedule as PendingIcon,
  HourglassEmpty as RunningIcon,
  Cancel as CancelIcon,
  Replay as RetryIcon,
  ExpandMore as ExpandIcon,
  ExpandLess as CollapseIcon,
  Code as CodeIcon,
  Timeline as TimelineIcon,
  Settings as SettingsIcon,
  Webhook as WebhookIcon
} from '@mui/icons-material';

const API_BASE = '/api/cicd';

// Status colors and icons
const statusConfig = {
  pending: { color: 'default', icon: PendingIcon, label: 'Pending' },
  queued: { color: 'info', icon: PendingIcon, label: 'Queued' },
  running: { color: 'warning', icon: RunningIcon, label: 'Running' },
  success: { color: 'success', icon: SuccessIcon, label: 'Success' },
  failed: { color: 'error', icon: ErrorIcon, label: 'Failed' },
  cancelled: { color: 'default', icon: CancelIcon, label: 'Cancelled' },
  skipped: { color: 'default', icon: CancelIcon, label: 'Skipped' }
};

function StatusChip({ status }) {
  const config = statusConfig[status] || statusConfig.pending;
  const Icon = config.icon;

  return (
    <Chip
      icon={<Icon fontSize="small" />}
      label={config.label}
      color={config.color}
      size="small"
      variant="outlined"
    />
  );
}

function formatDuration(seconds) {
  if (!seconds) return '-';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(0);
  return `${mins}m ${secs}s`;
}

function formatTime(isoString) {
  if (!isoString) return '-';
  return new Date(isoString).toLocaleString();
}

/**
 * Pipeline Card Component
 */
function PipelineCard({ pipeline, onTrigger }) {
  const [triggering, setTriggering] = useState(false);

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await onTrigger(pipeline.id);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Typography variant="h6" gutterBottom>
          {pipeline.name}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {pipeline.description || 'No description'}
        </Typography>

        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1 }}>
          {pipeline.triggers.map((trigger) => (
            <Chip key={trigger} label={trigger} size="small" variant="outlined" />
          ))}
        </Box>

        <Typography variant="caption" color="text.secondary">
          {pipeline.stage_count} stages • Branches: {pipeline.branches.join(', ')}
        </Typography>
      </CardContent>

      <CardActions>
        <Button
          startIcon={triggering ? <CircularProgress size={16} /> : <PlayIcon />}
          onClick={handleTrigger}
          disabled={triggering}
          color="primary"
          variant="contained"
          size="small"
        >
          {triggering ? 'Triggering...' : 'Run Pipeline'}
        </Button>
      </CardActions>
    </Card>
  );
}

/**
 * Run Details Dialog
 */
function RunDetailsDialog({ run, open, onClose }) {
  const [expandedStages, setExpandedStages] = useState({});

  if (!run) return null;

  const toggleStage = (stageName) => {
    setExpandedStages((prev) => ({
      ...prev,
      [stageName]: !prev[stageName]
    }));
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h6">Run: {run.id}</Typography>
          <StatusChip status={run.status} />
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">Pipeline</Typography>
            <Typography>{run.pipeline_name}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">Branch</Typography>
            <Typography>{run.branch}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">Trigger</Typography>
            <Typography>{run.trigger}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">Duration</Typography>
            <Typography>{formatDuration(run.duration_seconds)}</Typography>
          </Grid>
          <Grid item xs={12}>
            <Typography variant="caption" color="text.secondary">Genesis Key</Typography>
            <Typography fontFamily="monospace" fontSize="small">{run.genesis_key}</Typography>
          </Grid>
        </Grid>

        <Typography variant="h6" gutterBottom>Stages</Typography>

        {run.stage_results.map((stage) => (
          <Paper key={stage.stage_name} sx={{ mb: 1 }}>
            <Box
              sx={{
                p: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer'
              }}
              onClick={() => toggleStage(stage.stage_name)}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <StatusChip status={stage.status} />
                <Typography>{stage.stage_name}</Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  {formatDuration(stage.duration_seconds)}
                </Typography>
                {expandedStages[stage.stage_name] ? <CollapseIcon /> : <ExpandIcon />}
              </Box>
            </Box>

            <Collapse in={expandedStages[stage.stage_name]}>
              <Box sx={{ p: 2, pt: 0 }}>
                {stage.stdout && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Output</Typography>
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 1,
                        maxHeight: 200,
                        overflow: 'auto',
                        backgroundColor: 'grey.900',
                        fontFamily: 'monospace',
                        fontSize: '12px',
                        whiteSpace: 'pre-wrap'
                      }}
                    >
                      {stage.stdout}
                    </Paper>
                  </Box>
                )}
                {stage.stderr && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom color="error">
                      Errors
                    </Typography>
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 1,
                        maxHeight: 200,
                        overflow: 'auto',
                        backgroundColor: 'error.dark',
                        fontFamily: 'monospace',
                        fontSize: '12px',
                        whiteSpace: 'pre-wrap'
                      }}
                    >
                      {stage.stderr}
                    </Paper>
                  </Box>
                )}
              </Box>
            </Collapse>
          </Paper>
        ))}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

/**
 * Trigger Dialog
 */
function TriggerDialog({ open, onClose, onTrigger, pipelines }) {
  const [pipelineId, setPipelineId] = useState('');
  const [branch, setBranch] = useState('main');
  const [triggering, setTriggering] = useState(false);

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await onTrigger(pipelineId, branch);
      onClose();
    } finally {
      setTriggering(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Trigger Pipeline</DialogTitle>
      <DialogContent>
        <FormControl fullWidth sx={{ mt: 2, mb: 2 }}>
          <InputLabel>Pipeline</InputLabel>
          <Select
            value={pipelineId}
            onChange={(e) => setPipelineId(e.target.value)}
            label="Pipeline"
          >
            {pipelines.map((p) => (
              <MenuItem key={p.id} value={p.id}>
                {p.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          fullWidth
          label="Branch"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="main"
        />
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleTrigger}
          variant="contained"
          disabled={!pipelineId || triggering}
          startIcon={triggering ? <CircularProgress size={16} /> : <PlayIcon />}
        >
          {triggering ? 'Triggering...' : 'Trigger'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/**
 * Main CI/CD Dashboard
 */
export default function CICDDashboard() {
  const [tab, setTab] = useState(0);
  const [pipelines, setPipelines] = useState([]);
  const [runs, setRuns] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [triggerDialogOpen, setTriggerDialogOpen] = useState(false);
  const [_refreshInterval, setRefreshInterval] = useState(null);

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [pipelinesRes, runsRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/pipelines`),
        fetch(`${API_BASE}/runs?limit=20`),
        fetch(`${API_BASE}/status`)
      ]);

      if (pipelinesRes.ok) setPipelines(await pipelinesRes.json());
      if (runsRes.ok) setRuns(await runsRes.json());
      if (statusRes.ok) setStatus(await statusRes.json());

      setError(null);
    } catch {
      setError('Failed to fetch CI/CD data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchData, 10000);
    setRefreshInterval(interval);

    return () => clearInterval(interval);
  }, [fetchData]);

  // Trigger pipeline
  const triggerPipeline = async (pipelineId, branch = 'main') => {
    try {
      const response = await fetch(`${API_BASE}/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pipeline_id: pipelineId,
          branch: branch
        })
      });

      if (response.ok) {
        await fetchData();
      } else {
        const error = await response.json();
        setError(error.detail || 'Failed to trigger pipeline');
      }
    } catch {
      setError('Failed to trigger pipeline');
    }
  };

  // Cancel run
  const cancelRun = async (runId) => {
    try {
      await fetch(`${API_BASE}/runs/${runId}/cancel`, { method: 'POST' });
      await fetchData();
    } catch {
      setError('Failed to cancel run');
    }
  };

  // Retry run
  const retryRun = async (runId) => {
    try {
      await fetch(`${API_BASE}/runs/${runId}/retry`, { method: 'POST' });
      await fetchData();
    } catch {
      setError('Failed to retry run');
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2 }}>Loading CI/CD Dashboard...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Genesis CI/CD</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            startIcon={<RefreshIcon />}
            onClick={fetchData}
            variant="outlined"
          >
            Refresh
          </Button>
          <Button
            startIcon={<PlayIcon />}
            onClick={() => setTriggerDialogOpen(true)}
            variant="contained"
            color="primary"
          >
            Trigger Pipeline
          </Button>
        </Box>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Status Cards */}
      {status && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>Status</Typography>
                <Typography variant="h5">
                  <Chip
                    label={status.status}
                    color={status.status === 'running' ? 'success' : 'default'}
                  />
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>Pipelines</Typography>
                <Typography variant="h4">{status.pipelines_registered}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>Active Runs</Typography>
                <Typography variant="h4">{status.active_runs}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>Genesis Keys</Typography>
                <Typography variant="h4">{status.genesis_keys_generated}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Tabs */}
      <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab icon={<TimelineIcon />} label="Runs" />
        <Tab icon={<SettingsIcon />} label="Pipelines" />
      </Tabs>

      {/* Runs Tab */}
      {tab === 0 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Run ID</TableCell>
                <TableCell>Pipeline</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Branch</TableCell>
                <TableCell>Trigger</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {runs.map((run) => (
                <TableRow key={run.id} hover>
                  <TableCell>
                    <Typography
                      fontFamily="monospace"
                      fontSize="small"
                      sx={{ cursor: 'pointer', color: 'primary.main' }}
                      onClick={() => setSelectedRun(run)}
                    >
                      {run.id}
                    </Typography>
                  </TableCell>
                  <TableCell>{run.pipeline_name}</TableCell>
                  <TableCell><StatusChip status={run.status} /></TableCell>
                  <TableCell>{run.branch}</TableCell>
                  <TableCell>{run.trigger}</TableCell>
                  <TableCell>{formatDuration(run.duration_seconds)}</TableCell>
                  <TableCell>{formatTime(run.started_at)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {['running', 'queued', 'pending'].includes(run.status) && (
                        <Tooltip title="Cancel">
                          <IconButton size="small" onClick={() => cancelRun(run.id)}>
                            <StopIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {['failed', 'cancelled'].includes(run.status) && (
                        <Tooltip title="Retry">
                          <IconButton size="small" onClick={() => retryRun(run.id)}>
                            <RetryIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      <Tooltip title="View Details">
                        <IconButton size="small" onClick={() => setSelectedRun(run)}>
                          <CodeIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
              {runs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography color="text.secondary">No pipeline runs yet</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Pipelines Tab */}
      {tab === 1 && (
        <Grid container spacing={2}>
          {pipelines.map((pipeline) => (
            <Grid item xs={12} md={4} key={pipeline.id}>
              <PipelineCard pipeline={pipeline} onTrigger={triggerPipeline} />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Run Details Dialog */}
      <RunDetailsDialog
        run={selectedRun}
        open={!!selectedRun}
        onClose={() => setSelectedRun(null)}
      />

      {/* Trigger Dialog */}
      <TriggerDialog
        open={triggerDialogOpen}
        onClose={() => setTriggerDialogOpen(false)}
        onTrigger={triggerPipeline}
        pipelines={pipelines}
      />
    </Box>
  );
}

// Export for lazy loading
export { CICDDashboard };
