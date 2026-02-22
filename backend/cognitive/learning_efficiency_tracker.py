"""
Learning Efficiency Tracker - Data-to-Insight Ratio Tracking

Tracks how much data (bytes, documents, chunks) is required to gain:
- New insights
- New domains of knowledge
- New intelligence/skills
- Trust score improvements

Key Metrics:
- Data-to-Insight Ratio (bytes per insight)
- Domain Acquisition Efficiency (data per domain)
- Skill Acquisition Rate (data per skill level)
- Learning Curve Analysis

Classes:
- `Insight`
- `DomainAcquisition`
- `LearningEfficiencyMetrics`
- `LearningEfficiencyTracker`

Key Methods:
- `record_data_consumption()`
- `record_insight()`
- `record_domain_acquisition()`
- `get_efficiency_metrics()`
- `get_optimal_learning_paths()`
- `export_metrics()`
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from collections import defaultdict
import json

from cognitive.learning_memory import LearningMemoryManager, LearningExample
from models.database_models import Document, DocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """A single insight gained from data."""
    insight_id: str
    insight_type: str  # "concept", "pattern", "skill", "domain", "procedure"
    description: str
    data_consumed: Dict[str, float]  # {"bytes": 1024, "documents": 1, "chunks": 5}
    trust_score: float
    domain: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    time_since_last_insight: Optional[timedelta] = None  # Time since previous insight
    time_to_insight: Optional[timedelta] = None  # Time spent learning before this insight
    genesis_key_id: Optional[str] = None
    learning_example_id: Optional[str] = None


@dataclass
class DomainAcquisition:
    """Tracking when a new domain is acquired."""
    domain: str
    first_insight_time: datetime
    data_consumed_at_acquisition: Dict[str, float]
    time_to_acquisition: timedelta  # Time from start to domain acquisition
    total_insights: int = 0
    current_trust_score: float = 0.0
    skill_level: str = "NOVICE"  # NOVICE, BEGINNER, INTERMEDIATE, ADVANCED, EXPERT
    insights_per_hour: float = 0.0  # Learning velocity
    last_insight_time: Optional[datetime] = None


@dataclass
class LearningEfficiencyMetrics:
    """Efficiency metrics for learning."""
    # Data-to-Insight Ratios
    bytes_per_insight: float
    documents_per_insight: float
    chunks_per_insight: float
    
    # Time-to-Insight Ratios
    seconds_per_insight: float
    hours_per_insight: float
    time_per_insight_trend: List[Tuple[datetime, float]]  # (time, seconds_per_insight)
    
    # Learning Velocity
    insights_per_hour: float
    insights_per_day: float
    velocity_trend: List[Tuple[datetime, float]]  # (time, insights_per_hour)
    
    # Domain Acquisition
    bytes_per_domain: float
    documents_per_domain: float
    time_to_domain_acquisition: timedelta
    average_time_to_domain: timedelta
    
    # Skill Progression
    bytes_per_skill_level: Dict[str, float]  # {"BEGINNER": 1024, "INTERMEDIATE": 2048}
    time_per_skill_level: Dict[str, timedelta]  # {"BEGINNER": timedelta(hours=2)}
    data_efficiency_trend: List[Tuple[datetime, float]]  # (time, bytes_per_insight)
    
    # Learning Curve
    learning_curve: List[Tuple[int, float]]  # (insight_count, cumulative_efficiency)
    temporal_learning_curve: List[Tuple[datetime, float]]  # (time, cumulative_efficiency)
    
    # Domain-Specific Efficiency
    domain_efficiency: Dict[str, Dict[str, float]]  # {"python": {"bytes_per_insight": 512}}
    domain_temporal_efficiency: Dict[str, Dict[str, Any]]  # {"python": {"seconds_per_insight": 120}}


class LearningEfficiencyTracker:
    """
    Tracks learning efficiency: how much data is required to gain insights/domains/intelligence.
    
    Key Capabilities:
    1. Track data consumption (bytes, documents, chunks)
    2. Identify when new insights are gained
    3. Calculate data-to-insight ratios
    4. Track domain acquisition efficiency
    5. Analyze learning curves
    6. Identify optimal learning paths
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.learning_memory = LearningMemoryManager(session, None)
        
        # Track cumulative data consumption
        self.total_bytes_consumed = 0.0
        self.total_documents_consumed = 0
        self.total_chunks_consumed = 0
        
        # Track time consumption
        self.start_time: Optional[datetime] = None
        self.total_learning_time: timedelta = timedelta(0)
        self.last_insight_time: Optional[datetime] = None
        
        # Track insights gained
        self.insights: List[Insight] = []
        self.domain_acquisitions: Dict[str, DomainAcquisition] = {}
        
        # Track by domain
        self.domain_data_consumption: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            "bytes": 0.0,
            "documents": 0,
            "chunks": 0
        })
        
        # Track time by domain
        self.domain_time_consumption: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_seconds": 0.0,
            "first_insight": None,
            "last_insight": None,
            "insights": []
        })
        
        # Load existing data
        self._load_existing_data()
    
    def _load_existing_data(self):
        """Load existing data consumption from database."""
        try:
            # Count total documents and chunks
            total_docs = self.session.query(Document).count()
            total_chunks = self.session.query(DocumentChunk).count()
            
            # Estimate bytes (average chunk size * chunks)
            # Or sum actual document sizes if available
            total_bytes = sum(
                getattr(doc, 'file_size', 0) or 0 
                for doc in self.session.query(Document).all()
            )
            
            self.total_documents_consumed = total_docs
            self.total_chunks_consumed = total_chunks
            self.total_bytes_consumed = total_bytes or (total_chunks * 512)  # Estimate
            
            logger.info(f"Loaded existing data: {total_bytes/1024/1024:.2f} MB, "
                       f"{total_docs} docs, {total_chunks} chunks")
        except Exception as e:
            logger.warning(f"Could not load existing data: {e}")
    
    def record_data_consumption(
        self,
        bytes_consumed: float,
        documents_consumed: int = 1,
        chunks_consumed: int = 0,
        domain: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ):
        """
        Record data consumption (when documents are ingested).
        
        Args:
            bytes_consumed: Bytes of data consumed
            documents_consumed: Number of documents
            chunks_consumed: Number of chunks
            domain: Optional domain/category
            genesis_key_id: Optional Genesis Key tracking
        """
        self.total_bytes_consumed += bytes_consumed
        self.total_documents_consumed += documents_consumed
        self.total_chunks_consumed += chunks_consumed
        
        if domain:
            self.domain_data_consumption[domain]["bytes"] += bytes_consumed
            self.domain_data_consumption[domain]["documents"] += documents_consumed
            self.domain_data_consumption[domain]["chunks"] += chunks_consumed
    
    def record_insight(
        self,
        insight_type: str,
        description: str,
        trust_score: float,
        domain: Optional[str] = None,
        learning_example_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None,
        time_to_insight: Optional[timedelta] = None
    ) -> Insight:
        """
        Record a new insight gained.
        
        Args:
            insight_type: Type of insight ("concept", "pattern", "skill", "domain", "procedure")
            description: Description of the insight
            trust_score: Trust score of the insight
            domain: Domain/category
            learning_example_id: Link to learning example
            genesis_key_id: Link to Genesis Key
            
        Returns:
            Insight object
        """
        # Initialize start time if first insight
        current_time = datetime.now()
        if self.start_time is None:
            self.start_time = current_time
        
        # Calculate time since last insight
        time_since_last = None
        if self.last_insight_time:
            time_since_last = current_time - self.last_insight_time
        
        # Calculate time to insight (if not provided)
        if time_to_insight is None:
            if self.last_insight_time:
                time_to_insight = current_time - self.last_insight_time
            else:
                time_to_insight = current_time - self.start_time if self.start_time else timedelta(0)
        
        # Update total learning time
        self.total_learning_time += time_to_insight
        
        # Calculate data consumed since last insight
        # For now, use average distribution
        data_consumed = {
            "bytes": self.total_bytes_consumed / max(len(self.insights) + 1, 1),
            "documents": self.total_documents_consumed / max(len(self.insights) + 1, 1),
            "chunks": self.total_chunks_consumed / max(len(self.insights) + 1, 1)
        }
        
        # If domain-specific, use domain data
        if domain and domain in self.domain_data_consumption:
            domain_data = self.domain_data_consumption[domain]
            total_domain_insights = sum(
                1 for i in self.insights if i.domain == domain
            )
            if total_domain_insights > 0:
                data_consumed = {
                    "bytes": domain_data["bytes"] / (total_domain_insights + 1),
                    "documents": domain_data["documents"] / (total_domain_insights + 1),
                    "chunks": domain_data["chunks"] / (total_domain_insights + 1)
                }
            
            # Track domain time
            domain_time = self.domain_time_consumption[domain]
            if domain_time["first_insight"] is None:
                domain_time["first_insight"] = current_time
            domain_time["last_insight"] = current_time
            domain_time["total_seconds"] += time_to_insight.total_seconds()
            domain_time["insights"].append(current_time)
        
        insight = Insight(
            insight_id=f"INS-{current_time.timestamp()}",
            insight_type=insight_type,
            description=description,
            data_consumed=data_consumed,
            trust_score=trust_score,
            domain=domain,
            timestamp=current_time,
            time_since_last_insight=time_since_last,
            time_to_insight=time_to_insight,
            learning_example_id=learning_example_id,
            genesis_key_id=genesis_key_id
        )
        
        self.insights.append(insight)
        self.last_insight_time = current_time
        
        # Check if this is a new domain
        if domain and domain not in self.domain_acquisitions:
            time_to_acq = current_time - self.start_time if self.start_time else timedelta(0)
            self.domain_acquisitions[domain] = DomainAcquisition(
                domain=domain,
                first_insight_time=current_time,
                data_consumed_at_acquisition=data_consumed.copy(),
                time_to_acquisition=time_to_acq,
                total_insights=1,
                current_trust_score=trust_score,
                last_insight_time=current_time
            )
        elif domain:
            acq = self.domain_acquisitions[domain]
            acq.total_insights += 1
            acq.current_trust_score = max(acq.current_trust_score, trust_score)
            acq.last_insight_time = current_time
            
            # Calculate insights per hour for this domain
            if acq.first_insight_time:
                domain_duration = (current_time - acq.first_insight_time).total_seconds() / 3600
                if domain_duration > 0:
                    acq.insights_per_hour = acq.total_insights / domain_duration
        
        logger.info(f"Recorded insight: {insight_type} - {description[:50]}... "
                   f"(Data: {data_consumed['bytes']/1024:.2f} KB)")
        
        return insight
    
    def record_domain_acquisition(
        self,
        domain: str,
        skill_level: str = "NOVICE"
    ):
        """
        Explicitly record domain acquisition.
        
        Args:
            domain: Domain name
            skill_level: Initial skill level
        """
        if domain not in self.domain_acquisitions:
            data_consumed = self.domain_data_consumption.get(domain, {
                "bytes": 0.0,
                "documents": 0,
                "chunks": 0
            })
            
            current_time = datetime.now()
            time_to_acq = current_time - self.start_time if self.start_time else timedelta(0)
            self.domain_acquisitions[domain] = DomainAcquisition(
                domain=domain,
                first_insight_time=current_time,
                data_consumed_at_acquisition=data_consumed.copy(),
                time_to_acquisition=time_to_acq,
                skill_level=skill_level
            )
    
    def get_efficiency_metrics(
        self,
        domain: Optional[str] = None,
        time_window: Optional[timedelta] = None
    ) -> LearningEfficiencyMetrics:
        """
        Calculate learning efficiency metrics.
        
        Args:
            domain: Optional domain filter
            time_window: Optional time window filter
            
        Returns:
            LearningEfficiencyMetrics object
        """
        # Filter insights
        filtered_insights = self.insights
        if domain:
            filtered_insights = [i for i in filtered_insights if i.domain == domain]
        if time_window:
            cutoff = datetime.now() - time_window
            filtered_insights = [i for i in filtered_insights if i.timestamp >= cutoff]
        
        if not filtered_insights:
            return LearningEfficiencyMetrics(
                bytes_per_insight=0.0,
                documents_per_insight=0.0,
                chunks_per_insight=0.0,
                seconds_per_insight=0.0,
                hours_per_insight=0.0,
                time_per_insight_trend=[],
                insights_per_hour=0.0,
                insights_per_day=0.0,
                velocity_trend=[],
                bytes_per_domain=0.0,
                documents_per_domain=0.0,
                time_to_domain_acquisition=timedelta(0),
                average_time_to_domain=timedelta(0),
                bytes_per_skill_level={},
                time_per_skill_level={},
                data_efficiency_trend=[],
                learning_curve=[],
                temporal_learning_curve=[],
                domain_efficiency={},
                domain_temporal_efficiency={}
            )
        
        # Calculate data-to-insight ratios
        total_bytes = sum(i.data_consumed.get("bytes", 0) for i in filtered_insights)
        total_docs = sum(i.data_consumed.get("documents", 0) for i in filtered_insights)
        total_chunks = sum(i.data_consumed.get("chunks", 0) for i in filtered_insights)
        
        num_insights = len(filtered_insights)
        
        bytes_per_insight = total_bytes / num_insights if num_insights > 0 else 0.0
        documents_per_insight = total_docs / num_insights if num_insights > 0 else 0.0
        chunks_per_insight = total_chunks / num_insights if num_insights > 0 else 0.0
        
        # Calculate time-to-insight ratios
        total_time_seconds = sum(
            (i.time_to_insight.total_seconds() if i.time_to_insight else 0)
            for i in filtered_insights
        )
        seconds_per_insight = total_time_seconds / num_insights if num_insights > 0 else 0.0
        hours_per_insight = seconds_per_insight / 3600
        
        # Calculate learning velocity
        if filtered_insights and len(filtered_insights) > 1:
            first_insight_time = min(i.timestamp for i in filtered_insights)
            last_insight_time = max(i.timestamp for i in filtered_insights)
            total_duration_hours = (last_insight_time - first_insight_time).total_seconds() / 3600
            insights_per_hour = num_insights / total_duration_hours if total_duration_hours > 0 else 0.0
            insights_per_day = insights_per_hour * 24
        else:
            insights_per_hour = 0.0
            insights_per_day = 0.0
        
        # Time per insight trend
        time_per_insight_trend = []
        for insight in filtered_insights:
            if insight.time_to_insight:
                time_per_insight_trend.append((
                    insight.timestamp,
                    insight.time_to_insight.total_seconds()
                ))
        
        # Velocity trend (insights per hour over time)
        velocity_trend = []
        if len(filtered_insights) > 1:
            # Calculate rolling window velocity
            window_hours = 1.0  # 1 hour window
            for i, insight in enumerate(filtered_insights):
                window_start = insight.timestamp - timedelta(hours=window_hours)
                window_insights = [
                    ins for ins in filtered_insights
                    if ins.timestamp >= window_start and ins.timestamp <= insight.timestamp
                ]
                if len(window_insights) > 1:
                    window_duration = (window_insights[-1].timestamp - window_insights[0].timestamp).total_seconds() / 3600
                    window_velocity = len(window_insights) / window_duration if window_duration > 0 else 0.0
                    velocity_trend.append((insight.timestamp, window_velocity))
        
        # Domain acquisition metrics
        bytes_per_domain = 0.0
        documents_per_domain = 0.0
        time_to_domain = timedelta(0)
        average_time_to_domain = timedelta(0)
        
        if self.domain_acquisitions:
            total_domain_bytes = sum(
                d.data_consumed_at_acquisition.get("bytes", 0)
                for d in self.domain_acquisitions.values()
            )
            total_domain_docs = sum(
                d.data_consumed_at_acquisition.get("documents", 0)
                for d in self.domain_acquisitions.values()
            )
            num_domains = len(self.domain_acquisitions)
            
            bytes_per_domain = total_domain_bytes / num_domains if num_domains > 0 else 0.0
            documents_per_domain = total_domain_docs / num_domains if num_domains > 0 else 0.0
            
            # Average time to domain acquisition
            if len(self.domain_acquisitions) > 1:
                times = sorted([d.first_insight_time for d in self.domain_acquisitions.values()])
                if len(times) >= 2:
                    time_to_domain = (times[-1] - times[0]) / (len(times) - 1)
            
            # Calculate average time to domain from time_to_acquisition
            total_time_to_domain = sum(
                d.time_to_acquisition for d in self.domain_acquisitions.values()
            )
            average_time_to_domain = total_time_to_domain / num_domains if num_domains > 0 else timedelta(0)
        
        # Skill progression (bytes and time per skill level)
        bytes_per_skill_level = {}
        time_per_skill_level = {}
        skill_levels = ["NOVICE", "BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"]
        for level in skill_levels:
            level_domains = [
                d for d in self.domain_acquisitions.values()
                if d.skill_level == level
            ]
            if level_domains:
                total_level_bytes = sum(
                    d.data_consumed_at_acquisition.get("bytes", 0)
                    for d in level_domains
                )
                bytes_per_skill_level[level] = total_level_bytes / len(level_domains)
                
                # Average time to reach this skill level
                total_level_time = sum(
                    d.time_to_acquisition for d in level_domains
                )
                time_per_skill_level[level] = total_level_time / len(level_domains) if len(level_domains) > 0 else timedelta(0)
        
        # Efficiency trend over time
        data_efficiency_trend = []
        cumulative_bytes = 0.0
        for i, insight in enumerate(filtered_insights):
            cumulative_bytes += insight.data_consumed.get("bytes", 0)
            efficiency = cumulative_bytes / (i + 1) if i > 0 else 0.0
            data_efficiency_trend.append((insight.timestamp, efficiency))
        
        # Learning curve (efficiency vs insight count)
        learning_curve = []
        cumulative_bytes = 0.0
        for i, insight in enumerate(filtered_insights):
            cumulative_bytes += insight.data_consumed.get("bytes", 0)
            efficiency = cumulative_bytes / (i + 1) if i > 0 else 0.0
            learning_curve.append((i + 1, efficiency))
        
        # Temporal learning curve (efficiency over time)
        temporal_learning_curve = []
        cumulative_bytes = 0.0
        for i, insight in enumerate(filtered_insights):
            cumulative_bytes += insight.data_consumed.get("bytes", 0)
            efficiency = cumulative_bytes / (i + 1) if i > 0 else 0.0
            temporal_learning_curve.append((insight.timestamp, efficiency))
        
        # Domain-specific efficiency (data and time)
        domain_efficiency = {}
        domain_temporal_efficiency = {}
        for domain_name, data in self.domain_data_consumption.items():
            domain_insights = [i for i in filtered_insights if i.domain == domain_name]
            if domain_insights:
                domain_efficiency[domain_name] = {
                    "bytes_per_insight": data["bytes"] / len(domain_insights),
                    "documents_per_insight": data["documents"] / len(domain_insights) if len(domain_insights) > 0 else 0,
                    "chunks_per_insight": data["chunks"] / len(domain_insights) if len(domain_insights) > 0 else 0,
                    "total_insights": len(domain_insights)
                }
                
                # Temporal efficiency for domain
                domain_time_data = self.domain_time_consumption.get(domain_name, {})
                domain_total_seconds = domain_time_data.get("total_seconds", 0.0)
                domain_acq = self.domain_acquisitions.get(domain_name)
                
                domain_temporal_efficiency[domain_name] = {
                    "seconds_per_insight": domain_total_seconds / len(domain_insights) if len(domain_insights) > 0 else 0.0,
                    "hours_per_insight": (domain_total_seconds / len(domain_insights) / 3600) if len(domain_insights) > 0 else 0.0,
                    "insights_per_hour": domain_acq.insights_per_hour if domain_acq else 0.0,
                    "time_to_acquisition": domain_acq.time_to_acquisition.total_seconds() / 3600 if domain_acq else 0.0,
                    "first_insight": domain_time_data.get("first_insight").isoformat() if domain_time_data.get("first_insight") else None,
                    "last_insight": domain_time_data.get("last_insight").isoformat() if domain_time_data.get("last_insight") else None
                }
        
        return LearningEfficiencyMetrics(
            bytes_per_insight=bytes_per_insight,
            documents_per_insight=documents_per_insight,
            chunks_per_insight=chunks_per_insight,
            seconds_per_insight=seconds_per_insight,
            hours_per_insight=hours_per_insight,
            time_per_insight_trend=time_per_insight_trend,
            insights_per_hour=insights_per_hour,
            insights_per_day=insights_per_day,
            velocity_trend=velocity_trend,
            bytes_per_domain=bytes_per_domain,
            documents_per_domain=documents_per_domain,
            time_to_domain_acquisition=time_to_domain,
            average_time_to_domain=average_time_to_domain,
            bytes_per_skill_level=bytes_per_skill_level,
            time_per_skill_level=time_per_skill_level,
            data_efficiency_trend=data_efficiency_trend,
            learning_curve=learning_curve,
            temporal_learning_curve=temporal_learning_curve,
            domain_efficiency=domain_efficiency,
            domain_temporal_efficiency=domain_temporal_efficiency
        )
    
    def get_optimal_learning_paths(self) -> Dict[str, Any]:
        """
        Identify optimal learning paths based on efficiency data.
        
        Returns:
            Dict with recommended learning paths
        """
        # Find most efficient domains
        domain_eff = {}
        for domain, metrics in self.get_efficiency_metrics().domain_efficiency.items():
            domain_eff[domain] = metrics.get("bytes_per_insight", float('inf'))
        
        # Sort by efficiency (lower is better)
        sorted_domains = sorted(domain_eff.items(), key=lambda x: x[1])
        
        # Recommend learning order
        recommendations = {
            "most_efficient_domains": [
                {"domain": domain, "bytes_per_insight": eff}
                for domain, eff in sorted_domains[:5]
            ],
            "learning_path": [
                domain for domain, _ in sorted_domains[:10]
            ],
            "efficiency_insights": {
                "average_bytes_per_insight": self.get_efficiency_metrics().bytes_per_insight,
                "most_efficient_domain": sorted_domains[0][0] if sorted_domains else None,
                "least_efficient_domain": sorted_domains[-1][0] if sorted_domains else None
            }
        }
        
        return recommendations
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics as JSON-serializable dict."""
        metrics = self.get_efficiency_metrics()
        
        return {
            "summary": {
                "total_bytes_consumed": self.total_bytes_consumed,
                "total_documents_consumed": self.total_documents_consumed,
                "total_chunks_consumed": self.total_chunks_consumed,
                "total_insights": len(self.insights),
                "total_domains": len(self.domain_acquisitions)
            },
            "efficiency": {
                "bytes_per_insight": metrics.bytes_per_insight,
                "documents_per_insight": metrics.documents_per_insight,
                "chunks_per_insight": metrics.chunks_per_insight,
                "seconds_per_insight": metrics.seconds_per_insight,
                "hours_per_insight": metrics.hours_per_insight,
                "insights_per_hour": metrics.insights_per_hour,
                "insights_per_day": metrics.insights_per_day,
                "bytes_per_domain": metrics.bytes_per_domain,
                "documents_per_domain": metrics.documents_per_domain,
                "average_time_to_domain_hours": metrics.average_time_to_domain.total_seconds() / 3600
            },
            "domains": {
                domain: {
                    "insights": acq.total_insights,
                    "trust_score": acq.current_trust_score,
                    "skill_level": acq.skill_level,
                    "data_at_acquisition": acq.data_consumed_at_acquisition
                }
                for domain, acq in self.domain_acquisitions.items()
            },
            "domain_efficiency": metrics.domain_efficiency,
            "domain_temporal_efficiency": metrics.domain_temporal_efficiency,
            "learning_curve": [
                {"insight_count": count, "efficiency": eff}
                for count, eff in metrics.learning_curve
            ],
            "temporal_learning_curve": [
                {"timestamp": ts.isoformat(), "efficiency": eff}
                for ts, eff in metrics.temporal_learning_curve
            ],
            "velocity_trend": [
                {"timestamp": ts.isoformat(), "insights_per_hour": vel}
                for ts, vel in metrics.velocity_trend
            ],
            "time_per_insight_trend": [
                {"timestamp": ts.isoformat(), "seconds_per_insight": secs}
                for ts, secs in metrics.time_per_insight_trend
            ],
            "optimal_paths": self.get_optimal_learning_paths()
        }
