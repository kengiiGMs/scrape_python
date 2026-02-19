from pydantic import BaseModel
from typing import List, Optional, Any, Union
from enum import Enum

class ScrapeRequest(BaseModel):
    url: str

class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus

class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

class ContentResponse(BaseModel):
    job_id: str
    content: Union[str, List[dict], dict]
