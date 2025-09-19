from typing import List
from agents.nikto_agent import NiktoAgent
from agents.nmap_agent import NmapAgent
from agents.sqlmap_agent import SqlmapAgent
from core.models import ScanRequest, ScanResult, Workflow, WorkflowStep, OrchestrationEvent
from core.event_queue import EventQueue
from core.decision_engine import DecisionEngine
from core.storage import Storage


class Orchestrator:
    def __init__(self):
        self.agents = {
            "nmap": NmapAgent(),
            "nikto": NiktoAgent(),
            "sqlmap": SqlmapAgent(),
        }
        self.queue = EventQueue()
        self.decision_engine = DecisionEngine()
        self.storage = Storage()

    def run_scan(self, request: ScanRequest) -> List[ScanResult]:
        """
        Instead of directly running agents, enqueue workflow steps and invoke decision engine.
        """
        workflow = Workflow(
            id=request.workflow_id or request.id,
            name=f"Workflow-{request.id}",
            steps=[],
            context={}
        )
        self.storage.save_workflow(workflow)

        # Initial steps
        initial_steps = [
            WorkflowStep(
                id=f"{request.id}-{agent}",
                workflow_id=workflow.id,
                agent=agent,
                input={"target": request.target},
                status="pending",
                dependencies=[]
            )
            for agent in (request.requested_agents or self.agents.keys())
        ]

        for step in initial_steps:
            workflow.steps.append(step)
            self.queue.publish(OrchestrationEvent(
                id=step.id,
                type="scan_started",
                payload={"step": step.__dict__}
            ))

        results: List[ScanResult] = []
        while self.queue.size() > 0:
            event = self.queue.consume()
            if not event:
                continue

            if event.type == "scan_started":
                step_data = event.payload["step"]
                agent_name = step_data["agent"]
                agent = self.agents.get(agent_name)
                if agent:
                    result = agent.run(step_data["input"]["target"])
                    results.append(result)
                    self.storage.save_scan_result(result)

                    self.queue.publish(OrchestrationEvent(
                        id=step_data["id"],
                        type="scan_completed",
                        payload={"result": result.__dict__}
                    ))

            elif event.type == "scan_completed":
                decision = self.decision_engine.decide_next_steps(workflow, results)
                for next_step in decision.next_steps:
                    self.queue.publish(OrchestrationEvent(
                        id=next_step.id,
                        type="scan_started",
                        payload={"step": next_step.__dict__}
                    ))

        return results
