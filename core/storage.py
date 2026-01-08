import json
import os

# Removed unused import List

from sqlalchemy import JSON, Column, MetaData, String, Table, create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.types import TEXT, TypeDecorator

from core.models import K8sJobRecord, ScanRequest, ScanResult, Workflow


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

        self._dialect_name = self.engine.dialect.name

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

        self.k8s_jobs = Table(
            "k8s_jobs",
            self.metadata,
            Column("id", String, primary_key=True),
            Column("request_id", String),
            Column("agent", String),
            Column("target", String),
            Column("k8s_job_name", String, unique=True),
            Column("namespace", String),
            Column("status", String),
            Column("created_at", String),
            Column("started_at", String),
            Column("completed_at", String),
            Column("error_message", String),
            Column("metadata", json_type),
        )

        self.metadata.create_all(self.engine)

    def _upsert(self, table: Table, data: dict, id_column: str = "id"):
        """Cross-database upsert helper.

        - PostgreSQL: ON CONFLICT DO UPDATE
        - Others (e.g. SQLite in tests): best-effort insert then update
        """
        with self.engine.begin() as conn:
            if self._dialect_name == "postgresql":
                stmt = insert(table).values(**data)
                update_data = {k: v for k, v in data.items() if k != id_column}
                stmt = stmt.on_conflict_do_update(
                    index_elements=[id_column],
                    set_=update_data,
                )
                conn.execute(stmt)
                return

            # Fallback: insert; if fails, update.
            try:
                conn.execute(table.insert().values(**data))
            except Exception:  # pylint: disable=broad-exception-caught
                update_data = {k: v for k, v in data.items() if k != id_column}
                conn.execute(
                    table.update().where(getattr(table.c, id_column) == data[id_column]).values(**update_data)
                )

    def save_workflow(self, workflow: Workflow) -> None:
        data = {
            c.name: getattr(workflow, c.name)
            for c in self.workflows.columns
            if hasattr(workflow, c.name)
        }
        self._upsert(self.workflows, data, id_column="id")

    def save_scan_request(self, request: ScanRequest) -> None:
        with self.engine.begin() as conn:
            data = {
                c.name: getattr(request, c.name)
                for c in self.scan_requests.columns
                if hasattr(request, c.name)
            }
            conn.execute(self.scan_requests.insert().values(**data))

    def save_scan_result(self, result: ScanResult) -> None:
        data = {
            c.name: getattr(result, c.name)
            for c in self.scan_results.columns
            if hasattr(result, c.name)
        }
        self._upsert(self.scan_results, data, id_column="id")

    def save_k8s_job(self, job: K8sJobRecord) -> None:
        data = {
            c.name: getattr(job, c.name)
            for c in self.k8s_jobs.columns
            if hasattr(job, c.name)
        }
        self._upsert(self.k8s_jobs, data, id_column="id")

    def update_k8s_job_status(
        self,
        job_id: str,
        status: str,
        *,
        started_at: str = None,
        completed_at: str = None,
        error_message: str = None,
        metadata: dict = None,
    ) -> None:
        values = {"status": status}
        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        if error_message is not None:
            values["error_message"] = error_message
        if metadata is not None:
            values["metadata"] = metadata

        with self.engine.begin() as conn:
            conn.execute(
                self.k8s_jobs.update().where(self.k8s_jobs.c.id == job_id).values(**values)
            )

    def get_k8s_job(self, job_id: str):
        with self.engine.begin() as conn:
            result = conn.execute(self.k8s_jobs.select().where(self.k8s_jobs.c.id == job_id)).first()
            return dict(result._mapping) if result else None  # pylint: disable=protected-access

    def list_k8s_jobs(self, *, status: str = None, request_id: str = None, limit: int = 50):
        with self.engine.begin() as conn:
            stmt = self.k8s_jobs.select().order_by(self.k8s_jobs.c.created_at.desc()).limit(limit)
            if status:
                stmt = stmt.where(self.k8s_jobs.c.status == status)
            if request_id:
                stmt = stmt.where(self.k8s_jobs.c.request_id == request_id)
            result = conn.execute(stmt)
            return [dict(row._mapping) for row in result]  # pylint: disable=protected-access

    def list_active_k8s_jobs(self, limit: int = 200):
        with self.engine.begin() as conn:
            stmt = (
                self.k8s_jobs.select()
                .where(self.k8s_jobs.c.status.in_(["pending", "running"]))
                .order_by(self.k8s_jobs.c.created_at.desc())
                .limit(limit)
            )
            result = conn.execute(stmt)
            return [dict(row._mapping) for row in result]  # pylint: disable=protected-access

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
            return [dict(row._mapping) for row in result]  # pylint: disable=protected-access

    def get_scan_results(self, request_id: str):
        """Return all results for a given scan request."""
        with self.engine.begin() as conn:
            result = conn.execute(
                self.scan_results.select().where(self.scan_results.c.request_id == request_id)
            )
            return [dict(row._mapping) for row in result]  # pylint: disable=protected-access

    def get_scan_report(self, result_id: str):
        """Return a single scan result/report by ID."""
        with self.engine.begin() as conn:
            result = conn.execute(
                self.scan_results.select().where(self.scan_results.c.id == result_id)
            ).first()
            return dict(result._mapping) if result else None  # pylint: disable=protected-access
