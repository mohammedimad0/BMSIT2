"""
NeuroAdapt Backend - FastAPI Server

Transforms NCERT PDF chapters into dyslexia-friendly HTML.
Runs offline on teacher's machine.

Endpoints:
  POST   /upload          - Accept file or text, start processing
  GET    /status/{job_id} - Check processing status
  GET    /result/{job_id} - Retrieve final HTML
  DELETE /job/{job_id}    - Clean up job
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from uuid import uuid4
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

from models import (
    PipelineState,
    UploadRequest,
    UploadResponse,
    JobStatus,
    JobResult,
    StudentMetricsModel,
    RecommendationResponse,
    PDFExportRequest,
)
from pipeline import run_pipeline
from storage import get_job, delete_job, cleanup_expired_jobs

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Model Preloading
# ============================================================================

async def check_ollama_availability() -> None:
    """
    Background task: check if Ollama is available at startup.
    
    Ollama is optional - if not available, simplify agent will pass text through.
    """
    try:
        logger.info("[STARTUP] Checking Ollama availability...")
        
        import requests
        from agents.simplify_agent import OLLAMA_BASE_URL
        
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            logger.info(f"[STARTUP] Ollama available at {OLLAMA_BASE_URL}")
        else:
            logger.warning(f"[STARTUP] Ollama not responding at {OLLAMA_BASE_URL}")
    
    except Exception as e:
        logger.warning(f"[STARTUP] Ollama unavailable: {str(e)} - backend will work without it")


async def cleanup_job_scheduler() -> None:
    """
    Background task: periodically clean up expired jobs.
    
    Runs every 60 seconds to remove jobs older than 1 hour.
    """
    while True:
        try:
            await asyncio.sleep(60)
            await cleanup_expired_jobs()
        except Exception as e:
            logger.error(f"[CLEANUP] Error: {str(e)}")


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown lifecycle management.
    """
    # Startup
    logger.info("[STARTUP] NeuroAdapt Backend starting...")
    
    # Check Ollama availability in background (don't block startup)
    asyncio.create_task(check_ollama_availability())
    
    # Start cleanup scheduler
    cleanup_task = asyncio.create_task(cleanup_job_scheduler())
    
    yield
    
    # Shutdown
    logger.info("[SHUTDOWN] NeuroAdapt Backend stopping...")
    cleanup_task.cancel()


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="NeuroAdapt Backend",
    description="Transform NCERT chapters into dyslexia-friendly HTML",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: Allow Next.js dev server on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Routes
# ============================================================================

@app.post("/upload", response_model=UploadResponse)
async def upload(
    file: Optional[UploadFile] = File(None),
    text_payload: Optional[UploadRequest] = None,
    background_tasks: BackgroundTasks = None,
):
    """
    Accept a PDF/image file or direct text, start processing pipeline.
    
    Returns job_id immediately.
    Processing happens asynchronously.
    """
    job_id = str(uuid4())
    logger.info(f"[API:upload] New job {job_id}")
    
    # Determine source
    if file:
        # Validate file
        logger.info(f"[API:upload] File upload: {file.filename} (size: {file.size} bytes)")
        
        if file.size > 50 * 1024 * 1024:  # 50MB limit
            logger.warning(f"[API:upload] File too large: {file.size} bytes")
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")
        
        if file.size == 0:
            logger.warning(f"[API:upload] File is empty: {file.filename}")
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Determine type
        filename = file.filename.lower() if file.filename else ""
        logger.debug(f"[API:upload] Filename: {filename}")
        
        if filename.endswith('.pdf'):
            source_type = "pdf"
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
            source_type = "image"
        else:
            logger.warning(f"[API:upload] Unsupported file type: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Use PDF or image (PNG, JPG, JPEG, TIFF)"
            )
        
        # Read file bytes
        source = await file.read()
        logger.info(f"[API:upload] Read {len(source)} bytes from file")
        
        if len(source) == 0:
            logger.warning(f"[API:upload] File read returned 0 bytes")
            raise HTTPException(status_code=400, detail="Failed to read file")
        
        logger.info(
            f"[API:upload] Job {job_id}: file upload "
            f"({file.filename}, {len(source)} bytes, type={source_type})"
        )
    
    elif text_payload:
        source = text_payload.text
        source_type = "text"
        logger.info(f"[API:upload] Job {job_id}: direct text ({len(source)} chars)")
    
    else:
        logger.warning(f"[API:upload] Job {job_id}: no file or text provided")
        raise HTTPException(status_code=400, detail="Provide either 'file' or 'text'")
    
    # Start pipeline in background
    background_tasks.add_task(
        run_pipeline,
        job_id,
        source,
        source_type
    )
    
    logger.info(f"[API:upload] Job {job_id} queued for processing")
    return UploadResponse(job_id=job_id, status="processing")


