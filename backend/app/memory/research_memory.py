from app.schemas.research import Observation, Source


class ResearchMemory:
    def __init__(self) -> None:
        self.observations: list[Observation] = []
        self.sources: list[Source] = []

    def add_observation(self, observation: Observation) -> None:
        self.observations.append(observation)
        for source in observation.sources:
            if not any(existing.url == source.url for existing in self.sources):
                self.sources.append(source)
