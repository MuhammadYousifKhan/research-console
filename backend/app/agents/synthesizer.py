from app.schemas.research import Observation
from app.services.llm import LLMClient


class ResearchSynthesizer:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def create_answer(
        self,
        query: str,
        observations: list[Observation],
        citation_context: str = "",
    ) -> str:
        evidence = "\n\n".join(
            f"Task {item.task_id}: {item.task}\nResult: {item.result}"
            for item in observations
        )
        return await self.llm.complete_text(
            system=(
                "You are a research synthesis agent. Use only the provided evidence. "
                "Mention uncertainty when evidence is incomplete. Cite factual claims "
                "with source numbers like [1], [2]."
            ),
            user=(
                f"Query: {query}\n\n"
                f"Numbered sources:\n{citation_context}\n\n"
                f"Evidence:\n{evidence}\n\n"
                "Write a concise structured research answer with these sections: "
                "Summary, Key impacts, Risks and limitations, Sources used."
            ),
        )
