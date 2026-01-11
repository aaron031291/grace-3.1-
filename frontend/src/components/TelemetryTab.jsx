import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  Alert,
  CircularProgress,
  LinearProgress,
  Tabs,
  Tab,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Speed as SpeedIcon,
  Memory as MemoryIcon,
  Storage as StorageIcon,
  Timeline as TimelineIcon
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const TelemetryTab = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // State for different data sections
  const [systemState, setSystemState] = useState(null);
  const [operations, setOperations] = useState([]);
  const [baselines, setBaselines] = useState([]);
  const [driftAlerts, setDriftAlerts] = useState([]);
  const [stats, setStats] = useState(null);

  // Fetch system state
  const fetchSystemState = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/telemetry/system-state/current`);
      setSystemState(response.data);
    } catch (err) {
      console.error('Error fetching system state:', err);
    }
  };

  // Fetch recent operations
  const fetchOperations = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/telemetry/operations?limit=20`);
      setOperations(response.data);
    } catch (err) {
      console.error('Error fetching operations:', err);
    }
  };

  // Fetch baselines
  const fetchBaselines = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/telemetry/baselines`);
      setBaselines(response.data);
    } catch (err) {
      console.error('Error fetching baselines:', err);
    }
  };

  // Fetch drift alerts
  const fetchDriftAlerts = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/telemetry/drift-alerts?resolved=false`);
      setDriftAlerts(response.data);
    } catch (err) {
      console.error('Error fetching drift alerts:', err);
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/telemetry/stats?hours=24`);
      setStats(response.data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  // Fetch all data
  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchSystemState(),
        fetchOperations(),
        fetchBaselines(),
        fetchDriftAlerts(),
        fetchStats()
      ]);
    } catch (err) {
      console.error("Failed to load telemetry data:", err);
      setError('Failed to load telemetry data. Please ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Acknowledge alert
  const acknowledgeAlert = async (alertId) => {
    try {
      await axios.post(`${API_BASE_URL}/telemetry/drift-alerts/${alertId}/acknowledge`);
      fetchDriftAlerts();
    } catch (err) {
      console.error('Error acknowledging alert:', err);
    }
  };

  // Resolve alert
  const resolveAlert = async (alertId) => {
    try {
      await axios.post(`${API_BASE_URL}/telemetry/drift-alerts/${alertId}/resolve`);
      fetchDriftAlerts();
    } catch (err) {
      console.error('Error resolving alert:', err);
    }
  };

  // Get severity color
  const getSeverityColor = (severity) => {
    const colors = {
      low: 'info',
      medium: 'warning',
      high: 'error',
      critical: 'error'
    };
    return colors[severity] || 'default';
  };

  // Get status color
  const getStatusColor = (status) => {
    const colors = {
      completed: 'success',
      failed: 'error',
      timeout: 'warning',
      cancelled: 'default'
    };
    return colors[status] || 'default';
  };

  // Format duration
  const formatDuration = (ms) => {
    if (!ms) return 'N/A';
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // Format percentage
  const formatPercent = (value) => {
    if (value === null || value === undefined) return 'N/A';
    return `${(value * 100).toFixed(1)}%`;
  };

  // System Overview Card
  const SystemOverview = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <StorageIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">Documents</Typography>
            </Box>
            <Typography variant="h4">{systemState?.document_count || 0}</Typography>
            <Typography variant="caption" color="text.secondary">
              {systemState?.chunk_count || 0} chunks
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <SpeedIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">CPU</Typography>
            </Box>
            <Typography variant="h4">{systemState?.cpu_percent?.toFixed(1) || 0}%</Typography>
            <LinearProgress
              variant="determinate"
              value={systemState?.cpu_percent || 0}
              sx={{ mt: 1 }}
            />
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <MemoryIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">Memory</Typography>
            </Box>
            <Typography variant="h4">{systemState?.memory_percent?.toFixed(1) || 0}%</Typography>
            <LinearProgress
              variant="determinate"
              value={systemState?.memory_percent || 0}
              sx={{ mt: 1 }}
            />
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={3}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" mb={1}>
              <TimelineIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6">Confidence</Typography>
            </Box>
            <Typography variant="h4">
              {systemState?.average_confidence_score
                ? (systemState.average_confidence_score * 100).toFixed(0)
                : 0}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Average score
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      {/* Statistics Card */}
      {stats && (
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Last 24 Hours
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={3}>
                  <Typography variant="body2" color="text.secondary">Total Operations</Typography>
                  <Typography variant="h5">{stats.total_operations}</Typography>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Typography variant="body2" color="text.secondary">Success Rate</Typography>
                  <Typography variant="h5">{formatPercent(stats.success_rate)}</Typography>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Typography variant="body2" color="text.secondary">Avg Duration</Typography>
                  <Typography variant="h5">{formatDuration(stats.average_duration_ms)}</Typography>
                </Grid>
                <Grid item xs={12} sm={3}>
                  <Typography variant="body2" color="text.secondary">Tokens Processed</Typography>
                  <Typography variant="h5">{stats.total_tokens_processed.toLocaleString()}</Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      )}
    </Grid>
  );

  // Operations Table
  const OperationsTable = () => (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Operation</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Duration</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Started At</TableCell>
            <TableCell>Confidence</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {operations.map((op) => (
            <TableRow key={op.run_id}>
              <TableCell>{op.operation_name}</TableCell>
              <TableCell>
                <Chip label={op.operation_type} size="small" />
              </TableCell>
              <TableCell>{formatDuration(op.duration_ms)}</TableCell>
              <TableCell>
                <Chip
                  label={op.status}
                  color={getStatusColor(op.status)}
                  size="small"
                  icon={
                    op.status === 'completed' ? (
                      <CheckCircleIcon />
                    ) : op.status === 'failed' ? (
                      <ErrorIcon />
                    ) : (
                      <WarningIcon />
                    )
                  }
                />
              </TableCell>
              <TableCell>
                {new Date(op.started_at).toLocaleTimeString()}
              </TableCell>
              <TableCell>
                {op.confidence_score ? formatPercent(op.confidence_score) : 'N/A'}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  // Baselines Table
  const BaselinesTable = () => (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Operation</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Sample Count</TableCell>
            <TableCell>Mean Duration</TableCell>
            <TableCell>P95 Duration</TableCell>
            <TableCell>Success Rate</TableCell>
            <TableCell>Last Updated</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {baselines.map((baseline) => (
            <TableRow key={baseline.id}>
              <TableCell>{baseline.operation_name}</TableCell>
              <TableCell>
                <Chip label={baseline.operation_type} size="small" />
              </TableCell>
              <TableCell>{baseline.sample_count}</TableCell>
              <TableCell>{formatDuration(baseline.mean_duration_ms)}</TableCell>
              <TableCell>{formatDuration(baseline.p95_duration_ms)}</TableCell>
              <TableCell>{formatPercent(baseline.success_rate)}</TableCell>
              <TableCell>
                {new Date(baseline.last_updated).toLocaleDateString()}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  // Drift Alerts
  const DriftAlertsView = () => (
    <Box>
      {driftAlerts.length === 0 ? (
        <Alert severity="success">No active drift alerts. System is operating within baselines.</Alert>
      ) : (
        <Grid container spacing={2}>
          {driftAlerts.map((alert) => (
            <Grid item xs={12} key={alert.id}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="start">
                    <Box flex={1}>
                      <Box display="flex" alignItems="center" mb={1}>
                        <Chip
                          label={alert.severity.toUpperCase()}
                          color={getSeverityColor(alert.severity)}
                          size="small"
                          sx={{ mr: 1 }}
                        />
                        <Chip
                          label={alert.drift_type}
                          size="small"
                          sx={{ mr: 1 }}
                        />
                        <Typography variant="subtitle2">
                          {alert.operation_name}
                        </Typography>
                      </Box>

                      <Grid container spacing={2} sx={{ mt: 1 }}>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">
                            Baseline Value
                          </Typography>
                          <Typography variant="body1">
                            {alert.baseline_value?.toFixed(1) || 'N/A'}
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">
                            Observed Value
                          </Typography>
                          <Typography variant="body1">
                            {alert.observed_value?.toFixed(1) || 'N/A'}
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary">
                            Deviation
                          </Typography>
                          <Typography variant="body1" color="error">
                            {alert.deviation_percent?.toFixed(1)}%
                          </Typography>
                        </Grid>
                      </Grid>

                      <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                        Detected: {new Date(alert.created_at).toLocaleString()}
                      </Typography>
                    </Box>

                    <Box>
                      {!alert.acknowledged && (
                        <Button
                          size="small"
                          onClick={() => acknowledgeAlert(alert.id)}
                          sx={{ mr: 1 }}
                        >
                          Acknowledge
                        </Button>
                      )}
                      <Button
                        size="small"
                        color="success"
                        onClick={() => resolveAlert(alert.id)}
                      >
                        Resolve
                      </Button>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );

  return (
    <Box sx={{ width: '100%', p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Self-Modeling Telemetry
        </Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchAllData} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Service Status */}
      {systemState && (
        <Box mb={3}>
          <Grid container spacing={2}>
            <Grid item>
              <Chip
                icon={systemState.ollama_running ? <CheckCircleIcon /> : <ErrorIcon />}
                label={`Ollama: ${systemState.ollama_running ? 'Running' : 'Offline'}`}
                color={systemState.ollama_running ? 'success' : 'error'}
              />
            </Grid>
            <Grid item>
              <Chip
                icon={systemState.qdrant_connected ? <CheckCircleIcon /> : <ErrorIcon />}
                label={`Qdrant: ${systemState.qdrant_connected ? 'Connected' : 'Disconnected'}`}
                color={systemState.qdrant_connected ? 'success' : 'error'}
              />
            </Grid>
            <Grid item>
              <Chip
                icon={systemState.database_connected ? <CheckCircleIcon /> : <ErrorIcon />}
                label={`Database: ${systemState.database_connected ? 'Connected' : 'Disconnected'}`}
                color={systemState.database_connected ? 'success' : 'error'}
              />
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Error Message */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      )}

      {/* Tabs */}
      {!loading && (
        <>
          <Tabs
            value={activeTab}
            onChange={(e, newValue) => setActiveTab(newValue)}
            sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}
          >
            <Tab label="Overview" />
            <Tab label="Operations" />
            <Tab label="Baselines" />
            <Tab
              label={
                <Box display="flex" alignItems="center">
                  Drift Alerts
                  {driftAlerts.length > 0 && (
                    <Chip
                      label={driftAlerts.length}
                      color="error"
                      size="small"
                      sx={{ ml: 1, height: 20 }}
                    />
                  )}
                </Box>
              }
            />
          </Tabs>

          {/* Tab Panels */}
          {activeTab === 0 && <SystemOverview />}
          {activeTab === 1 && <OperationsTable />}
          {activeTab === 2 && <BaselinesTable />}
          {activeTab === 3 && <DriftAlertsView />}
        </>
      )}
    </Box>
  );
};

export default TelemetryTab;
