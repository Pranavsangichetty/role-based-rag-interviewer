import json
import logging
import re
from typing import Any
import httpx
from ..config import settings

logger = logging.getLogger("rag_interviewer.evaluator")

def calculate_overall_score(accuracy: float, completeness: float, depth: float, clarity: float) -> float:
    """Calculate weighted overall score (1-10)."""
    overall = (accuracy * 0.35) + (completeness * 0.25) + (depth * 0.25) + (clarity * 0.15)
    return round(max(1.0, min(10.0, overall)), 1)

def determine_hiring_recommendation(score: float) -> str:
    """Determine standardized hiring recommendation from overall score."""
    if score >= 8.5:
        return "Strong Hire"
    if score >= 7.0:
        return "Hire"
    if score >= 5.5:
        return "Lean Hire"
    return "No Hire"

def evaluate_answer_fallback(
    role: str,
    question: str,
    answer: str,
    retrieved_context: str,
    seniority: str = "Mid-Level"
) -> dict[str, Any]:
    """
    Deterministic rule-based rubric evaluation when no LLM API key is present.
    Evaluates accuracy, completeness, depth, and clarity based on technical heuristics.
    """
    answer_clean = answer.strip()
    words = answer_clean.split()
    word_count = len(words)
    answer_lower = answer_clean.lower()
    context_lower = retrieved_context.lower()

    if word_count == 0:
        return {
            "accuracy_score": 1.0,
            "completeness_score": 1.0,
            "depth_score": 1.0,
            "clarity_score": 1.0,
            "overall_score": 1.0,
            "feedback": "No answer was provided by the candidate.",
            "strengths": [],
            "weaknesses": ["Candidate left the response empty."],
            "ideal_answer": retrieved_context[:400].strip() if retrieved_context else f"A complete technical explanation addressing {question}."
        }

    # 1. Accuracy: check overlap of technical words with retrieved knowledge base
    context_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", context_lower))
    answer_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", answer_lower))
    overlap = len(context_words.intersection(answer_words)) if context_words else 5

    accuracy_raw = 5.0 + min(4.0, (overlap / max(1, len(context_words))) * 12.0)
    accuracy_score = round(max(2.0, min(9.5, accuracy_raw)), 1)

    # 2. Completeness: check answer length and structure
    if word_count >= 120:
        completeness_score = 9.0
    elif word_count >= 70:
        completeness_score = 7.5
    elif word_count >= 30:
        completeness_score = 6.0
    elif word_count >= 10:
        completeness_score = 4.0
    else:
        completeness_score = 2.5

    # 3. Depth: presence of technical reasoning & trade-off keywords
    depth_signals = [
        "trade-off", "tradeoff", "latency", "throughput", "concurrency", "scalable",
        "scale", "performance", "bottleneck", "cache", "distributed", "index", "failure",
        "optimize", "metric", "consistency", "reliability", "overhead", "memory"
    ]
    matched_depth = [w for w in depth_signals if w in answer_lower]
    depth_score = round(max(2.0, min(9.5, 4.0 + (len(matched_depth) * 1.0))), 1)

    # 4. Clarity: presence of structure and reasoning connectives
    clarity_signals = ["because", "therefore", "however", "in order to", "for example", "specifically", "first", "second", "additionally"]
    matched_clarity = [w for w in clarity_signals if w in answer_lower]
    clarity_score = round(max(3.0, min(9.5, 5.0 + (len(matched_clarity) * 0.8) + (1.0 if "\n" in answer_clean or "." in answer_clean else 0.0))), 1)

    overall_score = calculate_overall_score(accuracy_score, completeness_score, depth_score, clarity_score)

    strengths = []
    weaknesses = []

    if accuracy_score >= 7.0:
        strengths.append(f"Demonstrated good alignment with the core {role} domain principles.")
    if depth_score >= 6.5:
        strengths.append(f"Mentioned practical considerations ({', '.join(matched_depth[:2])}).")
    if word_count >= 50:
        strengths.append("Provided a well-elaborated response with sufficient detail.")

    if accuracy_score < 7.0:
        weaknesses.append("Could incorporate more specific domain terminology from the knowledge base.")
    if depth_score < 6.5:
        weaknesses.append("Lacked discussion of architectural trade-offs, edge cases, or failure modes.")
    if word_count < 40:
        weaknesses.append("Answer was somewhat brief; expanding on implementation nuances would strengthen the response.")

    if not strengths:
        strengths.append("Attempted to address the core question.")
    if not weaknesses:
        weaknesses.append("Minor: Could elaborate further on production deployment metrics.")

    ideal_answer = (
        f"A strong {seniority} answer should clearly address '{question}'. "
        f"Grounding in the knowledge base: {retrieved_context[:300].strip()}... "
        f"The candidate should analyze system trade-offs, scalability, and operational reliability."
    )

    feedback = (
        f"The candidate demonstrated {'strong' if overall_score >= 7.5 else 'moderate' if overall_score >= 5.5 else 'basic'} "
        f"understanding of the technical topic. Key strengths included: {'; '.join(strengths)}. "
        f"To improve: {'; '.join(weaknesses)}."
    )

    return {
        "accuracy_score": accuracy_score,
        "completeness_score": completeness_score,
        "depth_score": depth_score,
        "clarity_score": clarity_score,
        "overall_score": overall_score,
        "feedback": feedback,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "ideal_answer": ideal_answer,
    }

