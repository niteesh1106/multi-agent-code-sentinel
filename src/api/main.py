"""
FastAPI application for the Multi-Agent Code Review System.
"""
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import hmac
import hashlib
from typing import Dict, Any, Optional
import json
from loguru import logger
from datetime import datetime, timezone

from src.core.config import settings
from src.core.orchestrator import Orchestrator
from src.api.models import (
    WebhookPayload, 
    ReviewRequest, 
    ReviewResponse,
    HealthResponse
)
from src.api.github_handler import GitHubHandler

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent Code Review System",
    description="AI-powered code review system using multiple specialized agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
orchestrator = Orchestrator()
github_handler = GitHubHandler(settings.github_token)

# In-memory storage for review status (use Redis in production)
review_status: Dict[str, Dict[str, Any]] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("Starting Multi-Agent Code Review System...")
    logger.info(f"Agents enabled: {list(orchestrator.agents.keys())}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    await orchestrator.shutdown()
    logger.info("Shutting down Multi-Agent Code Review System...")


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "service": "Multi-Agent Code Review System",
        "version": "1.0.0",
        "agents": list(orchestrator.agents.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # Check if all components are working
    agents_status = {name: "active" for name in orchestrator.agents.keys()}
    
    return {
        "status": "healthy",
        "service": "Multi-Agent Code Review System",
        "version": "1.0.0",
        "agents": list(orchestrator.agents.keys()),
        "agents_status": agents_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/api/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle GitHub webhook events.
    
    This endpoint receives webhook events from GitHub when:
    - A pull request is opened
    - A pull request is updated
    - New commits are pushed to a PR
    """
    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    if settings.github_webhook_secret and signature:
        body = await request.body()
        expected_signature = "sha256=" + hmac.new(
            settings.github_webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook payload
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")
    
    logger.info(f"Received GitHub webhook: {event_type}")
    
    # Handle pull request events
    if event_type == "pull_request":
        action = payload.get("action")
        if action in ["opened", "synchronize", "reopened"]:
            pr_data = payload["pull_request"]
            repo_data = payload["repository"]
            
            # Start review in background
            review_id = f"{repo_data['full_name']}/pull/{pr_data['number']}"
            review_status[review_id] = {
                "status": "pending",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "pr_number": pr_data["number"],
                "repo": repo_data["full_name"]
            }
            
            background_tasks.add_task(
                process_pull_request,
                pr_data,
                repo_data,
                review_id
            )
            
            return {
                "status": "accepted",
                "review_id": review_id,
                "message": f"Review started for PR #{pr_data['number']}"
            }
    
    return {"status": "ignored", "reason": "Event not supported"}


@app.post("/api/review", response_model=ReviewResponse)
async def manual_review(review_request: ReviewRequest, background_tasks: BackgroundTasks):
    """
    Manually trigger a code review for a pull request.
    
    This endpoint allows manual triggering of reviews without webhooks.
    """
    review_id = f"{review_request.repo}/pull/{review_request.pr_number}"
    
    # Check if review already in progress
    if review_id in review_status and review_status[review_id]["status"] == "in_progress":
        raise HTTPException(
            status_code=409,
            detail="Review already in progress for this PR"
        )
    
    # Initialize review status
    review_status[review_id] = {
        "status": "pending",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "pr_number": review_request.pr_number,
        "repo": review_request.repo
    }
    
    # Start review in background
    background_tasks.add_task(
        process_manual_review,
        review_request,
        review_id
    )
    
    return {
        "review_id": review_id,
        "status": "pending",
        "message": f"Review started for {review_request.repo} PR #{review_request.pr_number}",
        "started_at": review_status[review_id]["started_at"]
    }


@app.get("/api/review/{review_id:path}")
async def get_review_status(review_id: str):
    """Get the status of a review."""
    if review_id not in review_status:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return review_status[review_id]


async def process_pull_request(pr_data: Dict, repo_data: Dict, review_id: str):
    """Process a pull request review (background task)."""
    try:
        review_status[review_id]["status"] = "in_progress"
        
        # Get PR files
        files_data = await github_handler.get_pr_files(
            repo_data["full_name"],
            pr_data["number"]
        )
        
        # Run orchestrator
        result = await orchestrator.review_pull_request(
            pr_number=pr_data["number"],
            repo_name=repo_data["full_name"],
            files_data=files_data
        )
        
        # Post comment to GitHub
        comment_body = result.to_markdown()
        await github_handler.post_pr_comment(
            repo_data["full_name"],
            pr_data["number"],
            comment_body
        )
        
        # Update status
        review_status[review_id].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "summary": result.summary,
            "total_issues": result.total_issues,
            "critical_issues": result.critical_issues
        })
        
        logger.info(f"Review completed for {review_id}")
        
    except Exception as e:
        logger.error(f"Error processing PR {review_id}: {e}")
        review_status[review_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat()
        })


async def process_manual_review(review_request: ReviewRequest, review_id: str):
    """Process a manual review request (background task)."""
    try:
        review_status[review_id]["status"] = "in_progress"
        
        # Get PR files
        files_data = await github_handler.get_pr_files(
            review_request.repo,
            review_request.pr_number
        )
        
        # Run orchestrator
        result = await orchestrator.review_pull_request(
            pr_number=review_request.pr_number,
            repo_name=review_request.repo,
            files_data=files_data
        )
        
        # Post comment if requested
        if review_request.post_comment:
            comment_body = result.to_markdown()
            await github_handler.post_pr_comment(
                review_request.repo,
                review_request.pr_number,
                comment_body
            )
        
        # Update status
        review_status[review_id].update({
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "summary": result.summary,
            "total_issues": result.total_issues,
            "critical_issues": result.critical_issues,
            "report": result.to_dict() if review_request.include_details else None
        })
        
        logger.info(f"Manual review completed for {review_id}")
        
    except Exception as e:
        logger.error(f"Error processing manual review {review_id}: {e}")
        review_status[review_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat()
        })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )