import pytest
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.models import Agent, Document, DocumentChunk, Forwarded
from app.repositories.document_chunks import DocumentChunksRepository


@pytest.mark.asyncio
async def test_get_relevant_chunks_filters_by_sender(session: AsyncSession) -> None:
    sender1 = Agent(name="sender1")
    sender2 = Agent(name="sender2")
    recipient = Agent(name="recipient")

    doc1 = Document(name="doc1")
    doc2 = Document(name="doc2")

    session.add_all([sender1, sender2, recipient, doc1, doc2])
    await session.flush()

    chunk1 = DocumentChunk(content="chunk1", embedding=[0.0] * 1024, hash=b"h1", document=doc1)
    chunk2 = DocumentChunk(content="chunk2", embedding=[0.0] * 1024, hash=b"h2", document=doc2)
    session.add_all([chunk1, chunk2])
    await session.flush()

    fwd1 = Forwarded(sender_id=sender1.id, recipient_id=recipient.id, document_id=doc1.id)
    fwd2 = Forwarded(sender_id=sender2.id, recipient_id=recipient.id, document_id=doc2.id)
    session.add_all([fwd1, fwd2])

    await session.commit()

    repo = DocumentChunksRepository(session)
    result = await repo.get_relevant_chunks(embedding=[0.0] * 1024, limit=10, sender_id=sender1.id)
    ids = [chunk.id for chunk, _ in result]
    assert chunk1.id in ids
    assert chunk2.id not in ids


@pytest.mark.asyncio
async def test_get_relevant_chunks_filters_by_valid_and_hidden(session: AsyncSession) -> None:
    sender = Agent(name="sender")
    recipient = Agent(name="recipient")
    doc1 = Document(name="doc1")
    doc2 = Document(name="doc2")

    session.add_all([sender, recipient, doc1, doc2])
    await session.flush()

    chunk1 = DocumentChunk(content="chunk1", embedding=[0.0] * 1024, hash=b"h1", document=doc1)
    chunk2 = DocumentChunk(content="chunk2", embedding=[0.0] * 1024, hash=b"h2", document=doc2)
    session.add_all([chunk1, chunk2])
    await session.flush()

    fwd1 = Forwarded(
        sender_id=sender.id,
        recipient_id=recipient.id,
        document_id=doc1.id,
        is_valid=True,
        is_hidden=False,
    )
    fwd2 = Forwarded(
        sender_id=sender.id,
        recipient_id=recipient.id,
        document_id=doc2.id,
        is_valid=False,
        is_hidden=True,
    )
    session.add_all([fwd1, fwd2])
    await session.commit()

    repo = DocumentChunksRepository(session)

    result_valid = await repo.get_relevant_chunks(embedding=[0.0] * 1024, limit=10, is_valid=True)
    ids_valid = [chunk.id for chunk, _ in result_valid]
    assert chunk1.id in ids_valid
    assert chunk2.id not in ids_valid

    result_hidden = await repo.get_relevant_chunks(embedding=[0.0] * 1024, limit=10, is_hidden=True)
    ids_hidden = [chunk.id for chunk, _ in result_hidden]
    assert chunk2.id in ids_hidden
    assert chunk1.id not in ids_hidden


@pytest.mark.sep_database
@pytest.mark.asyncio
async def test_get_relevant_chunks_exclude_and_limit(session: AsyncSession) -> None:
    doc1 = Document(name="doc1")
    doc2 = Document(name="doc2")
    session.add_all([doc1, doc2])
    await session.flush()

    chunk1 = DocumentChunk(content="chunk1", embedding=[0.0] * 1024, hash=b"h1", document=doc1)
    chunk2 = DocumentChunk(content="chunk2", embedding=[1.0] * 1024, hash=b"h2", document=doc2)
    session.add_all([chunk1, chunk2])
    await session.commit()

    repo = DocumentChunksRepository(session)

    res_limit = await repo.get_relevant_chunks(
        embedding=[0.0] * 1024,
        limit=1,
        distance_metric="l2",
    )
    limit_ids = [c.id for c, _ in res_limit]
    assert len(limit_ids) == 1
    assert chunk1.id in limit_ids
    assert chunk2.id not in limit_ids

    res_exclude = await repo.get_relevant_chunks(
        embedding=[0.0] * 1024,
        limit=10,
        distance_metric="l2",
        exclude_document_ids=[doc1.id],
    )
    exclude_ids = [c.id for c, _ in res_exclude]
    assert chunk2.id in exclude_ids
    assert chunk1.id not in exclude_ids
