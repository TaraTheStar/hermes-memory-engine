import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from domain.core.models import Base, Event, Project, Milestone, Skill, IdentityMarker, RelationalEdge

class StructuralLedger:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.environ.get("HERMES_STRUCTURAL_DB", "/data/hermes_memory_engine/structural/structure.db")
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_project(self, name: str, repository_url: Optional[str] = None) -> str:
        session = self.Session()
        try:
            p_id = f"proj_{uuid.uuid4().hex[:8]}"
            new_project = Project(id=p_id, name=name, repository_url=repository_url)
            session.add(new_project)
            session.commit()
            return p_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def add_milestone(self, title: str, description: str, project_id: Optional[str] = None, importance: float = 1.0) -> str:
        session = self.Session()
        try:
            m_id = f"ms_{uuid.uuid4().hex[:8]}"
            from datetime import datetime, timezone
            new_milestone = Milestone(
                id=m_id,
                title=title,
                description=description,
                project_id=project_id,
                importance_score=importance,
                timestamp=datetime.now(timezone.utc)
            )
            session.add(new_milestone)
            session.commit()
            return m_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def add_edge(self, source_id: str, target_id: str, relationship_type: str, weight: float = 1.0) -> str:
        session = self.Session()
        try:
            edge_id = f"edge_{uuid.uuid4().hex[:8]}"
            new_edge = RelationalEdge(
                id=edge_id,
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                weight=weight
            )
            session.add(new_edge)
            session.commit()
            return edge_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def add_skill(self, name: str, description: str, proficiency: float = 0.1) -> str:
        session = self.Session()
        try:
            s_id = f"sk_{uuid.uuid4().hex[:8]}"
            new_skill = Skill(
                id=s_id,
                name=name,
                description=description,
                proficiency_level=proficiency,
                last_used=datetime.utcnow()
            )
            session.add(new_skill)
            session.commit()
            return s_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def set_identity_marker(self, key: str, value: str, confidence: float = 1.0) -> str:
        session = self.Session()
        try:
            marker = session.query(IdentityMarker).filter_by(key=key).first()
            if marker:
                marker.value = value
                marker.confidence_score = confidence
                marker.updated_at = datetime.utcnow()
            else:
                i_id = f"id_{uuid.uuid4().hex[:8]}"
                marker = IdentityMarker(id=i_id, key=key, value=value, confidence_score=confidence)
                session.add(marker)
            session.commit()
            return marker.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_all_milestones(self) -> List[Dict[str, Any]]:
        session = self.Session()
        try:
            milestones = session.query(Milestone).all()
            return [{
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "timestamp": m.timestamp.isoformat(),
                "importance": m.importance_score
            } for m in milestones]
        finally:
            session.close()
