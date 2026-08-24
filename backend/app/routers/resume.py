import os
import tempfile
import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from ..schemas import ResumeParseResponse
from ..services.resume_parser import parse_pdf, extract_resume_signals


logger = logging.getLogger("rag_interviewer.resume")

router = APIRouter(prefix="/resume", tags=["resume"])

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


@router.post("/parse", response_model=ResumeParseResponse)
async def parse_resume(file: UploadFile = File(...)):
    """
    Upload and parse a candidate resume PDF.

    The endpoint:
    1. Validates the uploaded PDF.
    2. Extracts text from the PDF.
    3. Extracts resume signals from the text.
    4. Returns the structured resume information.
    """

    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents (.pdf) are supported."
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File exceeds maximum allowed size of "
                f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
            )
        )

    # Validate PDF header.
    if b"%PDF" not in content[:1024]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid PDF: File header does not match PDF specification."
        )

    temp_suffix = Path(file.filename).suffix or ".pdf"

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=temp_suffix
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        try:
            text = parse_pdf(tmp_path)
        except Exception as e:
            logger.exception("PDF parsing failed")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse PDF document: {str(e)}"
            )

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # ---------------------------------------------------------
    # IMPORTANT DIAGNOSTIC
    # ---------------------------------------------------------

    text_length = len(text.strip()) if text else 0

    logger.info(
        "Resume parsed successfully: filename=%s, extracted_text_length=%d",
        file.filename,
        text_length,
    )

    # Extract structured resume signals.
    signals = extract_resume_signals(text or "")


    logger.info(
        "Resume signals extracted: skills=%s technologies=%s domains=%s "
        "seniority=%s years=%s",
        signals.get("skills"),
        signals.get("technologies"),
        signals.get("domain_exposure"),
        signals.get("seniority_level"),
        signals.get("years_of_experience"),
    )

    return ResumeParseResponse(
        filename=file.filename,
        text=text,
        skills=signals.get("skills", []),
        technologies=signals.get("technologies", []),
        domain_exposure=signals.get("domain_exposure", []),
        seniority_level=signals.get("seniority_level", "Mid-Level"),
        years_of_experience=signals.get("years_of_experience"),
    )