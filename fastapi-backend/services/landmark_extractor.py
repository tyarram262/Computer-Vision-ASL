"""
MediaPipe Landmark Extraction Service
Handles pose and hand detection from video frames
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Try to import MediaPipe, fall back to mock if not available
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    logger.warning("MediaPipe not available, using mock implementation")
    MEDIAPIPE_AVAILABLE = False
    
    # Mock MediaPipe classes for development
    class MockMediaPipe:
        class solutions:
            class hands:
                class Hands:
                    def __init__(self, **kwargs):
                        pass
                    def process(self, image):
                        return MockHandResults()
                    def close(self):
                        pass
                        
            class pose:
                class Pose:
                    def __init__(self, **kwargs):
                        pass
                    def process(self, image):
                        return MockPoseResults()
                    def close(self):
                        pass
                        
            class drawing_utils:
                pass
    
    class MockHandResults:
        def __init__(self):
            self.multi_hand_landmarks = None
    
    class MockPoseResults:
        def __init__(self):
            self.pose_landmarks = None
    
    mp = MockMediaPipe()


class LandmarkExtractor:
    """
    Service for extracting pose and hand landmarks from video frames using MediaPipe
    """
    
    def __init__(self, 
                 pose_confidence: float = 0.5,
                 pose_tracking_confidence: float = 0.5,
                 hand_confidence: float = 0.5,
                 hand_tracking_confidence: float = 0.5,
                 max_num_hands: int = 2):
        """
        Initialize MediaPipe landmark extractor
        
        Args:
            pose_confidence: Minimum confidence for pose detection
            pose_tracking_confidence: Minimum confidence for pose tracking
            hand_confidence: Minimum confidence for hand detection
            hand_tracking_confidence: Minimum confidence for hand tracking
            max_num_hands: Maximum number of hands to detect
        """
        self.pose_confidence = pose_confidence
        self.pose_tracking_confidence = pose_tracking_confidence
        self.hand_confidence = hand_confidence
        self.hand_tracking_confidence = hand_tracking_confidence
        self.max_num_hands = max_num_hands
        
        # Initialize MediaPipe solutions
        self.mp_hands = mp.solutions.hands
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Initialize processors
        self._hands_processor = None
        self._pose_processor = None
        
    def _initialize_processors(self):
        """Initialize MediaPipe processors with error handling"""
        try:
            if not MEDIAPIPE_AVAILABLE:
                logger.warning("Using mock MediaPipe processors for development")
            
            self._hands_processor = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self.max_num_hands,
                min_detection_confidence=self.hand_confidence,
                min_tracking_confidence=self.hand_tracking_confidence
            )
            
            self._pose_processor = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=self.pose_confidence,
                min_tracking_confidence=self.pose_tracking_confidence
            )
            
            status = "mock" if not MEDIAPIPE_AVAILABLE else "real"
            logger.info(f"MediaPipe processors initialized successfully ({status})")
            
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe processors: {e}")
            raise RuntimeError(f"MediaPipe initialization failed: {e}")
    
    def extract_from_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Extract landmarks from a single frame
        
        Args:
            frame: BGR image frame from OpenCV
            
        Returns:
            Dictionary containing pose and hand landmarks
        """
        if self._hands_processor is None or self._pose_processor is None:
            self._initialize_processors()
        
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame with MediaPipe
            hand_results = self._hands_processor.process(rgb_frame)
            pose_results = self._pose_processor.process(rgb_frame)
            
            # Extract landmarks
            frame_landmarks = {
                "pose": self._extract_pose_landmarks(pose_results),
                "hands": self._extract_hand_landmarks(hand_results)
            }
            
            return frame_landmarks
            
        except Exception as e:
            logger.error(f"Error extracting landmarks from frame: {e}")
            return {"pose": None, "hands": []}
    
    def _extract_pose_landmarks(self, pose_results) -> Optional[List[Dict[str, float]]]:
        """Extract pose landmarks from MediaPipe results"""
        if not pose_results.pose_landmarks:
            return None
        
        landmarks = []
        for landmark in pose_results.pose_landmarks.landmark:
            landmarks.append({
                "x": float(landmark.x),
                "y": float(landmark.y),
                "z": float(landmark.z),
                "visibility": float(landmark.visibility)
            })
        
        return landmarks
    
    def _extract_hand_landmarks(self, hand_results) -> List[List[Dict[str, float]]]:
        """Extract hand landmarks from MediaPipe results"""
        hands_landmarks = []
        
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                landmarks = []
                for landmark in hand_landmarks.landmark:
                    landmarks.append({
                        "x": float(landmark.x),
                        "y": float(landmark.y),
                        "z": float(landmark.z)
                    })
                hands_landmarks.append(landmarks)
        
        return hands_landmarks
    
    def extract_from_video(self, video_path: str) -> Dict[str, Any]:
        """
        Extract landmarks from entire video
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing video metadata and frame-by-frame landmarks
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        try:
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            video_data = {
                "fps": fps,
                "frame_count": frame_count,
                "duration": duration,
                "frames": []
            }
            
            # Initialize processors
            self._initialize_processors()
            
            frame_idx = 0
            processed_frames = 0
            
            logger.info(f"Processing video: {frame_count} frames at {fps} FPS")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extract landmarks from frame
                frame_landmarks = self.extract_from_frame(frame)
                
                # Add frame metadata
                frame_data = {
                    "frame_index": frame_idx,
                    "timestamp": frame_idx / fps if fps > 0 else 0,
                    **frame_landmarks
                }
                
                video_data["frames"].append(frame_data)
                
                frame_idx += 1
                processed_frames += 1
                
                # Log progress every 30 frames
                if processed_frames % 30 == 0:
                    logger.info(f"Processed {processed_frames}/{frame_count} frames")
            
            logger.info(f"Video processing complete: {processed_frames} frames processed")
            
            return video_data
            
        except Exception as e:
            logger.error(f"Error processing video {video_path}: {e}")
            raise
        
        finally:
            cap.release()
            self._cleanup_processors()
    
    def _cleanup_processors(self):
        """Clean up MediaPipe processors"""
        try:
            if self._hands_processor:
                self._hands_processor.close()
                self._hands_processor = None
            
            if self._pose_processor:
                self._pose_processor.close()
                self._pose_processor = None
                
            logger.debug("MediaPipe processors cleaned up")
            
        except Exception as e:
            logger.warning(f"Error cleaning up processors: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self._cleanup_processors()