import io
import logging
import re
from pathlib import Path
from typing import BinaryIO, Optional, Union
from pypdf import PdfReader

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger("rag_interviewer.parser")

# ============================================================
# PDF PARSING
# ============================================================

def parse_pdf(pdf_input: Union[str, Path, BinaryIO, io.BytesIO]) -> str:
    """
    Extract text from a PDF path or file-like object using pypdf, falling back to PyMuPDF if available.

    Args:
        pdf_input: Path to the PDF file or a file-like/BytesIO stream.

    Returns:
        Extracted text as a string (empty string if blank or unextractable).

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If the file is not a valid PDF file.
    """
    if isinstance(pdf_input, (str, Path)):
        path = Path(pdf_input)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_input}")
        if not path.is_file():
            raise ValueError(f"PDF path is not a file: {pdf_input}")
        if path.suffix.lower() != ".pdf":
            raise ValueError("Only PDF files are supported.")
        target = str(path)
        name = path.name
    else:
        # File-like object / BytesIO / Streamlit UploadedFile
        if hasattr(pdf_input, "name") and pdf_input.name:
            if not str(pdf_input.name).lower().endswith(".pdf"):
                raise ValueError("Only PDF files are supported.")
            name = str(pdf_input.name)
        else:
            name = "uploaded.pdf"
        target = pdf_input

    extracted_text = ""

    # Method 1: pypdf
    try:
        reader = PdfReader(target)
        pages = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text)
            except Exception:
                continue
        extracted_text = "\n".join(pages).strip()
        if extracted_text:
            return extracted_text
    except Exception as exc:
        logger.debug(f"pypdf extraction notice for {name}: {exc}")

    # Method 2: PyMuPDF fallback
    if fitz is not None:
        try:
            if isinstance(target, str):
                document = fitz.open(target)
            elif hasattr(target, "read"):
                if hasattr(target, "seek"):
                    target.seek(0)
                stream_bytes = target.read()
                document = fitz.open(stream=stream_bytes, filetype="pdf")
            else:
                document = None

            if document:
                pages = []
                for page in document:
                    text = page.get_text("text") or ""
                    if text.strip():
                        pages.append(text)
                document.close()
                extracted_text = "\n".join(pages).strip()
                if extracted_text:
                    return extracted_text
        except Exception as exc:
            logger.debug(f"PyMuPDF extraction notice for {name}: {exc}")

    return extracted_text


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_text(text: str) -> str:
    """
    Normalize text for matching while preserving normal word
    boundaries and programming-language symbols.
    """
    text = text.lower()

    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# WORD-BOUNDARY MATCHING & SYNONYMS
# ============================================================

TERM_SYNONYMS = {
    "c#": (
        "c#",
        "csharp",
        "c sharp",
    ),
    "c++": (
        "c++",
        "cpp",
        "c plus plus",
    ),
    "llm": (
        "llm",
        "llms",
        "large language model",
        "large language models",
    ),
    "rag": (
        "rag",
        "rags",
        "retrieval augmented generation",
        "retrieval-augmented generation",
    ),
    "next.js": (
        "next.js",
        "nextjs",
        "next js",
        "next-js",
    ),
    "kubernetes": (
        "kubernetes",
        "k8s",
    ),
    "postgresql": (
        "postgresql",
        "postgres",
        "psql",
    ),
    "mongodb": (
        "mongodb",
        "mongo",
    ),
    "scikit-learn": (
        "scikit-learn",
        "scikit learn",
        "scikitlearn",
        "sklearn",
    ),
    "pytorch": (
        "pytorch",
        "torch",
    ),
    "fastapi": (
        "fastapi",
        "fast api",
        "fastapis",
    ),
    "rest api": (
        "rest api",
        "rest apis",
        "restful api",
        "restful apis",
        "restful",
        "rest-api",
        "rest-apis",
    ),
    "ci/cd": (
        "ci/cd",
        "ci cd",
        "cicd",
        "continuous integration",
        "continuous deployment",
    ),
    "microservices": (
        "microservices",
        "microservice",
        "micro-services",
        "micro-service",
    ),
    "api development": (
        "api development",
        "api design",
        "rest api",
        "rest apis",
        "restful api",
        "restful apis",
        "restful",
    ),
    "machine learning": (
        "machine learning",
        "machine-learning",
        "ml",
    ),
    "deep learning": (
        "deep learning",
        "deep-learning",
        "dl",
    ),
    "generative ai": (
        "generative ai",
        "genai",
        "gen ai",
    ),
    "nlp": (
        "nlp",
        "natural language processing",
    ),
}