async def evaluate_answer(
    role: str,
    question: str,
    answer: str,
    retrieved_context: str,
    seniority: str = "Mid-Level"
) -> dict[str, Any]:
    """
    Evaluate candidate answer against rubric (Accuracy, Completeness, Depth, Clarity 1-10)
    using OpenAI-compatible LLM or deterministic fallback.
    """
    if not settings.llm_api_key or not settings.llm_api_key.strip():
        logger.info("No LLM_API_KEY configured. Utilizing deterministic rubric evaluator.")
        return evaluate_answer_fallback(role, question, answer, retrieved_context, seniority)

    prompt = f"""You are a Calibrated Senior Technical Interview Evaluator. Evaluate the candidate's answer based on the following rubric.

Target Role: {role}
Seniority Level: {seniority}
Interview Question: {question}

=== RETRIEVED KNOWLEDGE BASE CONTEXT (SOURCE OF TRUTH) ===
{retrieved_context}

=== CANDIDATE ANSWER ===
{answer}

=== EVALUATION RUBRIC ===
1. Technical Accuracy (1-10): Correctness of technical statements and alignment with the knowledge base.
2. Completeness (1-10): Did the candidate thoroughly answer all dimensions of the question?
3. Depth (1-10): Did the candidate articulate trade-offs, internal mechanisms, and edge cases?
4. Clarity (1-10): Is the answer structured, articulate, and well-reasoned?

=== INSTRUCTIONS ===
Return ONLY a valid JSON object matching this exact schema:
{{
  "accuracy_score": <float between 1.0 and 10.0>,
  "completeness_score": <float between 1.0 and 10.0>,
  "depth_score": <float between 1.0 and 10.0>,
  "clarity_score": <float between 1.0 and 10.0>,
  "feedback": "<detailed constructive feedback explaining scores>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness/area for improvement 1>", "<weakness/area for improvement 2>"],
  "ideal_answer": "<comprehensive reference answer grounded in the knowledge base>"
}}"""

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are a precise technical interviewer evaluator. You return strict, valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
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
            content = data["choices"][0]["message"]["content"].strip()
            parsed = json.loads(content)

            acc = float(parsed.get("accuracy_score", 5.0))
            comp = float(parsed.get("completeness_score", 5.0))
            dep = float(parsed.get("depth_score", 5.0))
            cla = float(parsed.get("clarity_score", 5.0))
            overall = calculate_overall_score(acc, comp, dep, cla)

            return {
                "accuracy_score": round(max(1.0, min(10.0, acc)), 1),
                "completeness_score": round(max(1.0, min(10.0, comp)), 1),
                "depth_score": round(max(1.0, min(10.0, dep)), 1),
                "clarity_score": round(max(1.0, min(10.0, cla)), 1),
                "overall_score": overall,
                "feedback": str(parsed.get("feedback", "Evaluation completed.")),
                "strengths": list(parsed.get("strengths", ["Addressed the technical question."])),
                "weaknesses": list(parsed.get("weaknesses", ["Could provide more implementation depth."])),
                "ideal_answer": str(parsed.get("ideal_answer", "Refer to knowledge base documentation.")),
            }
    except Exception as e:
        logger.warning(f"LLM evaluation call failed ({e}). Falling back to deterministic rubric evaluator.")
        return evaluate_answer_fallback(role, question, answer, retrieved_context, seniority)

