import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from models import PipelineState

logger = logging.getLogger(__name__)

# In-memory job storage
job_store: Dict[str, PipelineState] = {}
store_lock = asyncio.Lock()

# Job expiration: 1 hour
JOB_EXPIRY_SECONDS = 3600
job_created_at: Dict[str, datetime] = {}


async def set_job(job_id: str, state: PipelineState) -> None:
    """Store a job state"""
    async with store_lock:
        job_store[job_id] = state
        job_created_at[job_id] = datetime.now()
        logger.info(f"[STORAGE] Job {job_id} stored (degraded={state.degraded})")


async def get_job(job_id: str) -> Optional[PipelineState]:
    """Retrieve a job state"""
    async with store_lock:
        if job_id not in job_store:
            return None
        
        # Check expiry
        created = job_created_at.get(job_id, datetime.now())
        if datetime.now() - created > timedelta(seconds=JOB_EXPIRY_SECONDS):
            logger.info(f"[STORAGE] Job {job_id} expired, removing")
            del job_store[job_id]
            del job_created_at[job_id]
            return None
        
        return job_store[job_id]


async def delete_job(job_id: str) -> None:
    """Delete a job state"""
    async with store_lock:
        if job_id in job_store:
            del job_store[job_id]
            del job_created_at[job_id]
            logger.info(f"[STORAGE] Job {job_id} deleted")


async def cleanup_expired_jobs() -> None:
    """Background task to clean up expired jobs"""
    async with store_lock:
        expired = []
        now = datetime.now()
        for job_id, created in job_created_at.items():
            if now - created > timedelta(seconds=JOB_EXPIRY_SECONDS):
                expired.append(job_id)
        
        for job_id in expired:
            del job_store[job_id]
            del job_created_at[job_id]
        
        if expired:
            logger.info(f"[STORAGE] Cleaned up {len(expired)} expired jobs")
