# Role-Based RAG Interviewer

An AI-powered technical interview platform that conducts role-specific, resume-aware interviews using Retrieval-Augmented Generation (RAG).

The system combines a candidate's resume with a role-specific knowledge base to generate relevant technical questions, evaluate candidate responses, and produce an interview performance report.

---

## 🚀 Overview

Traditional mock interview systems often generate generic questions without considering the candidate's background or the requirements of the target role.

The **Role-Based RAG Interviewer** addresses this by combining:

- Candidate resume analysis
- Role-specific knowledge retrieval
- Retrieval-Augmented Generation
- Adaptive technical questioning
- Answer evaluation
- Interview scoring and reporting

The result is a structured technical interview experience tailored to both the candidate and the selected engineering role.

---

## ✨ Key Features

### 📄 Resume-Aware Interviews

Candidates can upload their resume as a PDF.

The backend extracts relevant information from the resume and uses it as part of the interview context.

### 🎯 Role-Based Interviewing

The interviewer adapts its questions according to the selected engineering role.

Examples include:

- AI/ML Engineer
- Backend Engineer
- Data Engineer
- Software Engineer

### 🧠 Retrieval-Augmented Generation

The system retrieves relevant information from the role-specific knowledge base before generating interview questions.

This helps keep questions grounded in the available technical knowledge rather than relying entirely on unrestricted generation.

### 💬 Interactive Technical Interview

The candidate progresses through multiple interview turns.

Each answer is processed by the backend before the next question is generated.

### 📊 Automated Evaluation

Candidate responses are evaluated against a structured rubric.

The system produces an overall interview assessment containing strengths, weaknesses, and scoring information.

### 🔄 Adaptive Interview Flow

The interview maintains session state so that subsequent questions can depend on the current interview context and previous responses.

### 🛡️ Grounded Question Generation

The RAG pipeline provides relevant retrieved context to the question-generation process, helping produce technically relevant and role-specific questions.

---

# 🏗️ System Architecture

The application uses a decoupled frontend and backend architecture.

```mermaid
flowchart TD

    Candidate["Candidate"]

    subgraph Frontend["Frontend - Next.js on Vercel"]
        Setup["Candidate Setup"]
        ResumeUpload["Resume PDF Upload"]
        InterviewUI["Live Interview Interface"]
        ReportUI["Evaluation Report"]

        Setup --> ResumeUpload
        ResumeUpload --> InterviewUI
        InterviewUI --> ReportUI
    end

    subgraph Backend["Backend - FastAPI on Render"]
        API["FastAPI REST API"]

        Health["Health Endpoint"]
        ResumeAPI["Resume Processing"]
        SessionAPI["Interview Sessions"]

        Parser["Resume Parser"]
        RAG["RAG Service"]
        Embeddings["Sentence Transformer Embeddings"]
        QuestionGen["Question Generation"]
        Evaluator["Answer Evaluation"]

        API --> Health
        API --> ResumeAPI
        API --> SessionAPI

        ResumeAPI --> Parser
        SessionAPI --> RAG
        RAG --> Embeddings
        RAG --> QuestionGen
        SessionAPI --> Evaluator
    end

    Candidate --> Setup

    ResumeUpload -->|"HTTPS REST API"| ResumeAPI
    InterviewUI -->|"HTTPS REST API"| SessionAPI

    Parser --> RAG
    QuestionGen --> InterviewUI
    Evaluator --> ReportUI
