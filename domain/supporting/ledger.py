import logging
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SASession
from domain.core.models import Base, Project, Milestone, Skill, IdentityMarker, RelationalEdge
from infrastructure.paths import default_structural_db
# Import monitoring models so their tables are registered on Base.metadata
import domain.supporting.monitor_models  # noqa: F401

class StructuralLedger:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = default_structural_db()
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def _use_session(self, session: Optional[SASession] = None):
        """
        If a session is provided, yield it and flush on success (caller owns the transaction).
        Otherwise, create a new session and commit/rollback/close it automatically.
        """
        owned = session is None
        if owned:
            session = self.Session()
        try:
            yield session
            if owned:
                session.commit()
            else:
                session.flush()
        except Exception:
            if owned:
                session.rollback()
            raise
        finally:
            if owned:
                session.close()

    def add_project(self, name: str, repository_url: Optional[str] = None, session: Optional[SASession] = None) -> str:
        with self._use_session(session) as s:
            existing = s.query(Project).filter_by(name=name).first()
            if existing:
                if repository_url is not None:
                    existing.repository_url = repository_url
                return existing.id
            p_id = f"proj_{uuid.uuid4().hex[:8]}"
            s.add(Project(id=p_id, name=name, repository_url=repository_url))
            return p_id

    def add_milestone(self, title: str, description: str, project_id: Optional[str] = None, importance: float = 1.0, session: Optional[SASession] = None) -> str:
        with self._use_session(session) as s:
            m_id = f"ms_{uuid.uuid4().hex[:8]}"
            s.add(Milestone(
                id=m_id,
                title=title,
                description=description,
                project_id=project_id,
                importance_score=importance,
                timestamp=datetime.now(timezone.utc)
            ))
            return m_id

    def add_edge(self, source_id: str, target_id: str, relationship_type: str, weight: float = 1.0, session: Optional[SASession] = None) -> str:
        with self._use_session(session) as s:
            edge_id = f"edge_{uuid.uuid4().hex[:8]}"
            s.add(RelationalEdge(
                id=edge_id,
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type,
                weight=weight
            ))
            return edge_id

    def add_skill(self, name: str, description: str, proficiency: float = 0.1, session: Optional[SASession] = None) -> str:
        with self._use_session(session) as s:
            existing = s.query(Skill).filter_by(name=name).first()
            if existing:
                existing.description = description
                existing.proficiency_level = max(existing.proficiency_level, proficiency)
                existing.last_used = datetime.now(timezone.utc)
                return existing.id
            s_id = f"sk_{uuid.uuid4().hex[:8]}"
            s.add(Skill(
                id=s_id,
                name=name,
                description=description,
                proficiency_level=proficiency,
                last_used=datetime.now(timezone.utc)
            ))
            return s_id

    def set_identity_marker(self, key: str, value: str, confidence: float = 1.0, session: Optional[SASession] = None) -> str:
        with self._use_session(session) as s:
            marker = s.query(IdentityMarker).filter_by(key=key).first()
            if marker:
                marker.value = value
                marker.confidence_score = confidence
                marker.updated_at = datetime.now(timezone.utc)
            else:
                i_id = f"id_{uuid.uuid4().hex[:8]}"
                marker = IdentityMarker(id=i_id, key=key, value=value, confidence_score=confidence)
                s.add(marker)
            return marker.id

    def count_edges(self, relationship_type: Optional[str] = None, session: Optional[SASession] = None) -> int:
        """Return the total number of edges, optionally filtered by type."""
        with self._use_session(session) as s:
            q = s.query(RelationalEdge)
            if relationship_type:
                q = q.filter_by(relationship_type=relationship_type)
            return q.count()

    def prune_stale_edges(self, max_age_days: int = 90, min_weight: float = 0.5,
                          max_edges: int = 10000, session: Optional[SASession] = None) -> int:
        """Remove low-value edges to keep the graph bounded.

        Pruning strategy (applied in order):
        1. Delete edges older than *max_age_days* with weight below *min_weight*.
        2. If total edge count still exceeds *max_edges*, delete the oldest
           lowest-weight edges until the cap is met.

        Returns the number of edges deleted.
        """
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        deleted = 0

        with self._use_session(session) as s:
            # Phase 1: age + weight filter
            stale = s.query(RelationalEdge).filter(
                RelationalEdge.created_at < cutoff,
                RelationalEdge.weight < min_weight,
            ).all()
            for edge in stale:
                s.delete(edge)
                deleted += 1

            s.flush()

            # Phase 2: hard cap on total edges
            total = s.query(RelationalEdge).count()
            if total > max_edges:
                excess = total - max_edges
                weakest = (
                    s.query(RelationalEdge)
                    .order_by(RelationalEdge.weight.asc(), RelationalEdge.created_at.asc())
                    .limit(excess)
                    .all()
                )
                for edge in weakest:
                    s.delete(edge)
                    deleted += 1

        if deleted:
            logger.info("Pruned %d stale/excess edges (age cutoff=%d days, weight<%s, cap=%d)",
                        deleted, max_age_days, min_weight, max_edges)
        return deleted

    def get_all_milestones(self, session: Optional[SASession] = None) -> List[Dict[str, Any]]:
        with self._use_session(session) as s:
            milestones = s.query(Milestone).all()
            return [{
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "timestamp": m.timestamp.isoformat(),
                "importance": m.importance_score
            } for m in milestones]
