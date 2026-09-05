import io
import logging
import os
import sys
from pathlib import Path
from typing import Any
import asyncio
import streamlit as st

# Setup backend module import path
ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.services.rag_service import RAGService
from app.services.resume_parser import parse_pdf, extract_resume_signals
from app.services.question_generator import generate_question
from app.services.evaluator import evaluate_answer, generate_final_summary

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit_interviewer")

# ============================================================
# PAGE CONFIGURATION & STYLING
# ============================================================

st.set_page_config(
    page_title="Role-Based RAG Interviewer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Global Container Enhancements */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #60a5fa;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .citation-box {
        background-color: rgba(15, 23, 42, 0.8);
        border-left: 3px solid #3b82f6;
        padding: 0.6rem 1rem;
        border-radius: 4px;
        font-size: 0.88rem;
        color: #cbd5e1;
        margin-top: 0.5rem;
    }
    .skill-chip {
        display: inline-block;
        background-color: rgba(59, 130, 246, 0.2);
        color: #93c5fd;
        border: 1px solid rgba(59, 130, 246, 0.4);
        border-radius: 12px;
        padding: 2px 10px;
        font-size: 0.82rem;
        margin: 2px 4px 2px 0;
    }
    .rec-badge-strong {
        background-color: rgba(34, 197, 94, 0.2);
        color: #4ade80;
        border: 1px solid #22c55e;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
    }
    .rec-badge-hire {
        background-color: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        border: 1px solid #3b82f6;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
    }
    .rec-badge-lean {
        background-color: rgba(234, 179, 8, 0.2);
        color: #facc15;
        border: 1px solid #eab308;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
    }
    .rec-badge-no {
        background-color: rgba(239, 68, 68, 0.2);
        color: #f87171;
        border: 1px solid #ef4444;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CACHED RAG SERVICE SINGLETON
# ============================================================

@st.cache_resource(show_spinner="Initializing RAG Vector Engine & Embeddings...")
def get_rag_service() -> RAGService:
    """Initialize and cache the RAG Service singleton."""
    chroma_dir = str(BACKEND_DIR / "data" / "chroma")
    Path(chroma_dir).mkdir(parents=True, exist_ok=True)
    rag = RAGService(chroma_path=chroma_dir, embedding_model="all-MiniLM-L6-v2")

    # Auto-ingest knowledge base PDFs if collections are empty
    kb_dir = BACKEND_DIR / "data" / "knowledge_base"
    if kb_dir.exists():
        pdfs = list(kb_dir.rglob("*.pdf"))
        if pdfs:
            stats = rag.get_collection_stats()
            total_docs = sum(stats.values()) if stats else 0
            if total_docs == 0:
                logger.info(f"Auto-ingesting {len(pdfs)} knowledge base PDFs into ChromaDB...")
                for pdf in pdfs:
                    try:
                        rag.ingest_pdf(pdf, role="AI/ML Engineer", also_to_global=True)
                    except Exception as e:
                        logger.warning(f"Could not auto-ingest {pdf.name}: {e}")
    return rag

def run_async(coro):
    """Safely run an async coroutine synchronously in Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# ============================================================
# SESSION STATE MANAGEMENT
# ============================================================

if "stage" not in st.session_state:
    st.session_state.stage = "setup"  # "setup", "interview", "summary"
if "candidate_name" not in st.session_state:
    st.session_state.candidate_name = ""
if "role" not in st.session_state:
    st.session_state.role = "AI/ML Engineer"
if "resume_signals" not in st.session_state:
    st.session_state.resume_signals = None
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "current_turn" not in st.session_state:
    st.session_state.current_turn = 1
if "max_turns" not in st.session_state:
    st.session_state.max_turns = 5
if "current_question" not in st.session_state:
    st.session_state.current_question = ""
if "current_retrieved" not in st.session_state:
    st.session_state.current_retrieved = []
if "current_topic" not in st.session_state:
    st.session_state.current_topic = ""
if "turn_history" not in st.session_state:
    st.session_state.turn_history = []
if "final_summary" not in st.session_state:
    st.session_state.final_summary = None

# ============================================================
# SIDEBAR CONTROLS & SETTINGS
# ============================================================

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("Interview Console")
    st.caption("Role-Specific RAG Technical Interviewer")

    st.markdown("---")
    st.subheader("⚙️ Session Setup")

    role_options = ["AI/ML Engineer", "Backend Engineer", "Data Scientist"]
    selected_role = st.selectbox(
        "Target Role",
        options=role_options,
        index=role_options.index(st.session_state.role) if st.session_state.role in role_options else 0,
        disabled=(st.session_state.stage != "setup"),
    )
    st.session_state.role = selected_role

    candidate_input = st.text_input(
        "Candidate Name",
        value=st.session_state.candidate_name or "Alex Mercer",
        disabled=(st.session_state.stage != "setup"),
    )
    st.session_state.candidate_name = candidate_input.strip() or "Candidate"

    st.markdown("---")
    st.subheader("🔑 LLM Configuration")

    # Check Streamlit secrets or environment for LLM API Key and settings
    secrets_key = ""
    try:
        secrets_key = st.secrets.get("OPENAI_API_KEY") or st.secrets.get("LLM_API_KEY") or ""
        secrets_model = st.secrets.get("LLM_MODEL")
        if secrets_model:
            settings.llm_model = secrets_model
        secrets_base_url = st.secrets.get("LLM_BASE_URL")
        if secrets_base_url:
            settings.llm_base_url = secrets_base_url
    except Exception:
        secrets_key = ""

    env_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY") or secrets_key

    api_key_input = st.text_input(
        "OpenAI API Key (Optional)",
        value=env_key,
        type="password",
        help="Provide an OpenAI-compatible API key for dynamic LLM generation. If blank, deterministic offline RAG evaluation is used.",
    )

    if api_key_input:
        settings.llm_api_key = api_key_input
        st.success(f"✅ LLM Online Mode ({settings.llm_model})", icon="🤖")
    else:
        settings.llm_api_key = ""
        st.info("⚡ Offline RAG Fallback Mode Active (100% deterministic & offline)", icon="🛡️")

    st.markdown("---")
    # Vector DB Status
    rag = get_rag_service()
    col_stats = rag.get_collection_stats()
    total_vectors = sum(col_stats.values()) if col_stats else 0
    st.markdown(f"**📚 Knowledge Base:** `{total_vectors} indexed chunks`")

    if st.session_state.stage != "setup":
        if st.button("🔄 Reset Interview", use_container_width=True):
            st.session_state.stage = "setup"
            st.session_state.resume_signals = None
            st.session_state.resume_text = ""
            st.session_state.current_turn = 1
            st.session_state.turn_history = []
            st.session_state.final_summary = None
            st.rerun()

# ============================================================
# STAGE 1: CANDIDATE SETUP & RESUME UPLOAD
# ============================================================

if st.session_state.stage == "setup":
    st.markdown('<div class="main-header">🎯 Role-Based RAG Technical Interviewer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Upload a candidate resume PDF to extract technical signals, retrieve domain knowledge, and start a 5-turn grounded interview.</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1.2, 0.8], gap="large")

    with col1:
        st.subheader("📄 Resume Upload")
        uploaded_file = st.file_uploader(
            "Upload Candidate Resume (PDF)",
            type=["pdf"],
            help="Upload a technical resume in PDF format. Text and technical signals will be parsed in-memory.",
        )

        if uploaded_file is not None:
            try:
                with st.spinner("Extracting candidate signals from resume..."):
                    resume_text = parse_pdf(uploaded_file)
                    if not resume_text.strip():
                        st.error("Could not extract readable text from this PDF. Please upload a valid text-based PDF.")
                    else:
                        signals = extract_resume_signals(resume_text)
                        st.session_state.resume_text = resume_text
                        st.session_state.resume_signals = signals
                        st.success(f"Successfully parsed **{uploaded_file.name}** ({len(resume_text)} characters)", icon="✅")
            except Exception as e:
                st.error(f"Error parsing PDF: {e}")

        # Start interview button
        st.markdown("---")
        can_start = st.session_state.resume_signals is not None
        if st.button(
            "🚀 Start Technical Interview",
            type="primary",
            use_container_width=True,
            disabled=not can_start,
        ):
            with st.spinner("Generating Turn 1 Grounded Question..."):
                role = st.session_state.role
                signals = st.session_state.resume_signals
                query = f"{role} core architecture distributed systems latency trade-offs"
                retrieved = rag.retrieve(role=role, query=query, top_k=settings.top_k)

                question = run_async(
                    generate_question(
                        role=role,
                        signals=signals,
                        retrieved=retrieved,
                        previous=[],
                    )
                )

                st.session_state.current_turn = 1
                st.session_state.current_question = question
                st.session_state.current_retrieved = retrieved
                st.session_state.current_topic = role
                st.session_state.stage = "interview"
                st.rerun()

    with col2:
        st.subheader("🔍 Extracted Candidate Profile")
        if st.session_state.resume_signals:
            signals = st.session_state.resume_signals
            seniority = signals.get("seniority_level", "Mid-Level")
            years = signals.get("years_of_experience")

            st.markdown(f"**Detected Seniority:** `{seniority}`" + (f" ({years} years exp)" if years else ""))

            st.markdown("**Core Skills:**")
            skills = signals.get("skills", [])
            if skills:
                st.markdown(" ".join([f'<span class="skill-chip">{s}</span>' for s in skills]), unsafe_allow_html=True)
            else:
                st.caption("No specific skills detected.")

            st.markdown("<br/>**Technologies & Frameworks:**", unsafe_allow_html=True)
            techs = signals.get("technologies", [])
            if techs:
                st.markdown(" ".join([f'<span class="skill-chip">{t}</span>' for t in techs]), unsafe_allow_html=True)
            else:
                st.caption("No specific frameworks detected.")

            st.markdown("<br/>**Domain Exposure:**", unsafe_allow_html=True)
            domains = signals.get("domain_exposure", [])
            if domains:
                st.markdown(" ".join([f'<span class="skill-chip">{d}</span>' for d in domains]), unsafe_allow_html=True)
            else:
                st.caption("General engineering exposure.")
        else:
            st.info("Upload a resume PDF on the left to inspect extracted skills, technologies, and seniority level.")

# ============================================================
# STAGE 2: LIVE INTERVIEW CONSOLE
# ============================================================

elif st.session_state.stage == "interview":
    curr_turn = st.session_state.current_turn
    max_turns = st.session_state.max_turns
    progress_val = int((curr_turn / max_turns) * 100)

    st.markdown('<div class="main-header">💬 Live Technical Interview</div>', unsafe_allow_html=True)
    st.progress(progress_val, text=f"Interview Progress: Turn {curr_turn} of {max_turns}")

    # Top stats bar
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Candidate:** `{st.session_state.candidate_name}`")
    with c2:
        st.markdown(f"**Target Role:** `{st.session_state.role}`")
    with c3:
        seniority = (st.session_state.resume_signals or {}).get("seniority_level", "Mid-Level")
        st.markdown(f"**Target Level:** `{seniority}`")

    st.markdown("---")

    # Current Grounded Question Card
    st.subheader(f"📌 Turn {curr_turn} Question")
    st.info(st.session_state.current_question, icon="💡")

    # Citations & Retrieved Context
    if st.session_state.current_retrieved:
        with st.expander("📚 Knowledge Base Grounding & Citations (RAG Context)", expanded=False):
            for item in st.session_state.current_retrieved[:3]:
                st.markdown(f"**{item.get('citation')}** (Similarity Score: `{item.get('score')}`)")
                st.markdown(f'<div class="citation-box">{item.get("text")[:350]}...</div>', unsafe_allow_html=True)

    # Candidate Answer Input
    st.markdown("### ✍️ Your Answer")
    candidate_answer = st.text_area(
        "Provide a detailed, technical answer explaining mechanisms, trade-offs, and scalability:",
        height=180,
        placeholder="Explain your approach, architecture, trade-offs, and edge case handling...",
        key=f"answer_input_turn_{curr_turn}",
    )

    col_btn, col_skip = st.columns([0.8, 0.2])

    with col_btn:
        if st.button("Submit Answer & Next Turn ➔", type="primary", use_container_width=True):
            if not candidate_answer.strip():
                st.warning("Please type your technical answer before submitting.")
            else:
                with st.spinner("Evaluating technical response against 4-criterion rubric..."):
                    context_str = "\n".join([x["text"] for x in st.session_state.current_retrieved])
                    seniority_val = (st.session_state.resume_signals or {}).get("seniority_level", "Mid-Level")

                    eval_res = run_async(
                        evaluate_answer(
                            role=st.session_state.role,
                            question=st.session_state.current_question,
                            answer=candidate_answer,
                            retrieved_context=context_str,
                            seniority=seniority_val,
                        )
                    )

                    # Save turn record
                    turn_record = {
                        "turn_number": curr_turn,
                        "question": st.session_state.current_question,
                        "topic": st.session_state.current_topic,
                        "answer": candidate_answer,
                        "retrieved": st.session_state.current_retrieved,
                        "sources": [x.get("source", "knowledge_base") for x in st.session_state.current_retrieved],
                        "score": eval_res.get("overall_score"),
                        "accuracy_score": eval_res.get("accuracy_score"),
                        "depth_score": eval_res.get("depth_score"),
                        "completeness_score": eval_res.get("completeness_score"),
                        "clarity_score": eval_res.get("clarity_score"),
                        "feedback": eval_res.get("feedback"),
                        "strengths": eval_res.get("strengths", []),
                        "weaknesses": eval_res.get("weaknesses", []),
                        "ideal_answer": eval_res.get("ideal_answer", ""),
                    }
                    st.session_state.turn_history.append(turn_record)

                    # Check if final turn reached
                    if curr_turn >= max_turns:
                        st.session_state.stage = "summary"
                        st.rerun()
                    else:
                        # Fetch next question
                        next_turn = curr_turn + 1
                        signals = st.session_state.resume_signals or {}
                        skills = signals.get("skills", [])
                        topic = skills[(next_turn - 1) % len(skills)] if skills else st.session_state.role
                        retrieved = rag.retrieve(role=st.session_state.role, query=f"{st.session_state.role} {topic}", top_k=settings.top_k)

                        next_q = run_async(
                            generate_question(
                                role=st.session_state.role,
                                signals=signals,
                                retrieved=retrieved,
                                previous=st.session_state.turn_history,
                            )
                        )

                        st.session_state.current_turn = next_turn
                        st.session_state.current_question = next_q
                        st.session_state.current_retrieved = retrieved
                        st.session_state.current_topic = topic
                        st.rerun()

    # Previous Turn Timeline Accordion
    if st.session_state.turn_history:
        st.markdown("---")
        st.subheader("📜 Previous Turns & Evaluations")
        for t in reversed(st.session_state.turn_history):
            with st.expander(f"Turn {t['turn_number']}: Score {t['score']}/10 — {t['question'][:80]}...", expanded=False):
                st.markdown(f"**Question:** {t['question']}")
                st.markdown(f"**Your Answer:** {t['answer']}")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Accuracy", f"{t['accuracy_score']}/10")
                m2.metric("Depth", f"{t['depth_score']}/10")
                m3.metric("Completeness", f"{t['completeness_score']}/10")
                m4.metric("Clarity", f"{t['clarity_score']}/10")
                st.markdown(f"**Feedback:** {t['feedback']}")
                if t["strengths"]:
                    st.markdown(f"**Strengths:** {'; '.join(t['strengths'])}")
                if t["weaknesses"]:
                    st.markdown(f"**Areas to Improve:** {'; '.join(t['weaknesses'])}")

# ============================================================
# STAGE 3: EXECUTIVE SUMMARY & SCORECARD REPORT
# ============================================================

elif st.session_state.stage == "summary":
    st.markdown('<div class="main-header">📊 Executive Interview Assessment</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Comprehensive technical evaluation, competency breakdown, and hiring recommendation.</div>', unsafe_allow_html=True)

    summary = generate_final_summary(
        role=st.session_state.role,
        candidate_name=st.session_state.candidate_name,
        turns=st.session_state.turn_history,
        resume_signals=st.session_state.resume_signals,
    )

    # Top Level Score & Recommendation
    col_score, col_rec, col_stat = st.columns([1, 1, 1], gap="medium")

    overall = summary["overall_score"]
    rec = summary["recommendation"]

    with col_score:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{overall} / 10</div>
                <div class="metric-label">Overall Evaluation Score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_rec:
        rec_class = "rec-badge-strong" if rec == "Strong Hire" else "rec-badge-hire" if rec == "Hire" else "rec-badge-lean" if rec == "Lean Hire" else "rec-badge-no"
        st.markdown(
            f"""
            <div class="metric-card">
                <div style="margin-top: 6px;"><span class="{rec_class}">{rec}</span></div>
                <div class="metric-label" style="margin-top: 12px;">Recommendation</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_stat:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{summary['answered_questions']} / {summary['total_questions']}</div>
                <div class="metric-label">Turns Completed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Competency Breakdown
    st.subheader("🎯 Competency Breakdown (1–10)")
    comp = summary["competency_breakdown"]
    cb1, cb2, cb3, cb4 = st.columns(4)
    cb1.metric("Technical Accuracy (35%)", f"{comp['accuracy']} / 10")
    cb2.metric("Technical Depth (25%)", f"{comp['depth']} / 10")
    cb3.metric("Completeness (25%)", f"{comp['completeness']} / 10")
    cb4.metric("Clarity (15%)", f"{comp['clarity']} / 10")

    st.markdown("---")

    # Strengths and Weaknesses
    col_s, col_w = st.columns(2, gap="large")
    with col_s:
        st.subheader("🌟 Key Strengths")
        for s in summary["strengths"]:
            st.success(f"• {s}")

    with col_w:
        st.subheader("📈 Areas for Improvement")
        for w in summary["areas_for_improvement"]:
            st.warning(f"• {w}")

    st.markdown("---")
    st.subheader("📝 Executive Summary")
    st.info(summary["summary"], icon="📋")

    # Turn-by-turn audit table
    st.markdown("---")
    st.subheader("📑 Turn-by-Turn Detailed Evaluation History")
    for t in st.session_state.turn_history:
        with st.expander(f"Turn {t['turn_number']} — Overall Score: {t['score']}/10", expanded=False):
            st.markdown(f"**Question:** {t['question']}")
            st.markdown(f"**Answer:** {t['answer']}")
            st.markdown(f"**Feedback:** {t['feedback']}")
            if t.get("ideal_answer"):
                st.markdown(f"**Ideal Benchmark Answer:** {t['ideal_answer']}")

    st.markdown("---")
    if st.button("🔄 Start Another Interview", type="primary", use_container_width=True):
        st.session_state.stage = "setup"
        st.session_state.resume_signals = None
        st.session_state.resume_text = ""
        st.session_state.current_turn = 1
        st.session_state.turn_history = []
        st.session_state.final_summary = None
        st.rerun()
