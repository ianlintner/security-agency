import json
import os

# Removed unused import List

from sqlalchemy import JSON, Column, MetaData, String, Table, create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.types import TEXT, TypeDecorator

from core.models import ScanRequest, ScanResult, Workflow


class SQLiteJSON(TypeDecorator):  # pylint: disable=abstract-method, too-many-ancestors
    """Fallback JSON type for SQLite (stores as TEXT)."""

    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None

    @property
    def python_type(self):
        return dict


class Storage:
    """
    PostgreSQL persistence layer for workflows, requests, and results.
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/security_agency"
        )
        # Use in-memory SQLite for testing if TESTING env var is set
        if os.getenv("TESTING", "0") == "1":
            self.db_url = "sqlite:///:memory:"

        self.engine: Engine = create_engine(self.db_url, echo=False, future=True)
        self.metadata = MetaData()

        # Use SQLiteJSON if using SQLite
        json_type = SQLiteJSON if self.db_url.startswith("sqlite") else JSON

        # Define tables
        self.workflows = Table(
            "workflows",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("name", String),
            Column("description", String),
            Column("state", String),
            Column("context", json_type),
        )

        self.workflow_steps = Table(
            "workflow_steps",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("workflow_id", String),
            Column("agent", String),
            Column("input", json_type),
            Column("output", json_type),
            Column("status", String),
            Column("dependencies", json_type),
        )

        self.scan_requests = Table(
            "scan_requests",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("target", String),
            Column("requested_agents", json_type),
            Column("priority", String),
            Column("workflow_id", String),
        )

        self.scan_results = Table(
            "scan_results",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("request_id", String),
            Column("agent", String),
            Column("status", String),
            Column("output", json_type),
            Column("analysis", json_type),
            Column("metadata", json_type),
        )

        self.metadata.create_all(self.engine)

    def save_workflow(self, workflow: Workflow) -> None:
        with self.engine.begin() as conn:
            data = {
                c.name: getattr(workflow, c.name)
                for c in self.workflows.columns
                if hasattr(workflow, c.name)
            }
            stmt = insert(self.workflows).values(**data)
            update_data = {k: v for k, v in data.items() if k != "id"}
            stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_data)
            conn.execute(stmt)

    def save_scan_request(self, request: ScanRequest) -> None:
        with self.engine.begin() as conn:
            data = {
                c.name: getattr(request, c.name)
                for c in self.scan_requests.columns
                if hasattr(request, c.name)
            }
            conn.execute(self.scan_requests.insert().values(**data))

    def save_scan_result(self, result: ScanResult) -> None:
        with self.engine.begin() as conn:
            data = {
                c.name: getattr(result, c.name)
                for c in self.scan_results.columns
                if hasattr(result, c.name)
            }
            stmt = insert(self.scan_results).values(**data)
            update_data = {k: v for k, v in data.items() if k != "id"}
            stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_data)
            conn.execute(stmt)

    def update_workflow_state(self, workflow_id: str, state: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                self.workflows.update()
                .where(self.workflows.c.id == workflow_id)
                .values(state=state)
            )

    def list_scan_history(self, limit: int = 50):
        """Return recent scan requests with basic metadata."""
        with self.engine.begin() as conn:
            result = conn.execute(
                self.scan_requests.select().order_by(self.scan_requests.c.id.desc()).limit(limit)
            )
            return [dict(row._mapping) for row in result]

    def get_scan_results(self, request_id: str):
        """Return all results for a given scan request."""
        with self.engine.begin() as conn:
            result = conn.execute(
                self.scan_results.select().where(self.scan_results.c.request_id == request_id)
            )
            return [dict(row._mapping) for row in result]

    def get_scan_report(self, result_id: str):
        """Return a single scan result/report by ID."""
        with self.engine.begin() as conn:
            result = conn.execute(
                self.scan_results.select().where(self.scan_results.c.id == result_id)
            ).first()
            return dict(result._mapping) if result else None
