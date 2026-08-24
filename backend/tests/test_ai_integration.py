import pytest
from unittest.mock import patch, AsyncMock
from app.services.resume_parser import extract_resume_signals, extract_seniority, _match_term
from app.services.question_generator import (
    make_prompt,
    generate_fallback_question,
    generate_question,
)
from app.services.evaluator import (
    calculate_overall_score,
    determine_hiring_recommendation,
    evaluate_answer_fallback,
    evaluate_answer,
    generate_final_summary,
)

def test_resume_parser_word_boundary_and_seniority():
    """Verify word-boundary matching and seniority detection."""
    # "rag" in "courage" or "storage" should NOT match
    assert not _match_term("rag", "storage courage encourage")
    assert _match_term("rag", "experience in rag pipelines")
    assert _match_term("c++", "proficient in c++ and python")
    assert not _match_term("c++", "topic++")

    # Seniority extraction
    senior_text = "Senior Machine Learning Engineer with 6+ years experience in deep learning."
    signals = extract_resume_signals(senior_text)
    assert signals["seniority_level"] == "Senior"
    assert signals["years_of_experience"] == 6
    assert "machine learning" in signals["skills"]
    assert "deep learning" in signals["skills"]
    assert "AI/ML" in signals["domain_exposure"]

    junior_text = "Junior developer intern looking for entry level backend role in Python."
    junior_signals = extract_resume_signals(junior_text)
    assert junior_signals["seniority_level"] == "Junior"
    assert "python" in junior_signals["technologies"]
    assert "Backend" in junior_signals["domain_exposure"]

def test_adaptive_prompt_generation():
    """Verify adaptive prompt contains role, seniority, retrieved context, and previous turns."""
    signals = {
        "seniority_level": "Senior",
        "skills": ["machine learning", "rag"],
        "technologies": ["python", "chromadb"]
    }
    retrieved = [
        {
            "text": "Vector databases use HNSW graphs to perform approximate nearest neighbor search.",
            "source": "vector_search.pdf",
            "citation": "[vector_search.pdf (p. 10)]"
        }
    ]
    previous = [
        {
            "question": "What is cosine similarity?",
            "answer": "Cosine similarity measures the angle between two embedding vectors regardless of magnitude."
        }
    ]

    prompt = make_prompt("AI/ML Engineer", signals, retrieved, previous)
    assert "AI/ML Engineer" in prompt
    assert "Senior" in prompt
    assert "[vector_search.pdf (p. 10)]" in prompt
    assert "HNSW graphs" in prompt
    assert "Turn 1 Question: What is cosine similarity?" in prompt
    assert "GROUNDING RULE" in prompt
    assert "ADAPTIVITY RULE" in prompt

def test_fallback_question_generation_grounded():
    """Verify deterministic fallback question is grounded in context and adapts to turn."""
    signals = {"seniority_level": "Senior", "skills": ["system design"]}
    retrieved = [
        {
            "text": "Write-Ahead Logging (WAL) guarantees atomicity and durability in ACID transactions.",
            "source": "db_internals.pdf"
        }
    ]

    # Turn 1
    q1 = generate_fallback_question("Backend Engineer", signals, retrieved, previous=[])
    assert "db_internals.pdf" in q1
    assert "Write-Ahead Logging" in q1

    # Turn 2
    q2 = generate_fallback_question("Backend Engineer", signals, retrieved, previous=[{"question": q1, "answer": "done"}])
    assert "performance bottlenecks" in q2 or "scaling limitations" in q2

import asyncio

def test_generate_question_deterministic_without_api_key():
    """Verify generate_question produces valid grounded question when no API key is set."""
    signals = {"seniority_level": "Mid-Level", "skills": ["python", "fastapi"]}
    retrieved = [{"text": "FastAPI uses dependency injection for modular request handling.", "source": "fastapi_guide.pdf"}]

    question = asyncio.run(generate_question("Backend Engineer", signals, retrieved, previous=[]))
    assert isinstance(question, str)
    assert len(question) > 20
    assert "FastAPI" in question or "Backend Engineer" in question