@app.get("/status/{job_id}", response_model=JobStatus)
async def status(job_id: str):
    """
    Check status of a job.
    
    Returns:
      - status: "processing" | "complete" | "failed"
      - degraded: bool (any agent failed)
      - agent_statuses: dict of agent name → "ok" | "degraded" | "failed"
    """
    logger.info(f"[API:status] Job {job_id}")
    
    state = await get_job(job_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or expired")
    
    # Determine status
    if state.html_output:
        status_str = "complete"
    elif state.errors and len(state.errors) == len(state.agent_statuses):
        # All agents failed
        status_str = "failed"
    else:
        status_str = "processing"
    
    return JobStatus(
        job_id=job_id,
        status=status_str,
        degraded=state.degraded,
        agent_statuses=state.agent_statuses,
    )


@app.get("/result/{job_id}")
async def result(job_id: str):
    """
    Retrieve final result for a job.
    
    Returns:
      - html: complete HTML document
      - degraded: bool
      - errors: list of error messages
      - agent_statuses: dict
    
    Returns 202 Accepted if still processing.
    """
    logger.info(f"[API:result] Job {job_id}")
    
    state = await get_job(job_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or expired")
    
    # If still processing (no HTML yet), return 202
    if not state.html_output:
        return {"status": "processing", "job_id": job_id}, 202
    
    return JobResult(
        job_id=job_id,
        html=state.html_output,
        degraded=state.degraded,
        errors=state.errors,
        agent_statuses=state.agent_statuses,
    )


@app.delete("/job/{job_id}")
async def delete_job_endpoint(job_id: str):
    """
    Delete a job and clean up stored result.
    """
    logger.info(f"[API:delete] Job {job_id}")
    
    state = await get_job(job_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    await delete_job(job_id)
    
    return {"status": "deleted", "job_id": job_id}


class RecommendationRequest(BaseModel):
    subject: str
    class_level: int
    metrics: Optional[StudentMetricsModel] = None


@app.post("/recommend")
async def get_recommendations(request: RecommendationRequest):
    """
    Get personalized learning recommendations based on student profile.

    Tries Gemini AI first for truly personalised recommendations.
    Falls back to curated static database if AI unavailable.

    Args:
        subject: Subject name (science, maths, english, social-science)
        class_level: Grade level (6-10)
        metrics: Optional student performance metrics

    Returns:
        Recommendations with YouTube, NPTEL, Khan Academy resources,
        AI-generated activities, 14-day study timeline, and profile insight.
    """
    logger.info(f"[API:recommend] subject={request.subject}, class_level={request.class_level}")

    try:
        from agents.recommendation_agent import (
            generate_recommendations,
            generate_personalized_study_plan
        )

        metrics_dict = request.metrics.dict() if request.metrics else None
        recommendations = generate_recommendations(request.subject, request.class_level, metrics_dict)
        study_plan = generate_personalized_study_plan(request.subject, request.class_level, metrics_dict)

        recommendations["study_plan"] = study_plan

        # Build response — include extra fields gracefully
        response_data = {
            "subject": request.subject,
            "class_level": request.class_level,
            "resources": recommendations.get("resources", {}),
            "tips": recommendations.get("tips", []),
            "difficulty": recommendations.get("difficulty", "intermediate"),
            "adaptations": recommendations.get("adaptations", []),
            "study_plan": study_plan,
            "activities": recommendations.get("activities", []),
            "study_timeline": recommendations.get("study_timeline", {}),
            "profile_insight": recommendations.get("profile_insight", ""),
            "ai_powered": recommendations.get("ai_powered", False),
        }

        return response_data
    except Exception as e:
        logger.error(f"[API:recommend] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/export-pdf")
async def export_pdf_endpoint(request: PDFExportRequest):
    """
    Export chapter to PDF.
    
    Args:
        chapter_id: Chapter ID to export
        include_original: Include original text
        include_glossary: Include glossary
        include_objectives: Include learning objectives
    
    Returns:
        PDF file bytes
    """
    logger.info(f"[API:export-pdf] chapter_id={request.chapter_id}")
    
    try:
        from pdf_export import generate_chapter_pdf
        import json
        
        # Get chapter data from storage
        state = await get_job(request.chapter_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Chapter {request.chapter_id} not found")
        
        if not state.html_output:
            raise HTTPException(status_code=400, detail="Chapter not yet processed")
        
        # Extract chapter metadata from state
        # We need to reconstruct chapter data from the transformed_chunks
        chunks = state.transformed_chunks or []
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chapter data to export")
        
        # Generate PDF
        pdf_bytes = generate_chapter_pdf(
            title="Chapter Export",
            subject="Subject",
            class_level=6,
            board="NCERT",
            chunks=chunks,
            include_original=request.include_original,
            include_glossary=request.include_glossary,
            include_objectives=request.include_objectives
        )
        
        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")
        
        logger.info(f"[API:export-pdf] Generated PDF: {len(pdf_bytes)} bytes")
        
        return {
            "pdf": pdf_bytes.hex(),  # Convert bytes to hex string for JSON
            "size_bytes": len(pdf_bytes),
            "chapter_id": request.chapter_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API:export-pdf] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/export-pdf/{chapter_id}")
async def download_pdf(chapter_id: str, include_original: bool = False, include_glossary: bool = True):
    """
    Download chapter as PDF (simplified endpoint).
    
    Args:
        chapter_id: Chapter ID to download
        include_original: Include original text
        include_glossary: Include glossary
    
    Returns:
        PDF file with proper headers
    """
    logger.info(f"[API:download-pdf] chapter_id={chapter_id}")
    
    try:
        from pdf_export import generate_chapter_pdf
        
        # Get chapter data from storage
        state = await get_job(chapter_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found")
        
        if not state.html_output:
            raise HTTPException(status_code=400, detail="Chapter not yet processed")
        
        chunks = state.transformed_chunks or []
        if not chunks:
            raise HTTPException(status_code=400, detail="No chapter data to export")
        
        # Generate PDF
        pdf_bytes = generate_chapter_pdf(
            title="Chapter Export",
            subject="Subject",
            class_level=6,
            board="NCERT",
            chunks=chunks,
            include_original=include_original,
            include_glossary=include_glossary,
            include_objectives=True
        )
        
        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")
        
        logger.info(f"[API:download-pdf] Generated PDF: {len(pdf_bytes)} bytes")
        
        from fastapi.responses import Response
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=chapter_{chapter_id}.pdf"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API:download-pdf] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Read port from env or default to 8000
    port = int(os.getenv('PORT', '8000'))
    reload = os.getenv('RELOAD', 'false').lower() == 'true'
    
    logger.info(f"[MAIN] Starting uvicorn on port {port} (reload={reload})")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
    )
