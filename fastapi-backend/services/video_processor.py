"""
Video Processing Service
Handles video upload, validation, and processing pipeline
"""

import cv2
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from .landmark_extractor import LandmarkExtractor
from .data_storage import LandmarkDataStorage

logger = logging.getLogger(__name__)


class VideoProcessor:
    """
    Service for processing uploaded videos and extracting landmarks
    """
    
    def __init__(self, storage_service: Optional[LandmarkDataStorage] = None):
        """
        Initialize video processor
        
        Args:
            storage_service: Data storage service instance
        """
        self.storage = storage_service or LandmarkDataStorage()
        self.landmark_extractor = LandmarkExtractor()
        
        # Supported video formats
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        
        # Video validation limits
        self.max_file_size_mb = 100
        self.max_duration_seconds = 30
        self.min_duration_seconds = 0.5
    
    def validate_video_file(self, file_content: bytes, filename: str) -> Tuple[bool, str]:
        """
        Validate uploaded video file
        
        Args:
            file_content: Video file content as bytes
            filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file size
            file_size_mb = len(file_content) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return False, f"File size ({file_size_mb:.1f}MB) exceeds limit ({self.max_file_size_mb}MB)"
            
            # Check file extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                return False, f"Unsupported format '{file_ext}'. Supported: {', '.join(self.supported_formats)}"
            
            return True, "Valid video file"
            
        except Exception as e:
            logger.error(f"Error validating video file: {e}")
            return False, f"Validation error: {str(e)}"
    
    def validate_video_properties(self, video_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate video properties using OpenCV
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (is_valid, error_message, video_properties)
        """
        properties = {}
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return False, "Could not open video file", properties
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            properties = {
                "fps": fps,
                "frame_count": frame_count,
                "width": width,
                "height": height,
                "duration": duration
            }
            
            cap.release()
            
            # Validate duration
            if duration < self.min_duration_seconds:
                return False, f"Video too short ({duration:.1f}s). Minimum: {self.min_duration_seconds}s", properties
            
            if duration > self.max_duration_seconds:
                return False, f"Video too long ({duration:.1f}s). Maximum: {self.max_duration_seconds}s", properties
            
            # Validate resolution
            if width < 240 or height < 240:
                return False, f"Resolution too low ({width}x{height}). Minimum: 240x240", properties
            
            # Validate frame rate
            if fps < 10:
                return False, f"Frame rate too low ({fps:.1f} FPS). Minimum: 10 FPS", properties
            
            return True, "Valid video properties", properties
            
        except Exception as e:
            logger.error(f"Error validating video properties: {e}")
            return False, f"Property validation error: {str(e)}", properties
    
    def process_video(self, sign_name: str, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Complete video processing pipeline
        
        Args:
            sign_name: Name of the ASL sign
            file_content: Video file content as bytes
            filename: Original filename
            
        Returns:
            Processing result dictionary
        """
        try:
            logger.info(f"Starting video processing for sign: {sign_name}")
            
            # Step 1: Validate file
            is_valid, validation_message = self.validate_video_file(file_content, filename)
            if not is_valid:
                return {
                    "success": False,
                    "error": f"File validation failed: {validation_message}",
                    "stage": "file_validation"
                }
            
            # Step 2: Save video file
            video_path = self.storage.save_video_file(sign_name, file_content)
            
            # Step 3: Validate video properties
            is_valid, prop_message, properties = self.validate_video_properties(video_path)
            if not is_valid:
                # Clean up saved file
                if os.path.exists(video_path):
                    os.remove(video_path)
                return {
                    "success": False,
                    "error": f"Video validation failed: {prop_message}",
                    "stage": "property_validation",
                    "properties": properties
                }
            
            # Step 4: Extract landmarks
            logger.info(f"Extracting landmarks from video: {video_path}")
            landmark_data = self.landmark_extractor.extract_from_video(video_path)
            
            # Step 5: Save landmark data
            data_path = self.storage.save_landmark_data(sign_name, landmark_data)
            
            # Step 6: Prepare result
            result = {
                "success": True,
                "message": f"Video processed successfully. Extracted landmarks from {landmark_data['frame_count']} frames.",
                "sign_name": sign_name,
                "video_path": video_path,
                "data_path": data_path,
                "video_url": f"/static/videos/{sign_name.lower()}.mp4",
                "data_url": f"/static/data/{sign_name.lower()}_landmarks.json",
                "properties": {
                    **properties,
                    "processed_frames": len(landmark_data["frames"])
                }
            }
            
            logger.info(f"Video processing completed successfully for sign: {sign_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing video for sign '{sign_name}': {e}")
            
            # Clean up any partial files
            try:
                video_path = self.storage.get_video_path(sign_name)
                if video_path and os.path.exists(video_path):
                    os.remove(video_path)
                
                data_path = self.storage.get_data_path(sign_name)
                if data_path and os.path.exists(data_path):
                    os.remove(data_path)
            except:
                pass  # Ignore cleanup errors
            
            return {
                "success": False,
                "error": f"Processing failed: {str(e)}",
                "stage": "landmark_extraction"
            }
    
    def reprocess_video(self, sign_name: str) -> Dict[str, Any]:
        """
        Reprocess an existing video file
        
        Args:
            sign_name: Name of the ASL sign
            
        Returns:
            Processing result dictionary
        """
        try:
            video_path = self.storage.get_video_path(sign_name)
            if not video_path or not os.path.exists(video_path):
                return {
                    "success": False,
                    "error": f"Video file not found for sign: {sign_name}",
                    "stage": "file_lookup"
                }
            
            logger.info(f"Reprocessing video for sign: {sign_name}")
            
            # Validate video properties
            is_valid, prop_message, properties = self.validate_video_properties(video_path)
            if not is_valid:
                return {
                    "success": False,
                    "error": f"Video validation failed: {prop_message}",
                    "stage": "property_validation",
                    "properties": properties
                }
            
            # Extract landmarks
            landmark_data = self.landmark_extractor.extract_from_video(video_path)
            
            # Save landmark data
            data_path = self.storage.save_landmark_data(sign_name, landmark_data)
            
            result = {
                "success": True,
                "message": f"Video reprocessed successfully. Extracted landmarks from {landmark_data['frame_count']} frames.",
                "sign_name": sign_name,
                "video_path": video_path,
                "data_path": data_path,
                "video_url": f"/static/videos/{sign_name.lower()}.mp4",
                "data_url": f"/static/data/{sign_name.lower()}_landmarks.json",
                "properties": {
                    **properties,
                    "processed_frames": len(landmark_data["frames"])
                }
            }
            
            logger.info(f"Video reprocessing completed for sign: {sign_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error reprocessing video for sign '{sign_name}': {e}")
            return {
                "success": False,
                "error": f"Reprocessing failed: {str(e)}",
                "stage": "landmark_extraction"
            }