def _build_term_pattern(term: str) -> re.Pattern:
    """
    Build a regex pattern that handles special programming
    language symbols while avoiding substring false positives.
    """
    normalized_term = _normalize_text(term)

    # C#
    if normalized_term == "c#":
        return re.compile(
            r"(?<![a-z0-9])c\s*#(?![a-z0-9])"
            r"|(?<![a-z0-9])csharp(?![a-z0-9])"
            r"|(?<![a-z0-9])c\s+sharp(?![a-z0-9])",
            re.IGNORECASE,
        )

    # C++
    if normalized_term == "c++":
        return re.compile(
            r"(?<![a-z0-9])c\s*\+\s*\+(?![a-z0-9+])"
            r"|(?<![a-z0-9])cpp(?![a-z0-9])"
            r"|(?<![a-z0-9])c\s+plus\s+plus(?![a-z0-9])",
            re.IGNORECASE,
        )

    # Short programming language names (strict whole-word boundary)
    if normalized_term in {"go", "c", "r"}:
        return re.compile(
            rf"\b{re.escape(normalized_term)}\b",
            re.IGNORECASE,
        )

    escaped = re.escape(normalized_term)

    return re.compile(
        rf"(?<![a-z0-9]){escaped}(?![a-z0-9])",
        re.IGNORECASE,
    )


def _match_term(term: str, text: str) -> bool:
    """
    Return True when a term or one of its supported synonyms
    appears as a complete term in text.
    """
    if not term or not text:
        return False

    normalized_text = _normalize_text(text)
    normalized_term = _normalize_text(term)

    synonyms = TERM_SYNONYMS.get(
        normalized_term,
        (normalized_term,),
    )

    for synonym in synonyms:
        pattern = _build_term_pattern(synonym)
        if pattern.search(normalized_text):
            return True

    return False


# ============================================================
# CANONICAL TECHNOLOGY LIST
# ============================================================

TECHNOLOGY_TERMS = {
    "python": "python",
    "java": "java",
    "javascript": "javascript",
    "typescript": "typescript",
    "c#": "c#",
    "c++": "c++",
    "cpp": "c++",
    "csharp": "c#",
    "go": "go",
    "rust": "rust",
    "sql": "sql",
    "nosql": "nosql",
    "html": "html",
    "css": "css",

    "pytorch": "pytorch",
    "tensorflow": "tensorflow",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "pandas": "pandas",
    "numpy": "numpy",
    "keras": "keras",

    "fastapi": "fastapi",
    "flask": "flask",
    "django": "django",

    "react": "react",
    "next.js": "next.js",
    "nextjs": "next.js",
    "vue": "vue",
    "node.js": "node.js",
    "nodejs": "node.js",

    "langchain": "langchain",
    "chromadb": "chromadb",
    "faiss": "faiss",
    "pinecone": "pinecone",
    "qdrant": "qdrant",

    "aws": "aws",
    "azure": "azure",
    "gcp": "gcp",

    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "git": "git",
    "github": "git",

    "power bi": "power bi",
    "tableau": "tableau",

    "mongodb": "mongodb",
    "mongo": "mongodb",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "psql": "postgresql",
    "redis": "redis",
    "kafka": "kafka",
    "graphql": "graphql",

    "rest api": "rest api",
    "rest apis": "rest api",
}


# ============================================================
# CANONICAL SKILL LIST
# ============================================================

SKILL_TERMS = {
    "machine learning": (
        "machine learning",
        "machine-learning",
        "ml",
    ),

    "deep learning": (
        "deep learning",
        "deep-learning",
        "dl",
    ),

    "nlp": (
        "nlp",
        "natural language processing",
    ),

    "llm": (
        "llm",
        "llms",
        "large language model",
        "large language models",
    ),

    "rag": (
        "rag",
        "rags",
        "retrieval augmented generation",
        "retrieval-augmented generation",
    ),

    "prompt engineering": (
        "prompt engineering",
    ),

    "computer vision": (
        "computer vision",
        "computer-vision",
    ),

    "statistics": (
        "statistics",
        "statistical analysis",
    ),

    "data visualization": (
        "data visualization",
    ),

    "data engineering": (
        "data engineering",
    ),

    "reinforcement learning": (
        "reinforcement learning",
    ),

    "distributed systems": (
        "distributed systems",
        "distributed system",
        "system design",
    ),

    "system design": (
        "system design",
    ),

    "microservices": (
        "microservices",
        "microservice",
        "micro-services",
    ),

    "ci/cd": (
        "ci/cd",
        "ci cd",
        "cicd",
        "continuous integration",
        "continuous deployment",
    ),

    "api development": (
        "api development",
        "api design",
        "rest api",
        "rest apis",
        "restful api",
        "restful apis",
        "restful",
    ),

    "backend": (
        "backend",
        "back-end",
    ),

    "frontend": (
        "frontend",
        "front-end",
    ),

    "data analysis": (
        "data analysis",
        "data analytics",
    ),

    "generative ai": (
        "generative ai",
        "genai",
        "gen ai",
    ),
}


# ============================================================
# DOMAIN DEFINITIONS
# ============================================================