def test_score_calculation_and_recommendation():
    """Verify score calculation and hiring recommendation boundaries."""
    assert calculate_overall_score(10.0, 10.0, 10.0, 10.0) == 10.0
    assert calculate_overall_score(1.0, 1.0, 1.0, 1.0) == 1.0

    assert determine_hiring_recommendation(9.0) == "Strong Hire"
    assert determine_hiring_recommendation(7.5) == "Hire"
    assert determine_hiring_recommendation(6.0) == "Lean Hire"
    assert determine_hiring_recommendation(4.0) == "No Hire"

def test_evaluate_answer_fallback_rubric():
    """Verify answer evaluation returns complete rubric criteria, strengths, weaknesses, and ideal answer."""
    question = "How does database indexing improve query performance?"
    context = "B-Tree indexes allow logarithm search time O(log N) instead of full table scans O(N). Indexes require additional memory and maintenance overhead on write operations."
    answer = (
        "Indexes speed up search queries using B-Trees to avoid full table scans, reducing latency from O(N) to O(log N). "
        "However, there is a trade-off because write operations incur performance overhead to update the index."
    )

    evaluation = evaluate_answer_fallback(
        role="Backend Engineer",
        question=question,
        answer=answer,
        retrieved_context=context,
        seniority="Mid-Level"
    )

    assert "accuracy_score" in evaluation
    assert "completeness_score" in evaluation
    assert "depth_score" in evaluation
    assert "clarity_score" in evaluation
    assert "overall_score" in evaluation
    assert "feedback" in evaluation
    assert "strengths" in evaluation
    assert "weaknesses" in evaluation
    assert "ideal_answer" in evaluation

    assert 1.0 <= evaluation["overall_score"] <= 10.0
    assert len(evaluation["strengths"]) > 0
    assert len(evaluation["weaknesses"]) > 0
    assert len(evaluation["ideal_answer"]) > 20

def test_evaluate_empty_answer():
    """Verify empty answer returns low score and appropriate weakness."""
    evaluation = evaluate_answer_fallback(
        role="AI/ML Engineer",
        question="What is backpropagation?",
        answer="",
        retrieved_context="Backpropagation computes gradients using the chain rule.",
        seniority="Junior"
    )
    assert evaluation["overall_score"] == 1.0
    assert "No answer was provided" in evaluation["feedback"]

def test_generate_final_summary():
    """Verify interview final summary computes averages, recommendation, and competency breakdown."""
    turns = [
        {
            "turn_number": 1,
            "topic": "Transformers",
            "question": "Explain self-attention.",
            "answer": "Self-attention computes dynamic weights between token embeddings.",
            "accuracy_score": 8.5,
            "completeness_score": 8.0,
            "depth_score": 8.0,
            "clarity_score": 9.0,
            "score": 8.3,
            "strengths": ["Clear mathematical concept."],
            "weaknesses": ["Could mention multi-head scaling."],
        },
        {
            "turn_number": 2,
            "topic": "Vector DB",
            "question": "How does HNSW indexing work?",
            "answer": "HNSW creates hierarchical graphs for logarithmic nearest neighbor retrieval with low latency.",
            "accuracy_score": 9.0,
            "completeness_score": 8.5,
            "depth_score": 8.5,
            "clarity_score": 9.0,
            "score": 8.8,
            "strengths": ["Understands hierarchical graph traversal."],
            "weaknesses": ["Consider memory footprint."],
        }
    ]

    summary = generate_final_summary(
        role="AI/ML Engineer",
        candidate_name="Alice Smith",
        turns=turns
    )

    assert summary["candidate_name"] == "Alice Smith"
    assert summary["role"] == "AI/ML Engineer"
    assert summary["total_questions"] == 2
    assert summary["answered_questions"] == 2
    assert summary["overall_score"] >= 8.0
    assert summary["recommendation"] in ["Strong Hire", "Hire"]
    assert "accuracy" in summary["competency_breakdown"]
    assert len(summary["strengths"]) > 0
    assert len(summary["areas_for_improvement"]) > 0
    assert "Alice Smith" in summary["summary"]
