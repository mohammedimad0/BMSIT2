import asyncio
import logging
from typing import Callable, Any
from models import PipelineState
from storage import set_job

logger = logging.getLogger(__name__)


async def run_agent(
    name: str,
    fn: Callable,
    state: PipelineState,
    *args: Any
) -> PipelineState:
    """
    Run a single agent with exception handling.
    
    If agent fails, logs error, sets degraded=True,
    and returns state unchanged so pipeline continues.
    """
    logger.info(f"[AGENT:{name}] Starting")
    try:
        # Run agent in thread pool to avoid blocking
        result_state = await asyncio.to_thread(fn, state, *args)
        state.agent_statuses[name] = "ok"
        logger.info(f"[AGENT:{name}] Completed successfully")
        return result_state
    except Exception as e:
        logger.error(f"[AGENT:{name}] Failed: {str(e)}", exc_info=True)
        state.agent_statuses[name] = "failed"
        state.errors.append(f"{name}: {str(e)}")
        state.degraded = True
        return state


async def run_pipeline(
    job_id: str,
    source: str | bytes,
    source_type: str  # "pdf" | "image" | "text"
) -> PipelineState:
    """
    Master pipeline orchestrator.
    
    Runs all 5 agents sequentially with independent error handling.
    Never raises unhandled exceptions — always returns PipelineState.
    """
    logger.info(f"[PIPELINE] Starting job {job_id} with source_type={source_type}")
    
    # Import agents here to avoid circular imports
    from agents import (
        ocr_agent,
        preprocess_agent,
        simplify_agent,
        dyslexia_agent,
        html_agent,
    )
    
    state = PipelineState(job_id=job_id)
    
    # Agent 1: OCR Extraction
    state = await run_agent(
        "ocr",
        ocr_agent.run,
        state,
        source,
        source_type
    )
    
    # Agent 2: Text Preprocessing
    state = await run_agent(
        "preprocess",
        preprocess_agent.run,
        state
    )
    
    # Agent 3: LLM Simplification
    state = await run_agent(
        "simplify",
        simplify_agent.run,
        state
    )
    
    # Agent 4: Dyslexia Transforms
    state = await run_agent(
        "dyslexia",
        dyslexia_agent.run,
        state
    )
    
    # Agent 5: HTML Output Builder
    state = await run_agent(
        "html",
        html_agent.run,
        state
    )
    
    logger.info(
        f"[PIPELINE] Job {job_id} complete "
        f"(degraded={state.degraded}, errors={len(state.errors)})"
    )
    
    # Store final result
    await set_job(job_id, state)
    
    return state
