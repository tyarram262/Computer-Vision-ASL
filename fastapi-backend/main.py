"""
FastAPI Backend for ASL Real-time Learning System
Handles video preprocessing and AI feedback generation
"""

import os
import json
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
import logging
from dotenv import load_dotenv

# Import services
from services.video_processor import VideoProcessor
from services.data_storage import LandmarkDataStorage
from services.landmark_extractor import LandmarkExtractor
from services.bedrock_service import BedrockService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ASL Real-time Learning API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
storage_service = LandmarkDataStorage()
video_processor = VideoProcessor(storage_service)
bedrock_service = BedrockService()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class FeedbackRequest(BaseModel):
    sign: str
    error_code: str
    user_landmarks: Optional[Dict] = None
    target_landmarks: Optional[Dict] = None
    user_id: Optional[str] = "default"

class FeedbackResponse(BaseModel):
    success: bool
    feedback: str
    error_code: str
    sign: str
    timestamp: str
    source: str
    cached: bool = False

class RateLimitStatus(BaseModel):
    user_id: str
    is_rate_limited: bool
    limit_reason: str
    global_limits: Dict
    user_limits: Dict

class VideoProcessingResult(BaseModel):
    success: bool
    message: str
    video_path: Optional[str] = None
    data_path: Optional[str] = None
    frame_count: Optional[int] = None



@app.get("/")
async def root():
    return {"message": "ASL Form Correction API", "status": "running"}

@app.post("/upload_video")
async def upload_video(file: UploadFile = File(...), sign_name: str = Form(...)):
    """
    Upload and process a target video for ASL sign analysis
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Read file content
        content = await file.read()
        
        # Process video using VideoProcessor service
        result = video_processor.process_video(sign_name, content, file.filename or "video.mp4")
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "message": result["message"],
            "sign_name": result["sign_name"],
            "video_url": result["video_url"],
            "data_url": result["data_url"],
            "properties": result["properties"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_feedback")
async def get_feedback(request: FeedbackRequest):
    """
    Generate AI-powered feedback for ASL sign learning with rate limiting and caching
    """
    try:
        # Extract user identifier from request or use default
        user_id = request.user_id or "default"
        
        # Use the BedrockService to get feedback with user tracking
        feedback_response = bedrock_service.get_feedback(request.sign, request.error_code, user_id)
        
        return {
            "success": feedback_response.success,
            "feedback": feedback_response.feedback,
            "sign": feedback_response.sign,
            "error_code": feedback_response.error_code,
            "timestamp": feedback_response.timestamp.isoformat(),
            "source": feedback_response.source,
            "cached": feedback_response.cached
        }
        
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        return {
            "success": False,
            "feedback": "Keep practicing - you're doing great!",
            "error": str(e),
            "sign": request.sign,
            "error_code": request.error_code,
            "source": "error_fallback"
        }

@app.get("/available_signs")
async def get_available_signs():
    """
    Get list of available processed signs
    """
    try:
        available_signs = storage_service.list_available_signs()
        
        # Convert to expected format
        signs_list = []
        for sign_name, paths in available_signs.items():
            signs_list.append({
                "name": sign_name,
                "video_url": paths["video_url"],
                "data_url": paths["data_url"]
            })
        
        return {
            "success": True,
            "signs": signs_list,
            "count": len(signs_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting available signs: {e}")
        return {
            "success": False,
            "signs": [],
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """
    Health check endpoint with system status
    """
    try:
        # Get Bedrock service status
        bedrock_status = bedrock_service.get_service_status()
        
        # Get storage statistics
        storage_stats = storage_service.get_storage_stats()
        
        return {
            "status": "healthy",
            "message": "ASL Real-time Learning API is running",
            "bedrock": bedrock_status,
            "storage": storage_stats,
            "endpoints": [
                "/upload_video",
                "/get_feedback", 
                "/available_signs",
                "/reprocess_video/{sign_name}",
                "/static/videos/",
                "/static/data/",
                "/bedrock/status",
                "/bedrock/cache/clear",
                "/bedrock/cache/stats",
                "/bedrock/rate_limits/{user_id}",
                "/bedrock/statistics/reset",
                "/bedrock/error_codes"
            ]
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }

@app.post("/reprocess_video/{sign_name}")
async def reprocess_video(sign_name: str):
    """
    Reprocess an existing video file
    """
    try:
        result = video_processor.reprocess_video(sign_name)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "success": True,
            "message": result["message"],
            "sign_name": result["sign_name"],
            "video_url": result["video_url"],
            "data_url": result["data_url"],
            "properties": result["properties"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/signs/{sign_name}")
async def delete_sign(sign_name: str):
    """
    Delete a sign and its associated data
    """
    try:
        success = storage_service.delete_sign_data(sign_name)
        
        if success:
            return {
                "success": True,
                "message": f"Sign '{sign_name}' deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Sign '{sign_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting sign: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bedrock/status")
async def get_bedrock_status():
    """
    Get detailed Bedrock service status and configuration
    """
    try:
        status = bedrock_service.get_service_status()
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        logger.error(f"Error getting Bedrock status: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/bedrock/cache/clear")
async def clear_bedrock_cache():
    """
    Clear all cached Bedrock responses
    """
    try:
        cleared_count = bedrock_service.clear_cache()
        return {
            "success": True,
            "message": f"Cleared {cleared_count} cached responses"
        }
    except Exception as e:
        logger.error(f"Error clearing Bedrock cache: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/bedrock/cache/stats")
async def get_bedrock_cache_stats():
    """
    Get detailed cache statistics
    """
    try:
        stats = bedrock_service.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/bedrock/rate_limits/{user_id}")
async def get_rate_limit_status(user_id: str = "default"):
    """
    Get detailed rate limiting status for a specific user
    """
    try:
        status = bedrock_service.get_rate_limit_status(user_id)
        return {
            "success": True,
            "rate_limit_status": status
        }
    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/bedrock/statistics/reset")
async def reset_bedrock_statistics():
    """
    Reset request statistics and return previous values
    """
    try:
        old_stats = bedrock_service.reset_statistics()
        return {
            "success": True,
            "message": "Statistics reset successfully",
            "previous_statistics": old_stats
        }
    except Exception as e:
        logger.error(f"Error resetting statistics: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/bedrock/error_codes")
async def get_error_code_mapping():
    """
    Get the complete error code to prompt mapping for debugging
    """
    try:
        mapping = bedrock_service.get_error_code_mapping()
        return {
            "success": True,
            "error_code_mapping": mapping
        }
    except Exception as e:
        logger.error(f"Error getting error code mapping: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)