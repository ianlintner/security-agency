from typing import List
from langchain_openai.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from core.models import Workflow, ScanResult, AgentDecision, WorkflowStep


class DecisionEngine:
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

    def decide_next_steps(self, workflow: Workflow, results: List[ScanResult]) -> AgentDecision:
        scan_results_str = "\n".join([f"{r.agent}: {r.status}, output={r.output}" for r in results])

        chain = self.prompt | self.llm
        response = chain.invoke({
            "workflow_context": workflow.context,
            "scan_results": scan_results_str
        })

        # For now, assume response is structured JSON-like text
        # In production, add parsing/validation
        reasoning = response.content
        next_steps: List[WorkflowStep] = []  # Placeholder, would parse from response

        return AgentDecision(
            workflow_id=workflow.id,
            next_steps=next_steps,
            reasoning=reasoning
        )