def generate_final_summary(
    role: str,
    candidate_name: str,
    turns: list[dict[str, Any]],
    resume_signals: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Synthesize complete interview session results, competency breakdown,
    aggregated strengths/weaknesses, hiring recommendation, and structured summary.
    """
    answered_turns = [t for t in turns if t.get("answer") and t.get("answer").strip()]
    total_questions = len(turns)
    answered_questions = len(answered_turns)

    if not answered_turns:
        return {
            "candidate_name": candidate_name,
            "role": role,
            "total_questions": total_questions,
            "answered_questions": 0,
            "overall_score": 0.0,
            "recommendation": "No Hire",
            "competency_breakdown": {
                "accuracy": 0.0,
                "completeness": 0.0,
                "depth": 0.0,
                "clarity": 0.0,
            },
            "strengths": [],
            "areas_for_improvement": ["Candidate did not answer any interview questions."],
            "topics": sorted({t.get("topic") for t in turns if t.get("topic")}),
            "summary": f"{candidate_name} started an interview session for the {role} role but did not submit any answers."
        }

    # Aggregate scores
    acc_scores = [t.get("accuracy_score") or t.get("score") or 5.0 for t in answered_turns]
    comp_scores = [t.get("completeness_score") or t.get("score") or 5.0 for t in answered_turns]
    dep_scores = [t.get("depth_score") or t.get("score") or 5.0 for t in answered_turns]
    cla_scores = [t.get("clarity_score") or t.get("score") or 5.0 for t in answered_turns]

    avg_acc = round(sum(acc_scores) / len(acc_scores), 1)
    avg_comp = round(sum(comp_scores) / len(comp_scores), 1)
    avg_dep = round(sum(dep_scores) / len(dep_scores), 1)
    avg_cla = round(sum(cla_scores) / len(cla_scores), 1)

    overall_score = calculate_overall_score(avg_acc, avg_comp, avg_dep, avg_cla)
    recommendation = determine_hiring_recommendation(overall_score)

    # Collect strengths and weaknesses
    all_strengths: list[str] = []
    all_weaknesses: list[str] = []

    for t in answered_turns:
        if isinstance(t.get("strengths"), list):
            all_strengths.extend(t["strengths"])
        if isinstance(t.get("weaknesses"), list):
            all_weaknesses.extend(t["weaknesses"])

    # Deduplicate while preserving order
    unique_strengths = list(dict.fromkeys(all_strengths))[:4] or [f"Strong fundamental familiarity with {role} concepts."]
    unique_weaknesses = list(dict.fromkeys(all_weaknesses))[:4] or ["Deepen discussion of complex system trade-offs and failure scenarios."]

    topics = sorted({t.get("topic") for t in turns if t.get("topic")})

    narrative = (
        f"Candidate {candidate_name} completed a {total_questions}-question technical interview for {role} with an overall score of {overall_score}/10 ({recommendation}). "
        f"Technical accuracy averaged {avg_acc}/10, depth {avg_dep}/10, completeness {avg_comp}/10, and clarity {avg_cla}/10 across topics including {', '.join(topics) if topics else role}. "
        f"Primary strengths included: {'; '.join(unique_strengths[:2])}. Key areas for development: {'; '.join(unique_weaknesses[:2])}."
    )

    return {
        "candidate_name": candidate_name,
        "role": role,
        "total_questions": total_questions,
        "answered_questions": answered_questions,
        "overall_score": overall_score,
        "recommendation": recommendation,
        "competency_breakdown": {
            "accuracy": avg_acc,
            "completeness": avg_comp,
            "depth": avg_dep,
            "clarity": avg_cla,
        },
        "strengths": unique_strengths,
        "areas_for_improvement": unique_weaknesses,
        "topics": topics,
        "summary": narrative,
    }
