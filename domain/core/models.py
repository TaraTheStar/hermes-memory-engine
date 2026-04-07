from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid
from typing import Dict, Any

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Event:
    def __init__(self, text: str, event_type: str, metadata: Dict[str, Any]):
        self.text = text
        self.event_type = event_type
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "type": self.event_type,
            **self.metadata
        }

class Project(Base):
    __tablename__ = 'projects'

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    repository_url = Column(String, nullable=True)
    status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

    milestones = relationship("Milestone", back_populates="project")

class Milestone(Base):
    __tablename__ = 'milestones'

    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    importance_score = Column(Float, default=1.0)
    project_id = Column(String, ForeignKey('projects.id'), nullable=True)

    project = relationship("Project", back_populates="milestones")

class Skill(Base):
    __tablename__ = 'skills'

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    proficiency_level = Column(Float, default=0.1)
    last_used = Column(DateTime, nullable=True)

class IdentityMarker(Base):
    __tablename__ = 'identity_markers'

    id = Column(String, primary_key=True, default=generate_uuid)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    confidence_score = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RelationalEdge(Base):
    __tablename__ = 'relational_edges'

    id = Column(String, primary_key=True, default=generate_uuid)
    source_id = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    relationship_type = Column(String, nullable=False)
    weight = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
