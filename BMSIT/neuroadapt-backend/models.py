from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class AgentStatus(str, Enum):
    """Agent execution status"""
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


class PipelineState(BaseModel):
    """Shared state flowing through all pipeline agents"""
    job_id: str
    raw_text: str = ""
    cleaned_text: str = ""
    simplified_text: str = ""
    transformed_chunks: List[Dict] = Field(default_factory=list)
    html_output: str = ""
    agent_statuses: Dict[str, str] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    degraded: bool = False
    wpm: Optional[int] = None
    profile: Optional[str] = None


class UploadRequest(BaseModel):
    """Request body for direct text upload"""
    text: str = Field(..., min_length=1, max_length=1_000_000)


class JobStatus(BaseModel):
    """Response for /status/{job_id}"""
    job_id: str
    status: str  # "processing" | "complete" | "failed"
    degraded: bool
    agent_statuses: Dict[str, str]


class JobResult(BaseModel):
    """Response for /result/{job_id}"""
    job_id: str
    html: str
    degraded: bool
    errors: List[str]
    agent_statuses: Dict[str, str]


class UploadResponse(BaseModel):
    """Response for /upload"""
    job_id: str
    status: str  # "processing"


class RecommendationResource(BaseModel):
    """Single learning resource"""
    title: str
    channel: Optional[str] = None
    platform: Optional[str] = None
    url: str


class StudentMetricsModel(BaseModel):
    """Student performance metrics"""
    attentionSpanSec: Optional[int] = 300
    readingWpm: Optional[int] = 150
    focusDurationSec: Optional[int] = 300
    mistakesPerQuiz: Optional[int] = 0
    recentStress: Optional[float] = 0.1
    completedLessons: Optional[int] = 0
    focusCoins: Optional[int] = 0
    xpPoints: Optional[int] = 0
    profile: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response for /recommend endpoint"""
    subject: str
    class_level: int
    resources: Dict[str, List[RecommendationResource]]
    tips: List[str]
    difficulty: str
    adaptations: List[str]
    study_plan: Optional[Dict[str, Any]] = None


class PDFExportRequest(BaseModel):
    """Request body for PDF export"""
    chapter_id: str
    include_original: bool = False
    include_glossary: bool = True
    include_objectives: bool = True
