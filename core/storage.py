import os
from typing import List
from sqlalchemy import create_engine, Table, Column, String, JSON, MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from core.models import Workflow, WorkflowStep, ScanRequest, ScanResult


class Storage:
    """
    PostgreSQL persistence layer for workflows, requests, and results.
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/security_agency")
        self.engine: Engine = create_engine(self.db_url, echo=False, future=True)
        self.metadata = MetaData()

        # Define tables
        self.workflows = Table(
            "workflows", self.metadata,
            Column("id", String, primary_key=True),
            Column("name", String),
            Column("description", String),
            Column("state", String),
            Column("context", JSONB),
        )

        self.workflow_steps = Table(
            "workflow_steps", self.metadata,
            Column("id", String, primary_key=True),
            Column("workflow_id", String),
            Column("agent", String),
            Column("input", JSONB),
            Column("output", JSONB),
            Column("status", String),
            Column("dependencies", JSONB),
        )

        self.scan_requests = Table(
            "scan_requests", self.metadata,
            Column("id", String, primary_key=True),
            Column("target", String),
            Column("requested_agents", JSONB),
            Column("priority", String),
            Column("workflow_id", String),
        )

        self.scan_results = Table(
            "scan_results", self.metadata,
            Column("id", String, primary_key=True),
            Column("request_id", String),
            Column("agent", String),
            Column("status", String),
            Column("output", JSONB),
            Column("analysis", JSONB),
            Column("metadata", JSONB),
        )

        self.metadata.create_all(self.engine)

    def save_workflow(self, workflow: Workflow) -> None:
        with self.engine.begin() as conn:
            data = {c.name: getattr(workflow, c.name) for c in self.workflows.columns if hasattr(workflow, c.name)}
            conn.execute(self.workflows.insert().values(**data))

    def save_scan_request(self, request: ScanRequest) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.scan_requests.insert().values(**request.__dict__))

    def save_scan_result(self, result: ScanResult) -> None:
        with self.engine.begin() as conn:
            conn.execute(self.scan_results.insert().values(**result.__dict__))

    def update_workflow_state(self, workflow_id: str, state: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                self.workflows.update().where(self.workflows.c.id == workflow_id).values(state=state)
            )
