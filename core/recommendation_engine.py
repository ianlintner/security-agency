import logging
from typing import Any, Dict, List

from core.decision_engine import DecisionEngine


class RecommendationEngine:  # pylint: disable=too-few-public-methods
    """
    AI-powered recommendation engine that consumes scan results
    and generates prioritized remediation steps using GPT-4 via LangChain.
    """

    def __init__(self, decision_engine: DecisionEngine):
        self.decision_engine = decision_engine
        self.logger = logging.getLogger(__name__)

    async def generate_recommendations(
        self, scan_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate prioritized remediation recommendations from scan results.
        """
        try:
            # Prepare structured input for GPT
            input_payload = {
                "task": "Generate prioritized security remediation recommendations",
                "scan_results": scan_results,
            }

            # Use decision engine (LangChain + GPT-4) to process
            response = await self.decision_engine.process(input_payload)

            # Expect structured JSON-like response
            return {
                "status": "success",
                "recommendations": response.get("recommendations", []),
                "prioritized_vulnerabilities": response.get(
                    "prioritized_vulnerabilities", []
                ),
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Recommendation generation failed: %s", e)
            return {"status": "error", "message": str(e)}
