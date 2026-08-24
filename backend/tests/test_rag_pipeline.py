import pytest
import shutil
import tempfile
from pathlib import Path

from app.services.rag_service import (
    RAGService,
    sanitize_role_name,
    create_sliding_window_chunks,
)

@pytest.fixture
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB to isolate test collections."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def rag_service(temp_chroma_dir):
    """Instantiate RAGService pointing to isolated temporary directory."""
    return RAGService(chroma_path=temp_chroma_dir)

def test_sanitize_role_name():
    """Verify role name normalization into valid Chroma collection names."""
    assert sanitize_role_name("AI/ML Engineer") == "kb_ai_ml_engineer"
    assert sanitize_role_name("Backend Engineer") == "kb_backend_engineer"
    assert sanitize_role_name("Data Scientist") == "kb_data_scientist"
    assert sanitize_role_name("global") == "kb_global"
    assert sanitize_role_name("kb_global") == "kb_global"
    assert sanitize_role_name("") == "kb_global"
    assert sanitize_role_name("all") == "kb_global"

def test_create_sliding_window_chunks():
    """Verify sliding-window chunk generation, overlap, and metadata."""
    # Create 25 words of text
    words = [f"word{i}" for i in range(25)]
    text = " ".join(words)

    chunks = create_sliding_window_chunks(
        text=text,
        source="system_design.pdf",
        role="Backend Engineer",
        page=3,
        chunk_size=10,
        chunk_overlap=3
    )

    # With 25 words, size 10, overlap 3 -> step = 7:
    # chunk 0: 0..10
    # chunk 1: 7..17
    # chunk 2: 14..24
    # chunk 3: 21..25
    assert len(chunks) == 4
    assert chunks[0]["page"] == 3
    assert chunks[0]["source"] == "system_design.pdf"
    assert chunks[0]["role"] == "Backend Engineer"
    assert "system_design" in chunks[0]["id"]
    assert chunks[0]["word_count"] == 10

    # Check that overlap exists between chunk 0 and chunk 1
    c0_words = chunks[0]["text"].split()
    c1_words = chunks[1]["text"].split()
    assert c0_words[-3:] == c1_words[:3]

def test_rag_ingest_and_retrieve(rag_service):
    """Verify ingesting and retrieving chunks with semantic scoring and citations."""
    sample_text_ml = (
        "Transformers rely on the self-attention mechanism to compute representations of sequences "
        "without using recurrent alignment. Multi-head attention allows the model to jointly attend "
        "to information from different representation subspaces at different positions."
    )
    sample_text_db = (
        "Relational databases use B-Trees and Write-Ahead Logging (WAL) for ACID transactions. "
        "Database indexing speeds up search queries by maintaining auxiliary data structures."
    )

    chunks_ml = create_sliding_window_chunks(sample_text_ml, source="deep_learning.pdf", role="AI/ML Engineer", page=42)
    chunks_db = create_sliding_window_chunks(sample_text_db, source="database_internals.pdf", role="Backend Engineer", page=15)

    rag_service.ingest("AI/ML Engineer", chunks_ml, also_to_global=True)
    rag_service.ingest("Backend Engineer", chunks_db, also_to_global=True)

    # Retrieve for AI/ML Engineer
    results_ml = rag_service.retrieve(
        role="AI/ML Engineer",
        query="How does multi-head self attention work in transformer architectures?",
        top_k=2
    )

    assert len(results_ml) > 0
    top_hit = results_ml[0]
    assert "self-attention" in top_hit["text"]
    assert top_hit["source"] == "deep_learning.pdf"
    assert top_hit["page"] == 42
    assert "citation" in top_hit
    assert "deep_learning.pdf" in top_hit["citation"]
    assert top_hit["score"] > 0.0

def test_rag_fallback_to_global(rag_service):
    """Verify fallback to global collection when a role collection is empty."""
    # Ingest document only into global collection
    chunks = create_sliding_window_chunks(
        "Distributed systems consensus algorithms like Paxos and Raft ensure state machine replication.",
        source="distributed_systems.pdf",
        role="global",
        page=7
    )
    rag_service.ingest("global", chunks, also_to_global=False)

    # Query for a role that has 0 documents in its specific collection
    results = rag_service.retrieve(
        role="Cloud Architect",
        query="What is the Raft consensus algorithm?",
        top_k=1
    )

    assert len(results) == 1
    assert "Paxos and Raft" in results[0]["text"]
    assert results[0]["source"] == "distributed_systems.pdf"

def test_rag_empty_collection_returns_empty(rag_service):
    """Verify querying an empty collection returns [] cleanly without exceptions."""
    results = rag_service.retrieve(role="UnpopulatedRole", query="Any query")
    assert results == []

def test_rag_metadata_filter(rag_service):
    """Verify metadata filtering on retrieval."""
    chunk_p1 = create_sliding_window_chunks("Microservices architecture with REST APIs", source="arch.pdf", page=1)
    chunk_p2 = create_sliding_window_chunks("Monolithic architecture and database scaling", source="arch.pdf", page=2)

    rag_service.ingest("Backend Engineer", chunk_p1 + chunk_p2)

    # Filter specifically for page 2
    results = rag_service.retrieve(
        role="Backend Engineer",
        query="architecture",
        metadata_filter={"page": 2}
    )

    assert len(results) == 1
    assert results[0]["page"] == 2
    assert "Monolithic" in results[0]["text"]

def test_rag_score_threshold_filter(rag_service):
    """Verify score threshold filters out low-relevance results."""
    chunks = create_sliding_window_chunks(
        "Kubernetes container orchestration and pod management.",
        source="k8s.pdf",
        role="DevOps"
    )
    rag_service.ingest("DevOps", chunks)

    # High threshold should filter out unrelated query
    filtered = rag_service.retrieve(
        role="DevOps",
        query="Cooking recipes for Italian pasta carbonara",
        score_threshold=0.85
    )
    assert len(filtered) == 0
