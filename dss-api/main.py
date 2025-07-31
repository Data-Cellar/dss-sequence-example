import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict

import requests
import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DSS Mock API",
    description="Mock Decision Support System - Functionality 1 (Energy Optimization) for proof-of-concept integration",
    version="1.0.0",
)

# API Key authentication
API_KEY_HEADER = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def get_api_key(api_key: str = Depends(api_key_header)):
    """Get the API key from the environment variable"""

    expected_key = os.getenv("BACKEND_API_KEY")

    if expected_key and api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    return api_key


# In-memory job storage
jobs_storage: Dict[str, Dict[str, Any]] = {}


class F1JobRequest(BaseModel):
    building_id: str = "building_001"
    optimization_type: str = "energy_efficiency"
    parameters: Dict[str, Any] = {}


class F1JobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    created_at: str


class F1JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    result: Dict[str, Any] = None
    created_at: str
    completed_at: str = None


async def simulate_job_processing(job_id: str, callback_url: str = None):
    """Simulate DSS F1 (Energy Optimization) job processing with status updates"""
    try:
        # Update job status to running
        jobs_storage[job_id]["status"] = "running"
        jobs_storage[job_id]["progress"] = 10

        # Simulate processing time (10 minutes -> 10 seconds for demo)
        await asyncio.sleep(2)
        jobs_storage[job_id]["progress"] = 25

        await asyncio.sleep(2)
        jobs_storage[job_id]["progress"] = 50

        await asyncio.sleep(2)
        jobs_storage[job_id]["progress"] = 75

        await asyncio.sleep(2)
        jobs_storage[job_id]["progress"] = 90

        await asyncio.sleep(2)

        # Complete the job
        jobs_storage[job_id]["status"] = "completed"
        jobs_storage[job_id]["progress"] = 100
        jobs_storage[job_id]["completed_at"] = datetime.now().isoformat()
        jobs_storage[job_id]["result"] = {
            "energy_savings_kwh": 245.8,
            "cost_reduction_eur": 48.72,
            "co2_reduction_kg": 98.32,
            "optimization_score": 0.85,
            "recommended_actions": [
                "Reduce HVAC temperature by 2°C during off-peak hours",
                "Implement smart lighting controls in zone B",
                "Schedule high-energy equipment during low-cost periods",
            ],
        }

        # Send callback if provided (webhook simulation)
        if callback_url:
            callback_data = {
                "job_id": job_id,
                "status": "completed",
                "result": jobs_storage[job_id]["result"],
            }

            requests.post(callback_url, json=callback_data, timeout=5)
            logger.info(f"Sent callback to {callback_url} for job {job_id}")

    except Exception as e:
        logger.error(f"Job processing failed: {e}")
        jobs_storage[job_id]["status"] = "failed"
        jobs_storage[job_id]["error"] = str(e)


@app.get("/health")
async def health_check():
    """Health check endpoint"""

    return {"status": "healthy", "service": "DSS F1 (Energy Optimization) Mock API"}


@app.post("/f1/jobs", response_model=F1JobResponse)
async def create_f1_job(
    job_request: F1JobRequest,
    background_tasks: BackgroundTasks,
    callback_url: str = None,
    api_key: str = Depends(get_api_key),
):
    """Create a new DSS F1 (Energy Optimization) analysis job"""

    job_id = str(uuid.uuid4())

    # Store job in memory
    job_data = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "building_id": job_request.building_id,
        "optimization_type": job_request.optimization_type,
        "parameters": job_request.parameters,
        "created_at": datetime.now().isoformat(),
        "callback_url": callback_url,
    }

    jobs_storage[job_id] = job_data

    # Start background processing
    background_tasks.add_task(simulate_job_processing, job_id, callback_url)

    logger.info(f"Created DSS F1 job {job_id} for building {job_request.building_id}")

    return F1JobResponse(
        job_id=job_id,
        status="pending",
        message=f"DSS F1 energy optimization job created for building {job_request.building_id} ({job_request.optimization_type})",
        created_at=job_data["created_at"],
    )


@app.get("/f1/jobs/{job_id}", response_model=F1JobStatus)
async def get_job_status(job_id: str, api_key: str = Depends(get_api_key)):
    """Get the status of a specific DSS F1 energy optimization job"""

    if job_id not in jobs_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    job_data = jobs_storage[job_id]

    return F1JobStatus(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data["progress"],
        result=job_data.get("result"),
        created_at=job_data["created_at"],
        completed_at=job_data.get("completed_at"),
    )


@app.get("/f1/jobs")
async def list_jobs(api_key: str = Depends(get_api_key)):
    """List all DSS F1 energy optimization jobs"""

    return {"jobs": list(jobs_storage.values())}


@app.delete("/f1/jobs/{job_id}")
async def cancel_job(job_id: str, api_key: str = Depends(get_api_key)):
    """Cancel a running DSS F1 energy optimization job"""

    if job_id not in jobs_storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )

    job_data = jobs_storage[job_id]

    if job_data["status"] in ["completed", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed or failed job",
        )

    jobs_storage[job_id]["status"] = "cancelled"
    logger.info(f"Cancelled DSS F1 job {job_id}")

    return {"message": f"Job {job_id} cancelled"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
