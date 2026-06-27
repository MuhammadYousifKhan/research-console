from pydantic import ValidationError

from app.schemas.research import Evaluation, Observation
from app.services.llm import LLMClient, LLMError


class ResearchEvaluator:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    @staticmethod
    def fallback_evaluation(observations: list[Observation]) -> Evaluation:
        return Evaluation.model_validate(
            {
                "is_supported": bool(observations),
                "confidence": "medium" if observations else "low",
                "missing_evidence": [],
                "notes": (
                    "Heuristic fallback: the evaluator LLM call could not run, so support "
                    "is inferred from whether any evidence was gathered (see the failed step "
                    "detail for the underlying cause)."
                ),
            }
        )

    async def evaluate(self, query: str, answer: str, observations: list[Observation]) -> Evaluation:
        evidence = "\n\n".join(item.result for item in observations)
        data = await self.llm.complete_json(
            system=(
                "You are an evidence evaluator. Return strict JSON only. "
                "Check whether the answer is supported by the evidence."
            ),
            user=(
                f"Query: {query}\n\nAnswer:\n{answer}\n\nEvidence:\n{evidence}\n\n"
                "Return JSON with: is_supported boolean, confidence low|medium|high, "
                "missing_evidence array, notes string."
            ),
        )
        try:
            return Evaluation.model_validate(data)
        except ValidationError as error:
            raise LLMError(f"Evaluator returned an invalid structure: {error}") from error
