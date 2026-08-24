import io
import pytest
import tempfile
from pathlib import Path
from pypdf import PdfWriter

from app.services.resume_parser import (
    parse_pdf,
    extract_resume_signals,
    extract_seniority,
    _match_term,
)

def create_in_memory_pdf_file(text_lines: list[str] | None = None) -> Path:
    """Helper to create a real temporary PDF file on disk for testing."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    
    # Write to a temporary PDF file
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    writer.write(temp)
    temp.close()
    return Path(temp.name)

def test_parse_pdf_nonexistent_file():
    """Verify parse_pdf raises FileNotFoundError when target path does not exist."""
    with pytest.raises(FileNotFoundError):
        parse_pdf("nonexistent_path_to_resume.pdf")

def test_parse_pdf_invalid_extension():
    """Verify parse_pdf raises ValueError when file extension is not .pdf."""
    temp_txt = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    temp_txt.write(b"Hello World")
    temp_txt.close()
    try:
        with pytest.raises(ValueError):
            parse_pdf(temp_txt.name)
    finally:
        Path(temp_txt.name).unlink(missing_ok=True)

def test_parse_pdf_blank_or_unextractable_pdf():
    """Verify parse_pdf returns empty string without crashing on blank/unextractable PDFs."""
    pdf_path = create_in_memory_pdf_file()
    try:
        result = parse_pdf(pdf_path)
        assert isinstance(result, str)
        assert result == ""
    finally:
        pdf_path.unlink(missing_ok=True)

def test_word_boundary_false_positive_prevention():
    """Verify substring collisions are prevented for short names and terms."""
    # "rag" should not match inside courage, storage, drag
    assert not _match_term("rag", "courage storage encourage drag fragment")
    assert _match_term("rag", "Specialized in RAG systems and RAGs")

    # "go" should not match algorithm, django, google
    assert not _match_term("go", "algorithm and google django")
    assert _match_term("go", "Experienced with Go and Python")

    # "c" should not match cat, react, docker
    assert not _match_term("c", "cat react docker cloud")
    assert _match_term("c", "Proficient in C, C++, and Python")

    # "c++"
    assert _match_term("c++", "Implemented in C++ and Python")
    assert _match_term("c++", "Implemented in CPP")
    assert not _match_term("c++", "topic++")

    # "c#"
    assert _match_term("c#", "Developed services in C#")
    assert _match_term("c#", "Developed services in CSharp")

def test_special_technologies_and_synonyms():
    """Verify special technologies and common synonym variations are extracted."""
    sample_text = (
        "Senior Full Stack Engineer. Built modern web applications using NextJS, Next.js, and React. "
        "Deployed microservices using K8s on AWS with robust CI/CD and GitHub Actions. "
        "Database layer designed using Postgres and MongoDB with Redis caching. "
        "Built ML models using Sklearn, PyTorch, and trained LLMs with LangChain and ChromaDB. "
        "Designed high-performance REST APIs using FastAPI."
    )
    signals = extract_resume_signals(sample_text)

    # Technologies
    assert "next.js" in signals["technologies"]
    assert "kubernetes" in signals["technologies"]
    assert "postgresql" in signals["technologies"]
    assert "mongodb" in signals["technologies"]
    assert "redis" in signals["technologies"]
    assert "scikit-learn" in signals["technologies"]
    assert "pytorch" in signals["technologies"]
    assert "fastapi" in signals["technologies"]
    assert "rest api" in signals["technologies"]
    assert "docker" not in signals["technologies"]  # not mentioned

    # Skills
    assert "llm" in signals["skills"]
    assert "ci/cd" in signals["skills"]
    assert "microservices" in signals["skills"]
    assert "api development" in signals["skills"]
    assert "machine learning" in signals["skills"]

def test_investigate_0_extracted_signals_issue():
    """
    Test previously reported bug where valid resumes with plural or shorthand
    terms (LLMs, REST APIs, Postgres, NextJS, K8s, Sklearn) resulted in 0 extracted signals.
    """
    resume_text = (
        "Alex Rivera - Machine Learning & Backend Engineer\n"
        "Summary: Experience building with LLMs, RAGs, and REST APIs. "
        "Proficient in Postgres, NextJS, K8s, and Sklearn."
    )
    signals = extract_resume_signals(resume_text)

    # Must extract all matching signals despite plurals and shorthands
    assert len(signals["skills"]) >= 3
    assert len(signals["technologies"]) >= 3
    assert "llm" in signals["skills"]
    assert "rag" in signals["skills"]
    assert "postgresql" in signals["technologies"]
    assert "kubernetes" in signals["technologies"]
    assert "next.js" in signals["technologies"]
    assert "scikit-learn" in signals["technologies"]
    assert "rest api" in signals["technologies"]

def test_seniority_and_experience_detection():
    """Verify accurate seniority level classification and years of experience parsing."""
    # Senior with explicit years
    s1, y1 = extract_seniority("Senior AI Researcher with 7+ years of experience in NLP.")
    assert s1 == "Senior"
    assert y1 == 7

    # Senior inferred from high years
    s2, y2 = extract_seniority("Software Engineer with 8 years experience in distributed systems.")
    assert s2 == "Senior"
    assert y2 == 8

    # Staff / Lead
    s3, y3 = extract_seniority("Staff Software Engineer / Tech Lead with 10 yrs of experience.")
    assert s3 == "Staff/Lead"
    assert y3 == 10

    # Junior
    s4, y4 = extract_seniority("Junior developer looking for entry level backend role.")
    assert s4 == "Junior"

    # Junior inferred from low years
    s5, y5 = extract_seniority("Developer with 1 year of experience in Python.")
    assert s5 == "Junior"
    assert y5 == 1

    # Mid-Level default
    s6, y6 = extract_seniority("Software Developer proficient in Python and React.")
    assert s6 == "Mid-Level"
    assert y6 is None

def test_domain_exposure_detection():
    """Verify domain categories are mapped correctly from extracted signals."""
    ai_text = "Trained deep learning and generative ai models using PyTorch and TensorFlow."
    assert "AI/ML" in extract_resume_signals(ai_text)["domain_exposure"]

    backend_text = "Engineered microservices and REST APIs using FastAPI, Django, and PostgreSQL."
    assert "Backend" in extract_resume_signals(backend_text)["domain_exposure"]

    data_text = "Performed data analysis and pipeline engineering with Pandas, SQL, and Tableau."
    assert "Data" in extract_resume_signals(data_text)["domain_exposure"]

    frontend_text = "Frontend engineer developing interactive dashboards with React, Next.js, and TypeScript."
    assert "Frontend" in extract_resume_signals(frontend_text)["domain_exposure"]

    devops_text = "Implemented CI/CD pipelines deploying Docker containers to Kubernetes on AWS."
    assert "Cloud/DevOps" in extract_resume_signals(devops_text)["domain_exposure"]
