from typing import List  # type: ignore
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.chat_models import ChatOpenAI

from core.models import AgentDecision, ScanResult, Workflow, WorkflowStep


class DecisionEngine:  # pylint: disable=too-few-public-methods
    """
    LangChain-based decision engine for orchestrating workflow steps.
    """

    def __init__(self, model_name: str = "gpt-4", temperature: float = 0.2):
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)

        self.prompt = ChatPromptTemplate.from_template(
            """
            You are an orchestration engine for a security scanning system.
            Given the current workflow context and scan results, decide the next steps.

            Workflow Context:
            {workflow_context}

            Scan Results:
            {scan_results}

            Respond with:
            - Next steps (agents to run, with input)
            - Reasoning
            """
        )

    def decide_next_steps(
        self, workflow: Workflow, results: List[ScanResult]
    ) -> AgentDecision:
        scan_results_str = "\n".join(
            [f"{r.agent}: {r.status}, output={r.output}" for r in results]
        )

        chain = self.llm
        response = chain.invoke(
            {"workflow_context": workflow.context, "scan_results": scan_results_str}
        )

        # Attempt to parse structured response
        reasoning = response.content
        next_steps: List[WorkflowStep] = []

        try:
            parsed = json.loads(response.content)
            for step in parsed.get("next_steps", []):
                next_steps.append(
                    WorkflowStep(
                        id=f"{workflow.id}-{step['agent']}-{len(next_steps)}",
                        workflow_id=workflow.id,
                        agent=step["agent"],
                        input=step.get("input", {}),
                        status="pending",
                        dependencies=step.get("dependencies", []),
                    )
                )
            reasoning = parsed.get("reasoning", reasoning)
        except Exception:  # pylint: disable=broad-exception-caught
            # fallback to raw text reasoning
            pass

        return AgentDecision(
            workflow_id=workflow.id, next_steps=next_steps, reasoning=reasoning
        )
