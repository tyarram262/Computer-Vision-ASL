"""
AWS Bedrock Service for AI-powered ASL feedback generation
Handles authentication, rate limiting, caching, and error processing
"""

import os
import json
import time
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class FeedbackResponse:
    """Structured feedback response format"""
    success: bool
    feedback: str
    error_code: str
    sign: str
    timestamp: datetime
    source: str  # 'bedrock' or 'fallback'
    cached: bool = False

class BedrockService:
    """
    AWS Bedrock integration service for generating intelligent ASL feedback
    """
    
    def __init__(self):
        self.client = None
        self.region = os.getenv('AWS_REGION', 'us-west-2')
        self.model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        self.enabled = os.getenv('USE_BEDROCK', 'true').lower() == 'true'
        
        # Enhanced rate limiting configuration
        self.max_requests_per_minute = int(os.getenv('BEDROCK_MAX_REQUESTS_PER_MINUTE', '10'))
        self.max_requests_per_hour = int(os.getenv('BEDROCK_MAX_REQUESTS_PER_HOUR', '100'))
        self.request_timestamps = []
        self.hourly_request_timestamps = []
        
        # Per-user rate limiting (using IP or session)
        self.user_request_limits = {}
        self.max_requests_per_user_per_minute = int(os.getenv('BEDROCK_MAX_REQUESTS_PER_USER_PER_MINUTE', '3'))
        
        # Request tracking for analytics
        self.request_stats = {
            'total_requests': 0,
            'bedrock_requests': 0,
            'fallback_requests': 0,
            'cached_requests': 0,
            'rate_limited_requests': 0
        }
        
        # Caching configuration
        self.cache = {}
        self.cache_ttl_seconds = int(os.getenv('BEDROCK_CACHE_TTL_SECONDS', '300'))  # 5 minutes
        self.max_cache_size = int(os.getenv('BEDROCK_MAX_CACHE_SIZE', '100'))
        
        # Enhanced error code to prompt mapping with detailed context
        self.error_prompts = {
            # Hand position errors
            "THUMB_LOW": "User is learning ASL sign '{sign}' and their thumb is positioned too low compared to the target. The thumb should be higher for proper hand shape.",
            "THUMB_HIGH": "User is learning ASL sign '{sign}' and their thumb is positioned too high compared to the target. The thumb needs to be lowered slightly.",
            "THUMB_ANGLE": "User is learning ASL sign '{sign}' and their thumb angle is incorrect. The thumb orientation needs adjustment.",
            
            # Finger positioning errors
            "FINGERS_SPREAD": "User is learning ASL sign '{sign}' and their fingers are too spread apart. The fingers should be closer together for this sign.",
            "FINGERS_CLOSED": "User is learning ASL sign '{sign}' and their fingers are too closed together. The fingers need more separation.",
            "FINGERS_CURVED": "User is learning ASL sign '{sign}' and their fingers are too curved. The fingers should be straighter.",
            "FINGERS_STRAIGHT": "User is learning ASL sign '{sign}' and their fingers are too straight. The fingers should have more natural curve.",
            
            # Hand orientation and angle errors
            "HAND_ANGLE": "User is learning ASL sign '{sign}' and their hand angle is incorrect. The hand orientation needs to be adjusted.",
            "HAND_ROTATION": "User is learning ASL sign '{sign}' and their hand rotation is incorrect. The palm direction should match the target.",
            "WRIST_BEND": "User is learning ASL sign '{sign}' and their wrist is bent incorrectly. The wrist should be more neutral.",
            "WRIST_ANGLE": "User is learning ASL sign '{sign}' and their wrist angle needs adjustment for proper form.",
            
            # Arm and elbow positioning
            "ARM_POSITION": "User is learning ASL sign '{sign}' and their arm position needs adjustment. The arm should be repositioned.",
            "ELBOW_WIDE": "User is learning ASL sign '{sign}' and their elbow angle is too wide. The elbow should be closer to the body.",
            "ELBOW_NARROW": "User is learning ASL sign '{sign}' and their elbow angle is too narrow. The elbow needs more space from the body.",
            "ELBOW_HEIGHT": "User is learning ASL sign '{sign}' and their elbow height is incorrect. The elbow position should be adjusted vertically.",
            
            # Movement and timing errors
            "TIMING_FAST": "User is learning ASL sign '{sign}' and their movement is too fast. The sign should be performed more slowly.",
            "TIMING_SLOW": "User is learning ASL sign '{sign}' and their movement is too slow. The sign can be performed more quickly.",
            "MOVEMENT_JERKY": "User is learning ASL sign '{sign}' and their movement is too jerky. The motion should be smoother.",
            "MOVEMENT_INCOMPLETE": "User is learning ASL sign '{sign}' and their movement is incomplete. The full range of motion is needed.",
            
            # Overall form errors
            "GENERAL_FORM": "User is learning ASL sign '{sign}' and their overall form needs improvement. Multiple aspects need adjustment.",
            "HAND_SHAPE": "User is learning ASL sign '{sign}' and their hand shape is not quite right. The finger configuration needs refinement.",
            "SPATIAL_POSITION": "User is learning ASL sign '{sign}' and their hand is in the wrong spatial location. The position relative to the body needs adjustment."
        }
        
        # Enhanced fallback messages for when Bedrock is unavailable
        self.fallback_messages = {
            # Hand position fallbacks
            "THUMB_LOW": "Great effort! Try lifting your thumb just a bit higher - you're almost there!",
            "THUMB_HIGH": "Nice work! Lower your thumb slightly for better form.",
            "THUMB_ANGLE": "Good job! Adjust your thumb angle to match the target position.",
            
            # Finger positioning fallbacks
            "FINGERS_SPREAD": "Good job! Bring your fingers a little closer together.",
            "FINGERS_CLOSED": "You're doing well! Spread your fingers out just a touch more.",
            "FINGERS_CURVED": "Nice effort! Try straightening your fingers a bit more.",
            "FINGERS_STRAIGHT": "Great work! Let your fingers curve more naturally.",
            
            # Hand orientation fallbacks
            "HAND_ANGLE": "Almost perfect! Adjust your hand angle slightly.",
            "HAND_ROTATION": "Keep it up! Rotate your hand slightly to match the target position.",
            "WRIST_BEND": "Nice effort! Keep your wrist more relaxed and natural.",
            "WRIST_ANGLE": "Good progress! Adjust your wrist angle for better form.",
            
            # Arm and elbow fallbacks
            "ARM_POSITION": "Great start! Try adjusting your arm position a bit.",
            "ELBOW_WIDE": "Good progress! Bring your elbow in a little closer to your body.",
            "ELBOW_NARROW": "You're getting there! Open up your elbow angle just a bit more.",
            "ELBOW_HEIGHT": "Nice work! Adjust your elbow height to match the target.",
            
            # Movement and timing fallbacks
            "TIMING_FAST": "Excellent effort! Try slowing down your movement just a little.",
            "TIMING_SLOW": "Nice work! You can speed up your movement slightly.",
            "MOVEMENT_JERKY": "Good job! Try to make your movement smoother and more fluid.",
            "MOVEMENT_INCOMPLETE": "Great start! Complete the full range of motion for this sign.",
            
            # Overall form fallbacks
            "GENERAL_FORM": "You're making progress! Keep practicing and you'll get it!",
            "HAND_SHAPE": "Nice effort! Refine your hand shape to match the target.",
            "SPATIAL_POSITION": "Good work! Adjust your hand position relative to your body."
        }
        
        # Initialize Bedrock client if enabled
        if self.enabled:
            self._initialize_client()
    
    def _initialize_client(self) -> bool:
        """Initialize AWS Bedrock client with proper authentication"""
        try:
            # Check if we have the required credentials
            aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            
            if not aws_access_key or not aws_secret_key:
                logger.info("AWS credentials not configured, Bedrock will be disabled")
                self.enabled = False
                return False
            
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=self.region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                aws_session_token=os.getenv('AWS_SESSION_TOKEN')
            )
            
            # Test the connection with a simple call
            self._test_connection()
            logger.info("AWS Bedrock client initialized successfully")
            return True
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            self.enabled = False
            return False
        except ClientError as e:
            logger.error(f"AWS Bedrock client initialization failed: {e}")
            self.enabled = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing Bedrock client: {e}")
            self.enabled = False
            return False
    
    def _test_connection(self) -> None:
        """Test Bedrock connection with a minimal request"""
        if not self.client:
            raise Exception("Bedrock client not initialized")
        
        # For bedrock-runtime, we can't easily test without making a model call
        # So we'll just verify the client was created successfully
        # The actual connection will be tested when making the first request
        pass
    
    def _generate_cache_key(self, sign: str, error_code: str) -> str:
        """Generate cache key for feedback requests"""
        key_string = f"{sign}:{error_code}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_rate_limited(self, user_id: str = "default") -> Tuple[bool, str]:
        """
        Check if we're hitting rate limits (global or per-user)
        
        Returns:
            Tuple of (is_limited, reason)
        """
        now = time.time()
        
        # Clean up old timestamps
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        self.hourly_request_timestamps = [ts for ts in self.hourly_request_timestamps if now - ts < 3600]
        
        # Check global per-minute limit
        if len(self.request_timestamps) >= self.max_requests_per_minute:
            return True, "global_minute_limit"
        
        # Check global per-hour limit
        if len(self.hourly_request_timestamps) >= self.max_requests_per_hour:
            return True, "global_hour_limit"
        
        # Check per-user limits
        if user_id not in self.user_request_limits:
            self.user_request_limits[user_id] = []
        
        # Clean up old user timestamps
        self.user_request_limits[user_id] = [
            ts for ts in self.user_request_limits[user_id] if now - ts < 60
        ]
        
        # Check per-user per-minute limit
        if len(self.user_request_limits[user_id]) >= self.max_requests_per_user_per_minute:
            return True, "user_minute_limit"
        
        return False, ""
    
    def _add_request_timestamp(self, user_id: str = "default") -> None:
        """Add current timestamp to rate limiting trackers"""
        now = time.time()
        self.request_timestamps.append(now)
        self.hourly_request_timestamps.append(now)
        
        # Add to user-specific tracking
        if user_id not in self.user_request_limits:
            self.user_request_limits[user_id] = []
        self.user_request_limits[user_id].append(now)
        
        # Update stats
        self.request_stats['total_requests'] += 1
    
    def _get_cached_feedback(self, cache_key: str) -> Optional[FeedbackResponse]:
        """Retrieve cached feedback if available and not expired"""
        if cache_key not in self.cache:
            return None
        
        cached_item = self.cache[cache_key]
        
        # Check if cache entry has expired
        if datetime.now() - cached_item['timestamp'] > timedelta(seconds=self.cache_ttl_seconds):
            del self.cache[cache_key]
            return None
        
        # Return cached response
        response = cached_item['response']
        response.cached = True
        return response
    
    def _cache_feedback(self, cache_key: str, response: FeedbackResponse) -> None:
        """Cache feedback response"""
        # Implement LRU-style cache eviction if at max size
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]
        
        self.cache[cache_key] = {
            'response': response,
            'timestamp': datetime.now()
        }
    
    def _create_prompt(self, sign: str, error_code: str) -> str:
        """Create AI prompt based on sign and error code"""
        base_prompt = self.error_prompts.get(
            error_code, 
            f"User is learning ASL sign '{sign}' and needs guidance."
        ).format(sign=sign)
        
        return f"""You are an encouraging ASL instructor. {base_prompt}

Provide a short, positive, and specific tip (1-2 sentences) to help them improve. 
Be encouraging and focus on what they can do better. Keep it under 50 words.
Use encouraging language and be specific about the correction needed.

Examples:
- "Great effort! Try lifting your thumb just a bit higher - you're almost there!"
- "Nice work! Relax your fingers slightly and let them flow more naturally."
- "You're doing well! Just adjust your wrist angle slightly and you'll nail it!"
"""
    
    def _call_bedrock(self, prompt: str) -> str:
        """Make actual call to AWS Bedrock"""
        if not self.client:
            raise Exception("Bedrock client not initialized")
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text'].strip()
    
    def get_feedback(self, sign: str, error_code: str, user_id: str = "default") -> FeedbackResponse:
        """
        Generate AI feedback for ASL sign learning
        
        Args:
            sign: Name of the ASL sign being learned
            error_code: Specific error code identifying the issue
            
        Returns:
            FeedbackResponse with structured feedback data
        """
        timestamp = datetime.now()
        
        # Generate cache key
        cache_key = self._generate_cache_key(sign, error_code)
        
        # Check cache first
        cached_response = self._get_cached_feedback(cache_key)
        if cached_response:
            self.request_stats['cached_requests'] += 1
            logger.info(f"Returning cached feedback for {sign}:{error_code}")
            return cached_response
        
        # Check rate limiting first (applies to all requests, not just Bedrock)
        is_limited, limit_reason = self._is_rate_limited(user_id)
        if is_limited:
            logger.warning(f"Rate limit exceeded ({limit_reason}), using fallback for {sign}:{error_code}")
            self.request_stats['rate_limited_requests'] += 1
            response = FeedbackResponse(
                success=True,
                feedback=self.fallback_messages.get(error_code, "Keep practicing - you're doing great!"),
                error_code=error_code,
                sign=sign,
                timestamp=timestamp,
                source=f'fallback_rate_limited_{limit_reason}'
            )
            self._cache_feedback(cache_key, response)
            return response
        
        # Track this request for rate limiting
        self._add_request_timestamp(user_id)
        
        # Check if Bedrock is enabled and available
        if not self.enabled or not self.client:
            logger.info("Bedrock disabled or unavailable, using fallback feedback")
            self.request_stats['fallback_requests'] += 1
            response = FeedbackResponse(
                success=True,
                feedback=self.fallback_messages.get(error_code, "Keep practicing - you're doing great!"),
                error_code=error_code,
                sign=sign,
                timestamp=timestamp,
                source='fallback'
            )
            self._cache_feedback(cache_key, response)
            return response
        
        # Try to get AI feedback from Bedrock
        try:
            
            prompt = self._create_prompt(sign, error_code)
            feedback_text = self._call_bedrock(prompt)
            
            self.request_stats['bedrock_requests'] += 1
            response = FeedbackResponse(
                success=True,
                feedback=feedback_text,
                error_code=error_code,
                sign=sign,
                timestamp=timestamp,
                source='bedrock'
            )
            
            # Cache the successful response
            self._cache_feedback(cache_key, response)
            
            logger.info(f"Generated Bedrock feedback for {sign}:{error_code}")
            return response
            
        except ClientError as e:
            logger.error(f"AWS Bedrock error for {sign}:{error_code}: {e}")
            self.request_stats['fallback_requests'] += 1
            response = FeedbackResponse(
                success=False,
                feedback=self.fallback_messages.get(error_code, "Keep practicing - you're doing great!"),
                error_code=error_code,
                sign=sign,
                timestamp=timestamp,
                source='fallback_bedrock_error'
            )
            self._cache_feedback(cache_key, response)
            return response
            
        except Exception as e:
            logger.error(f"Unexpected error generating feedback for {sign}:{error_code}: {e}")
            self.request_stats['fallback_requests'] += 1
            response = FeedbackResponse(
                success=False,
                feedback=self.fallback_messages.get(error_code, "Keep practicing - you're doing great!"),
                error_code=error_code,
                sign=sign,
                timestamp=timestamp,
                source='fallback_unexpected_error'
            )
            self._cache_feedback(cache_key, response)
            return response
    
    def get_service_status(self) -> Dict:
        """Get current service status and statistics"""
        now = time.time()
        
        # Clean up old timestamps for accurate counts
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        self.hourly_request_timestamps = [ts for ts in self.hourly_request_timestamps if now - ts < 3600]
        
        return {
            "enabled": self.enabled,
            "client_initialized": self.client is not None,
            "region": self.region,
            "model_id": self.model_id,
            "rate_limits": {
                "max_requests_per_minute": self.max_requests_per_minute,
                "max_requests_per_hour": self.max_requests_per_hour,
                "max_requests_per_user_per_minute": self.max_requests_per_user_per_minute,
                "current_minute_requests": len(self.request_timestamps),
                "current_hour_requests": len(self.hourly_request_timestamps),
                "active_users": len(self.user_request_limits)
            },
            "cache": {
                "size": len(self.cache),
                "max_size": self.max_cache_size,
                "ttl_seconds": self.cache_ttl_seconds
            },
            "statistics": self.request_stats.copy()
        }
    
    def clear_cache(self) -> int:
        """Clear all cached responses and return number of items cleared"""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cleared {count} cached feedback responses")
        return count
    
    def get_cache_stats(self) -> Dict:
        """Get detailed cache statistics"""
        if not self.cache:
            return {"size": 0, "entries": []}
        
        entries = []
        for key, item in self.cache.items():
            age_seconds = (datetime.now() - item['timestamp']).total_seconds()
            entries.append({
                "key": key,
                "sign": item['response'].sign,
                "error_code": item['response'].error_code,
                "age_seconds": age_seconds,
                "source": item['response'].source
            })
        
        return {
            "size": len(self.cache),
            "entries": entries
        }
    
    def get_rate_limit_status(self, user_id: str = "default") -> Dict:
        """Get detailed rate limiting status for a specific user"""
        now = time.time()
        
        # Clean up old timestamps
        self.request_timestamps = [ts for ts in self.request_timestamps if now - ts < 60]
        self.hourly_request_timestamps = [ts for ts in self.hourly_request_timestamps if now - ts < 3600]
        
        if user_id in self.user_request_limits:
            self.user_request_limits[user_id] = [
                ts for ts in self.user_request_limits[user_id] if now - ts < 60
            ]
            user_requests = len(self.user_request_limits[user_id])
        else:
            user_requests = 0
        
        is_limited, limit_reason = self._is_rate_limited(user_id)
        
        return {
            "user_id": user_id,
            "is_rate_limited": is_limited,
            "limit_reason": limit_reason,
            "global_limits": {
                "minute": {
                    "current": len(self.request_timestamps),
                    "max": self.max_requests_per_minute,
                    "remaining": max(0, self.max_requests_per_minute - len(self.request_timestamps))
                },
                "hour": {
                    "current": len(self.hourly_request_timestamps),
                    "max": self.max_requests_per_hour,
                    "remaining": max(0, self.max_requests_per_hour - len(self.hourly_request_timestamps))
                }
            },
            "user_limits": {
                "minute": {
                    "current": user_requests,
                    "max": self.max_requests_per_user_per_minute,
                    "remaining": max(0, self.max_requests_per_user_per_minute - user_requests)
                }
            }
        }
    
    def reset_statistics(self) -> Dict:
        """Reset request statistics and return the previous values"""
        old_stats = self.request_stats.copy()
        self.request_stats = {
            'total_requests': 0,
            'bedrock_requests': 0,
            'fallback_requests': 0,
            'cached_requests': 0,
            'rate_limited_requests': 0
        }
        logger.info("Request statistics reset")
        return old_stats
    
    def get_error_code_mapping(self) -> Dict:
        """Get the complete error code to prompt mapping for debugging"""
        return {
            "error_prompts": self.error_prompts.copy(),
            "fallback_messages": self.fallback_messages.copy()
        }