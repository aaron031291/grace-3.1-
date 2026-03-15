"""
Tab API Response Schemas — Pydantic models for every tab endpoint.

These are the single source of truth for frontend/backend data contracts.
FastAPI auto-generates OpenAPI JSON from these models at /openapi.json.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== BI Tab ====================

class BIUptime(BaseModel):
    days: int = 0
    hours: int = 0

class BIDocuments(BaseModel):
    total: int = 0
    total_size_mb: int = 0
    growth: str = "flat"
    this_week: int = 0
    avg_confidence: float = 0.0

class BIChats(BaseModel):
    total_chats: int = 0
    total_messages: int = 0
    avg_per_chat: int = 0

class BIGenesisKeys(BaseModel):
    total: int = 0
    today: int = 0
    error_rate: float = 0.0

class BILearning(BaseModel):
    examples: int = 0
    skills: int = 0
    avg_trust: float = 0.0

class BITaskStatus(BaseModel):
    completed: int = 0
    active: int = 0
    failed: int = 0

class BITasks(BaseModel):
    total: int = 0
    by_status: BITaskStatus = BITaskStatus()

class BIDashboardResponse(BaseModel):
    uptime: BIUptime = BIUptime()
    documents: BIDocuments = BIDocuments()
    chats: BIChats = BIChats()
    genesis_keys: BIGenesisKeys = BIGenesisKeys()
    learning: BILearning = BILearning()
    tasks: BITasks = BITasks()

class BITrendDay(BaseModel):
    date: str
    genesis_keys: int = 0
    documents: int = 0

class BITrendsResponse(BaseModel):
    days: List[BITrendDay] = []


# ==================== Oracle Tab ====================

class OracleMetric(BaseModel):
    total: int = 0
    avg_trust: float = 0.0

class OracleMetricWithSuccess(BaseModel):
    total: int = 0
    avg_success_rate: float = 0.0

class OracleEpisodes(BaseModel):
    total: int = 0
    avg_trust: float = 0.0

class OracleDocuments(BaseModel):
    total: int = 0
    total_chunks: int = 0

class OracleVectorStore(BaseModel):
    vectors: int = 0

class OracleFederated(BaseModel):
    status: str = "unavailable"
    nodes: int = 0
    rounds: int = 0
    global_model_version: Optional[int] = None

class OracleDashboardResponse(BaseModel):
    learning_examples: OracleMetric = OracleMetric()
    learning_patterns: OracleMetricWithSuccess = OracleMetricWithSuccess()
    procedures: OracleMetricWithSuccess = OracleMetricWithSuccess()
    episodes: OracleEpisodes = OracleEpisodes()
    documents: OracleDocuments = OracleDocuments()
    vector_store: OracleVectorStore = OracleVectorStore()
    federated: OracleFederated = OracleFederated()

class TrustDistributionResponse(BaseModel):
    total: int = 0
    distribution: Dict[str, int] = {}

class TrainingExample(BaseModel):
    id: str
    type: Optional[str] = None
    trust_score: Optional[float] = None
    source: Optional[str] = None
    input: str = ""

class TrainingDataResponse(BaseModel):
    examples: List[TrainingExample] = []
    total: int = 0


# ==================== Learn & Heal Tab ====================

class HealthSnapshot(BaseModel):
    status: str = "unknown"
    cpu: float = 0.0
    memory: float = 0.0

class LHExamples(BaseModel):
    total: int = 0
    avg_trust: float = 0.0

class LHPatterns(BaseModel):
    total: int = 0
    avg_success: float = 0.0

class LHProcedures(BaseModel):
    total: int = 0
    avg_success: float = 0.0

class TopType(BaseModel):
    type: str
    count: int = 0

class LHLearning(BaseModel):
    examples: LHExamples = LHExamples()
    patterns: LHPatterns = LHPatterns()
    procedures: LHProcedures = LHProcedures()
    episodes: int = 0
    last_24h: int = 0
    trust_distribution: Dict[str, int] = {}
    top_types: List[TopType] = []

class HealingAction(BaseModel):
    id: str
    name: str
    severity: str = "medium"

class LHHealing(BaseModel):
    available_actions: List[HealingAction] = []

class LearnHealDashboardResponse(BaseModel):
    health_snapshot: HealthSnapshot = HealthSnapshot()
    learning: LHLearning = LHLearning()
    healing: LHHealing = LHHealing()

class SkillItem(BaseModel):
    id: str
    name: Optional[str] = None
    goal: Optional[str] = None
    type: str = "Unknown"
    usage: int = 0
    trust: Optional[float] = None
    success: Optional[float] = None

class SkillsResponse(BaseModel):
    skills: List[SkillItem] = []


# ==================== System Health Tab ====================

class ResourceMetrics(BaseModel):
    cpu_total: float = 0.0
    cpu_per_core: List[float] = []
    cpu_cores: int = 0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0

class ServiceStatus(BaseModel):
    status: str = "unknown"

class HealthServices(BaseModel):
    api: ServiceStatus = ServiceStatus()
    database: ServiceStatus = ServiceStatus()
    qdrant: ServiceStatus = ServiceStatus()
    ollama: ServiceStatus = ServiceStatus()
    ml_engine: ServiceStatus = ServiceStatus()

class OrganProgress(BaseModel):
    name: str
    progress: int = 0

class SystemHealthDashboardResponse(BaseModel):
    overall: str = "unknown"
    resources: ResourceMetrics = ResourceMetrics()
    services: HealthServices = HealthServices()
    organs: List[OrganProgress] = []

class ProcessInfo(BaseModel):
    pid: int
    name: Optional[str] = None
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None

class ProcessesResponse(BaseModel):
    processes: List[ProcessInfo] = []


# ==================== Governance Tab ====================

class GovernanceStatsResponse(BaseModel):
    status: str = "ok"

class GovernanceRule(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None

class GovernanceRulesResponse(BaseModel):
    rules: List[GovernanceRule] = []

class GovernanceDecision(BaseModel):
    id: Optional[str] = None
    status: Optional[str] = None
    component: Optional[str] = None

class GovernancePendingResponse(BaseModel):
    decisions: List[GovernanceDecision] = []

class GovernanceHistoryResponse(BaseModel):
    history: List[Dict[str, Any]] = []

class GovernancePillar(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None

class GovernancePillarsResponse(BaseModel):
    pillars: List[GovernancePillar] = []


# ==================== Cognitive Tab ====================

class CognitiveStatsResponse(BaseModel):
    status: str = "ok"
    stats: Dict[str, Any] = {}

class CognitiveDecisionsResponse(BaseModel):
    decisions: List[Dict[str, Any]] = []


# ==================== Tab Aggregation Endpoints ====================
# These are the /api/tabs/*/full endpoints

class TabDocsFullResponse(BaseModel):
    """Aggregated data for Docs tab mount."""
    documents: List[Dict[str, Any]] = []
    folders: List[str] = []
    total: int = 0

class TabChatFullResponse(BaseModel):
    """Aggregated data for Chat tab mount."""
    recent_chats: List[Dict[str, Any]] = []
    total_chats: int = 0

class TabOracleFullResponse(BaseModel):
    """Aggregated data for Oracle tab mount."""
    dashboard: OracleDashboardResponse = OracleDashboardResponse()
    trust_distribution: TrustDistributionResponse = TrustDistributionResponse()

class TabLearnHealFullResponse(BaseModel):
    """Aggregated data for Learning & Healing tab mount."""
    dashboard: LearnHealDashboardResponse = LearnHealDashboardResponse()
    skills: List[SkillItem] = []

class DiagnosticSensors(BaseModel):
    uptime_hours: int = 0
    connection_pool_size: int = 0
    active_tasks: int = 0
    last_error: str = "None"

class DiagnosticHealing(BaseModel):
    playbooks_run: int = 0
    successful_heals: int = 0

class DiagnosticTrends(BaseModel):
    cpu_trend: str = "stable"
    memory_trend: str = "stable"
    api_latency_ms: int = 0

class TabHealthFullResponse(BaseModel):
    """Aggregated data for System Health tab mount."""
    diagnostic_sensors: DiagnosticSensors = DiagnosticSensors()
    diagnostic_healing: DiagnosticHealing = DiagnosticHealing()
    diagnostic_trends: DiagnosticTrends = DiagnosticTrends()

class KPISummary(BaseModel):
    user_retention: str = "0%"
    system_efficiency: str = "0%"
    cost_per_query: str = "$0"

class KPIDashboard(BaseModel):
    active_users: int = 0
    compute_hours: int = 0

class MonitoringMetrics(BaseModel):
    avg_response_time: str = "0s"
    cache_hit_rate: str = "0%"

class TabBIFullResponse(BaseModel):
    """Aggregated data for BI tab mount."""
    kpi_summary: KPISummary = KPISummary()
    kpi_dashboard: KPIDashboard = KPIDashboard()
    monitoring_metrics: MonitoringMetrics = MonitoringMetrics()
