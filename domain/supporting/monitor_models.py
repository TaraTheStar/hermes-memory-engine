import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy import Column, String, Float, DateTime, JSON, Integer, Boolean, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# New Base for Monitoring models
MonitoringBase = declarative_base()

class GraphSnapshot(MonitoringBase):
    """
    Stores a point-in-time 'fingerprint' of the knowledge graph's structure.
    """
    __tablename__ = 'graph_snapshots'

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Global Metrics
    density = Column(Float)
    community_count = Column(Integer)
    
    # Node-level Metrics (Stored as JSON for flexibility)
    # Format: { "node_id": {"degree": 0.5, "betweenness": 0.1, ...}, ... }
    centrality_metrics = Column(JSON)
    
    # Metadata
    metadata_tags = Column(JSON)

class AnomalyEvent(MonitoringBase):
    """
    Records detected structural anomalies for auditing and trigger history.
    """
    __tablename__ = 'anomaly_events'

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    anomaly_type = Column(String, nullable=False)  # e.g., 'HUB_EMERGENCE', 'COMMUNITY_SPLIT'
    description = Column(String, nullable=False)
    severity = Column(String, default='medium')   # 'low', 'medium', 'high', 'critical'
    
    # The raw data that triggered the anomaly for debugging/audit
    trigger_data = Column(JSON)

    # Whether this anomaly has been processed by InsightTrigger
    processed = Column(Boolean, default=False)
