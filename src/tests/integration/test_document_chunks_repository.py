import pytest
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.models import Agent, Document, DocumentChunk, Forwarded
from app.repositories.document_chunks import DocumentChunksRepository


@pytest.mark.asyncio
async def test_get_relevant_chunks_filters_by_sender(session: AsyncSession):
    sender1 = Agent(name="sender1")
    sender2 = Agent(name="sender2")
    recipient = Agent(name="recipient")

    doc1 = Document(name="doc1")
    doc2 = Document(name="doc2")

    session.add_all([sender1, sender2, recipient, doc1, doc2])
    await session.flush()

    chunk1 = DocumentChunk(content="chunk1", embedding=[0.0]*1024, hash=b"h1", document=doc1)
    chunk2 = DocumentChunk(content="chunk2", embedding=[0.0]*1024, hash=b"h2", document=doc2)
    session.add_all([chunk1, chunk2])
    await session.flush()

    fwd1 = Forwarded(sender_id=sender1.id, recipient_id=recipient.id, document_id=doc1.id)
    fwd2 = Forwarded(sender_id=sender2.id, recipient_id=recipient.id, document_id=doc2.id)
    session.add_all([fwd1, fwd2])

    await session.commit()

    repo = DocumentChunksRepository(session)
    result = await repo.get_relevant_chunks(embedding=[0.0]*1024, limit=10, sender_id=sender1.id)
    ids = [chunk.id for chunk, _ in result]
    assert ids == [chunk1.id]
