"""
Landmark Data Storage and JSON Serialization Service
Handles saving and loading of processed landmark data
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LandmarkDataStorage:
    """
    Service for storing and retrieving landmark data with JSON serialization
    """
    
    def __init__(self, base_directory: str = "static"):
        """
        Initialize data storage service
        
        Args:
            base_directory: Base directory for storing files
        """
        self.base_directory = Path(base_directory)
        self.videos_dir = self.base_directory / "videos"
        self.data_dir = self.base_directory / "data"
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories"""
        try:
            self.videos_dir.mkdir(parents=True, exist_ok=True)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage directories ensured: {self.base_directory}")
        except Exception as e:
            logger.error(f"Failed to create storage directories: {e}")
            raise
    
    def save_landmark_data(self, sign_name: str, landmark_data: Dict[str, Any]) -> str:
        """
        Save landmark data as JSON file
        
        Args:
            sign_name: Name of the sign
            landmark_data: Processed landmark data from LandmarkExtractor
            
        Returns:
            Path to saved JSON file
        """
        try:
            # Create filename
            filename = f"{sign_name.lower()}_landmarks.json"
            file_path = self.data_dir / filename
            
            # Add metadata
            data_with_metadata = {
                "sign_name": sign_name,
                "processing_timestamp": self._get_current_timestamp(),
                **landmark_data
            }
            
            # Save to JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_with_metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Landmark data saved: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save landmark data for {sign_name}: {e}")
            raise
    
    def load_landmark_data(self, sign_name: str) -> Optional[Dict[str, Any]]:
        """
        Load landmark data from JSON file
        
        Args:
            sign_name: Name of the sign
            
        Returns:
            Landmark data dictionary or None if not found
        """
        try:
            filename = f"{sign_name.lower()}_landmarks.json"
            file_path = self.data_dir / filename
            
            if not file_path.exists():
                logger.warning(f"Landmark data not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"Landmark data loaded: {file_path}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load landmark data for {sign_name}: {e}")
            return None
    
    def save_video_file(self, sign_name: str, video_content: bytes) -> str:
        """
        Save uploaded video file
        
        Args:
            sign_name: Name of the sign
            video_content: Video file content as bytes
            
        Returns:
            Path to saved video file
        """
        try:
            filename = f"{sign_name.lower()}.mp4"
            file_path = self.videos_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(video_content)
            
            logger.info(f"Video file saved: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save video file for {sign_name}: {e}")
            raise
    
    def get_video_path(self, sign_name: str) -> Optional[str]:
        """
        Get path to video file
        
        Args:
            sign_name: Name of the sign
            
        Returns:
            Path to video file or None if not found
        """
        filename = f"{sign_name.lower()}.mp4"
        file_path = self.videos_dir / filename
        
        if file_path.exists():
            return str(file_path)
        return None
    
    def get_data_path(self, sign_name: str) -> Optional[str]:
        """
        Get path to landmark data file
        
        Args:
            sign_name: Name of the sign
            
        Returns:
            Path to data file or None if not found
        """
        filename = f"{sign_name.lower()}_landmarks.json"
        file_path = self.data_dir / filename
        
        if file_path.exists():
            return str(file_path)
        return None
    
    def list_available_signs(self) -> Dict[str, Dict[str, str]]:
        """
        List all available signs with their file paths
        
        Returns:
            Dictionary mapping sign names to their video and data paths
        """
        available_signs = {}
        
        try:
            # Get all video files
            if self.videos_dir.exists():
                for video_file in self.videos_dir.glob("*.mp4"):
                    sign_name = video_file.stem
                    
                    # Check if corresponding data file exists
                    data_file = self.data_dir / f"{sign_name}_landmarks.json"
                    
                    if data_file.exists():
                        available_signs[sign_name] = {
                            "video_path": str(video_file),
                            "data_path": str(data_file),
                            "video_url": f"/static/videos/{video_file.name}",
                            "data_url": f"/static/data/{data_file.name}"
                        }
            
            logger.info(f"Found {len(available_signs)} available signs")
            return available_signs
            
        except Exception as e:
            logger.error(f"Error listing available signs: {e}")
            return {}
    
    def delete_sign_data(self, sign_name: str) -> bool:
        """
        Delete both video and landmark data for a sign
        
        Args:
            sign_name: Name of the sign to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            deleted_files = []
            
            # Delete video file
            video_path = self.get_video_path(sign_name)
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                deleted_files.append(video_path)
            
            # Delete data file
            data_path = self.get_data_path(sign_name)
            if data_path and os.path.exists(data_path):
                os.remove(data_path)
                deleted_files.append(data_path)
            
            if deleted_files:
                logger.info(f"Deleted files for sign '{sign_name}': {deleted_files}")
                return True
            else:
                logger.warning(f"No files found to delete for sign '{sign_name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting sign data for '{sign_name}': {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage information
        """
        try:
            stats = {
                "base_directory": str(self.base_directory),
                "videos_directory": str(self.videos_dir),
                "data_directory": str(self.data_dir),
                "total_signs": 0,
                "video_files": 0,
                "data_files": 0,
                "storage_size_mb": 0
            }
            
            # Count files
            if self.videos_dir.exists():
                video_files = list(self.videos_dir.glob("*.mp4"))
                stats["video_files"] = len(video_files)
                
                # Calculate storage size
                total_size = sum(f.stat().st_size for f in video_files)
                stats["storage_size_mb"] = round(total_size / (1024 * 1024), 2)
            
            if self.data_dir.exists():
                data_files = list(self.data_dir.glob("*_landmarks.json"))
                stats["data_files"] = len(data_files)
            
            # Count complete signs (both video and data)
            available_signs = self.list_available_signs()
            stats["total_signs"] = len(available_signs)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()