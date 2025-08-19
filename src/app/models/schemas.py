from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SimilarDocumentSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: UUID
    document_similar_score: float | None = Field(default=None)

    def __hash__(self) -> int:
        return hash(self.document_id)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SimilarDocumentSource):
            return NotImplemented
        return self.document_id == other.document_id


class PotentialRecipient(BaseModel):
    agent_id: UUID
    similar_docs: set[SimilarDocumentSource] = Field(default_factory=set)
    is_eligible: bool = Field(default=False)