DOMAIN_TERMS = {
    "AI/ML": (
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "generative ai",
        "nlp",
        "llm",
        "tensorflow",
        "pytorch",
        "ai/ml",
        "ai ml",
    ),

    "Backend": (
        "backend",
        "back-end",
        "fastapi",
        "django",
        "flask",
        "api development",
        "rest api",
        "microservices",
        "postgresql",
        "redis",
    ),

    "Cloud/DevOps": (
        "cloud",
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "devops",
        "ci/cd",
    ),

    "Data": (
        "data science",
        "data analysis",
        "data analytics",
        "data engineering",
        "pandas",
        "numpy",
        "sql",
        "power bi",
        "tableau",
        "statistics",
    ),

    "Frontend": (
        "frontend",
        "front-end",
        "react",
        "next.js",
        "nextjs",
        "vue",
        "javascript",
        "typescript",
    ),
}


# ============================================================
# EXPERIENCE / SENIORITY
# ============================================================

def _extract_years_of_experience(text: str) -> Optional[int]:
    """
    Extract an explicit years-of-experience integer when present.
    """
    normalized = _normalize_text(text)

    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?experience",
        r"(\d+(?:\.\d+)?)\s*\+?\s*yrs?\s+(?:of\s+)?experience",
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+experience",
        r"(\d+(?:\.\d+)?)\s*\+?\s*yrs?\s+experience",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*years?",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*\+?\s*yrs?",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                return int(val)
            except ValueError:
                pass

    return None


def extract_seniority(text: str) -> tuple[str, Optional[int]]:
    """
    Detect candidate seniority level and estimated years of experience.
    Returns:
        (seniority_level, years_of_experience)
    """
    if not isinstance(text, str):
        raise TypeError("Resume text must be a string.")

    normalized = _normalize_text(text)
    years = _extract_years_of_experience(normalized)

    # 1. Staff / Lead (highest priority keyword)
    if re.search(
        r"\b(?:staff|principal|lead engineer|tech lead|technical lead|engineering manager|architect)\b",
        normalized,
        re.IGNORECASE,
    ):
        return "Staff/Lead", years

    # 2. Senior keyword
    if re.search(
        r"\b(?:senior|sr\.?)\b",
        normalized,
        re.IGNORECASE,
    ):
        return "Senior", years

    # 3. Junior keyword
    if re.search(
        r"\b(?:junior|jr\.?|intern|internship|entry[- ]level|entry level|graduate|associate|trainee)\b",
        normalized,
        re.IGNORECASE,
    ):
        return "Junior", years

    # 4. Mid-Level keyword
    if re.search(
        r"\b(?:mid[- ]level|midlevel|intermediate)\b",
        normalized,
        re.IGNORECASE,
    ):
        return "Mid-Level", years

    # 5. Infer from explicit years of experience
    if years is not None:
        if years >= 5:
            return "Senior", years
        if years <= 2:
            return "Junior", years
        return "Mid-Level", years

    return "Mid-Level", None


def _detect_seniority(text: str) -> str:
    """Internal helper returning only seniority level string."""
    level, _ = extract_seniority(text)
    return level


# ============================================================
# SIGNAL EXTRACTION HELPERS
# ============================================================

def _extract_technologies(text: str) -> list[str]:
    """
    Extract canonical technology names from resume text.
    """
    technologies: list[str] = []

    for term, canonical in TECHNOLOGY_TERMS.items():
        if _match_term(term, text):
            if canonical not in technologies:
                technologies.append(canonical)

    return sorted(technologies)


def _extract_skills(text: str) -> list[str]:
    """
    Extract canonical skill names from resume text.
    """
    skills: list[str] = []

    for canonical, synonyms in SKILL_TERMS.items():
        for synonym in synonyms:
            if _match_term(synonym, text):
                if canonical not in skills:
                    skills.append(canonical)
                break

    return sorted(skills)


def _extract_domains(text: str) -> list[str]:
    """
    Extract broad domain categories from resume text.
    """
    domains: set[str] = set()

    for domain, terms in DOMAIN_TERMS.items():
        for term in terms:
            if _match_term(term, text):
                domains.add(domain)
                break

    return sorted(domains)


# ============================================================
# PUBLIC SIGNAL EXTRACTION API
# ============================================================

def extract_resume_signals(text: str) -> dict:
    """
    Extract structured signals from resume text.

    Returns:
        {
            "skills": [...],
            "technologies": [...],
            "domain_exposure": [...],
            "seniority_level": "...",
            "years_of_experience": ...
        }
    """
    if not isinstance(text, str):
        raise TypeError("Resume text must be a string.")

    if not text.strip():
        return {
            "skills": [],
            "technologies": [],
            "domain_exposure": [],
            "seniority_level": "Mid-Level",
            "years_of_experience": None,
        }

    normalized_text = _normalize_text(text)

    technologies = _extract_technologies(normalized_text)
    skills = _extract_skills(normalized_text)
    domains = _extract_domains(normalized_text)
    seniority_level, years_exp = extract_seniority(normalized_text)

    return {
        "skills": skills,
        "technologies": technologies,
        "domain_exposure": domains,
        "seniority_level": seniority_level,
        "years_of_experience": years_exp,
    }