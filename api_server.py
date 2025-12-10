#!/usr/bin/env python3
"""
FastAPI server for crawler and validators with WebSocket support for real-time updates.
"""

import asyncio
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from crawler import crawl_with_mitmproxy

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: List[WebSocket] = []


class CrawlRequest(BaseModel):
    url: str
    validators: List[str]
    max_pages: int = 4
    max_depth: int = 2


class StatusUpdate(BaseModel):
    type: str  # "crawling" | "validator" | "complete" | "error"
    stage: str  # "crawling" | validator name
    status: str  # "running" | "success" | "failed"
    message: Optional[str] = None
    details: Optional[dict] = None
    timestamp: str


async def broadcast_status(update: StatusUpdate):
    """Broadcast status update to all connected WebSocket clients."""
    message = update.model_dump_json()
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception as e:
            print(f"Error broadcasting to client: {e}")


async def run_validator(validator_name: str, script_name: str, args: List[str]) -> dict:
    """
    Run a validator script and capture its output.

    Args:
        validator_name: Display name of the validator
        script_name: Name of the validator script
        args: List of arguments to pass

    Returns:
        Dictionary with validation results
    """
    try:
        await broadcast_status(
            StatusUpdate(
                type="validator",
                stage=validator_name,
                status="running",
                message=f"Running {validator_name}...",
                timestamp=datetime.now().isoformat(),
            )
        )

        script_path = os.path.join("validators", script_name)
        cmd = ["python3", script_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        # Check if validation passed
        success = "PASSED ✓" in result.stdout or "Validation: PASSED" in result.stdout

        await broadcast_status(
            StatusUpdate(
                type="validator",
                stage=validator_name,
                status="success" if success else "failed",
                message=f"{validator_name} {'passed' if success else 'failed'}",
                details={"output": result.stdout, "passed": success},
                timestamp=datetime.now().isoformat(),
            )
        )

        return {
            "name": validator_name,
            "success": success,
            "output": result.stdout,
        }
    except Exception as e:
        error_msg = f"Error running {validator_name}: {str(e)}"
        await broadcast_status(
            StatusUpdate(
                type="validator",
                stage=validator_name,
                status="failed",
                message=error_msg,
                timestamp=datetime.now().isoformat(),
            )
        )
        return {
            "name": validator_name,
            "success": False,
            "output": error_msg,
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


@app.post("/api/crawl")
async def crawl_and_validate(request: CrawlRequest):
    """
    Start crawling and run validators.
    Returns immediately while broadcasting status updates via WebSocket.
    """
    # Start the crawl and validation process in the background
    asyncio.create_task(execute_crawl_and_validate(request))
    return {"status": "started", "message": "Crawl and validation started"}


async def execute_crawl_and_validate(request: CrawlRequest):
    """Execute crawl and validation with status updates."""
    try:
        # Broadcast crawling start
        await broadcast_status(
            StatusUpdate(
                type="crawling",
                stage="crawling",
                status="running",
                message=f"Starting crawl of {request.url}...",
                timestamp=datetime.now().isoformat(),
            )
        )

        # Run the crawler
        network_patterns = [
            r"https://.*\.adobedc\.net/.*",
            r"https://.*\.omtrdc\.net/.*",
            rf"{re.escape('https://www.adobe.com/experienceedge/')}",  # URLs starting with edge prefix
            r"marketingtech.*launch-",  # URLs containing marketingtech and launch-
        ]

        await crawl_with_mitmproxy(
            url=request.url,
            network_patterns=network_patterns,
            max_pages=request.max_pages,
            max_depth=request.max_depth,
            headless=True,
            output_file="ping_requests.json",
        )

        # Broadcast crawling complete
        await broadcast_status(
            StatusUpdate(
                type="crawling",
                stage="crawling",
                status="success",
                message="Crawling completed successfully",
                timestamp=datetime.now().isoformat(),
            )
        )

        # Define all available validators
        all_validators = {
            "required_fields": {
                "name": "Required Fields",
                "script": "required_fields.py",
                "args": ["requests.json"],
            },
            "ecid_consistency": {
                "name": "ECID Consistency",
                "script": "ecid_consistency.py",
                "args": ["payload", "requests.json"],
            },
            "page_view_integrity": {
                "name": "Page View Integrity",
                "script": "page_view_integrity.py",
                "args": ["requests.json"],
            },
            "no_duplicate_events": {
                "name": "No Duplicate Events",
                "script": "no_duplicate_events.py",
                "args": ["requests.json", "1.0"],
            },
            "payload_size": {
                "name": "Payload Size",
                "script": "payload_size.py",
                "args": ["requests.json", "32.0"],
            },
        }

        # Run selected validators
        results = []
        for validator_key in request.validators:
            if validator_key in all_validators:
                validator = all_validators[validator_key]
                result = await run_validator(
                    validator["name"],
                    validator["script"],
                    validator["args"],
                )
                results.append(result)

        # Broadcast completion
        passed = sum(1 for r in results if r["success"])
        total = len(results)

        await broadcast_status(
            StatusUpdate(
                type="complete",
                stage="complete",
                status="success",
                message=f"All tasks completed. {passed}/{total} validators passed.",
                details={
                    "results": results,
                    "passed": passed,
                    "total": total,
                },
                timestamp=datetime.now().isoformat(),
            )
        )

    except Exception as e:
        # Broadcast error
        await broadcast_status(
            StatusUpdate(
                type="error",
                stage="error",
                status="failed",
                message=f"Error: {str(e)}",
                timestamp=datetime.now().isoformat(),
            )
        )


@app.get("/api/validators")
async def get_validators():
    """Get list of available validators."""
    return {
        "validators": [
            {
                "id": "required_fields",
                "name": "Required Fields",
                "description": "Validates that all events contain required XDM fields",
            },
            {
                "id": "ecid_consistency",
                "name": "ECID Consistency",
                "description": "Validates that all requests share the same ECID",
            },
            {
                "id": "page_view_integrity",
                "name": "Page View Integrity",
                "description": "Validates exactly one page view event per page",
            },
            {
                "id": "no_duplicate_events",
                "name": "No Duplicate Events",
                "description": "Validates no duplicate events within time window",
            },
            {
                "id": "payload_size",
                "name": "Payload Size",
                "description": "Validates payload sizes are under limit (32 KB)",
            },
        ]
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
