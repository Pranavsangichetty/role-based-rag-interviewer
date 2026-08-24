import logging
from typing import Any
import httpx
from ..config import settings

logger = logging.getLogger("rag_interviewer.question_gen")

ROLE_PERSONAS = {
    "ai/ml engineer": "You are a Principal AI/ML Staff Interviewer assessing machine learning engineering, deep learning, retrieval-augmented generation (RAG), and model deployment.",
    "backend engineer": "You are a Principal Backend Systems Architect assessing distributed systems, API design, database transactions, concurrency, and reliability.",
    "data scientist": "You are a Lead Data Science Director assessing statistical modeling, experimentation, feature engineering, and data pipeline design.",
}

SENIORITY_DIFFICULTY = {
    "junior": "Target foundational technical mechanisms, basic syntax/framework usage, edge cases, and code-level comprehension.",
    "mid-level": "Target practical design trade-offs, scalability, failure handling, performance optimization, and architectural integration.",
    "senior": "Target distributed systems complexity, performance bottlenecks, high-availability trade-offs, fault tolerance, and production trade-offs.",
    "staff/lead": "Target system-wide architectural paradigm choices, trade-offs under high concurrency, multi-region reliability, and organizational architectural patterns.",
}

def make_prompt(role: str, signals: dict[str, Any], retrieved: list[dict[str, Any]], previous: list[dict[str, Any]]) -> str:
    """Construct an adaptive, grounded prompt factoring in seniority, previous turns, and RAG context."""
    seniority = signals.get("seniority_level", "Mid-Level")
    skills = signals.get("skills", [])
    technologies = signals.get("technologies", [])

    # Format retrieved knowledge base context
    if retrieved:
        context_blocks = []
        for x in retrieved:
            citation = x.get("citation") or f"[{x.get('source', 'Knowledge Base')}]"
            context_blocks.append(f"{citation}:\n{x['text']}")
        context = "\n\n".join(context_blocks)
    else:
        context = "[No specific knowledge base context retrieved. Formulate question based strictly on standard role competencies.]"

    # Format previous turns
    if previous:
        history_blocks = []
        for i, t in enumerate(previous[-5:], start=1):
            q = t.get("question", "")
            a = t.get("answer") or "[Candidate did not provide an answer]"
            history_blocks.append(f"Turn {i} Question: {q}\nTurn {i} Candidate Answer: {a}")
        history = "\n\n".join(history_blocks)
    else:
        history = "[This is Turn 1. No previous interview turns.]"

    persona = ROLE_PERSONAS.get(role.lower().strip(), f"You are a Senior Technical Interviewer assessing candidates for {role}.")
    difficulty = SENIORITY_DIFFICULTY.get(seniority.lower().strip(), SENIORITY_DIFFICULTY["mid-level"])

    prompt = f"""{persona}

Target Role: {role}
Candidate Seniority Level: {seniority}
Seniority Focus: {difficulty}
Candidate Skills: {', '.join(skills) if skills else 'General ' + role}
Candidate Technologies: {', '.join(technologies) if technologies else 'Not specified'}

=== RETRIEVED KNOWLEDGE BASE CONTEXT ===
{context}

=== PREVIOUS INTERVIEW TURNS ===
{history}

=== INSTRUCTIONS & RULES ===
1. GROUNDING RULE: Ground the technical scenario and question in the retrieved knowledge-base context above.
2. ADAPTIVITY RULE: Inspect the candidate's previous answers in the history. If the candidate answered previous questions well, challenge them with deeper trade-offs or related edge cases. If they struggled, explore a foundational concept from the context.
3. SENIORITY RULE: Calibrate the question difficulty strictly for a {seniority} candidate.
4. NO GENERICS RULE: Do NOT ask generic behavioral or broad questions like 'Tell me about yourself' or 'What is {role}?'.
5. OUTPUT RULE: Return ONLY the question text. Do not include introductory or concluding conversational filler."""
    return prompt

def generate_fallback_question(role: str, signals: dict[str, Any], retrieved: list[dict[str, Any]], previous: list[dict[str, Any]]) -> str:
    """Deterministic, template-based question generation when no LLM API key is available."""
    seniority = signals.get("seniority_level", "Mid-Level")
    turn_num = len(previous) + 1

    # Extract topic from context or skills
    if retrieved and retrieved[0].get("text"):
        raw_text = retrieved[0]["text"]
        first_sentence = raw_text.split(".")[0].strip()
        if len(first_sentence) > 120:
            first_sentence = first_sentence[:120].rsplit(" ", 1)[0]
        topic = first_sentence
        source = retrieved[0].get("source", "knowledge base")
    else:
        skills = signals.get("skills", [])
        topic = skills[(turn_num - 1) % len(skills)] if skills else f"{role} core architecture"
        source = "technical reference"

    templates = [
        f"In the context of {source}, specifically concerning '{topic}', how would you explain the core mechanism and its trade-offs for a {seniority} {role} implementation?",
        f"Regarding '{topic}', what primary performance bottlenecks or scaling limitations arise in a high-throughput {role} environment, and how would you mitigate them?",
        f"Suppose a production system utilizing '{topic}' experiences unexpected latency spikes or failures. What debugging methodology and metrics would you examine to isolate the root cause?",
        f"How would you integrate '{topic}' with modern cloud and data infrastructure while balancing consistency, latency, and operational complexity?",
        f"Reflecting on '{topic}', what alternative architectural patterns exist, and under what specific engineering constraints would you choose them over this approach?",
    ]
    template_idx = (turn_num - 1) % len(templates)
    return templates[template_idx]

async def generate_question(
    role: str,
    signals: dict[str, Any],
    retrieved: list[dict[str, Any]],
    previous: list[dict[str, Any]]
) -> str:
    """Generate an adaptive, grounded technical interview question via LLM or deterministic fallback."""
    if not settings.llm_api_key or not settings.llm_api_key.strip():
        logger.info("No LLM_API_KEY configured. Utilizing deterministic grounded question generator.")
        return generate_fallback_question(role, signals, retrieved, previous)

    prompt = make_prompt(role, signals, retrieved, previous)
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are an expert technical interviewer who generates grounded, rigorous technical interview questions."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 250,
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(
                settings.llm_base_url.rstrip("/") + "/chat/completions",
                json=payload,
                headers=headers
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"LLM API call failed ({e}). Falling back to deterministic question generator.")
        return generate_fallback_question(role, signals, retrieved, previous)

