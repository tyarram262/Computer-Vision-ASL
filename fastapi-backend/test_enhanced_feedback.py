#!/usr/bin/env python3
"""
Test script for enhanced feedback request processing and caching functionality
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.bedrock_service import BedrockService
import time

def test_error_code_mapping():
    """Test that all error codes have proper mappings"""
    print("Testing error code mapping...")
    
    service = BedrockService()
    
    # Check that we have comprehensive error code coverage
    assert len(service.error_prompts) > 15, "Should have comprehensive error code mapping"
    assert len(service.fallback_messages) > 15, "Should have comprehensive fallback messages"
    
    # Test that all error codes have both prompts and fallbacks
    for error_code in service.error_prompts:
        assert error_code in service.fallback_messages, f"Missing fallback for {error_code}"
    
    print(f"✓ {len(service.error_prompts)} error codes properly mapped")

def test_rate_limiting():
    """Test rate limiting functionality"""
    print("Testing rate limiting...")
    
    service = BedrockService()
    
    # Clear cache to ensure we're not getting cached responses
    service.clear_cache()
    
    # Test that rate limiting starts clean
    status = service.get_rate_limit_status("rate_test_user")
    assert not status["is_rate_limited"], "Should not be rate limited initially"
    
    # Test user-specific rate limiting
    user_limit = service.max_requests_per_user_per_minute
    
    # Make requests up to the limit with different error codes to avoid caching
    error_codes = ["THUMB_LOW", "FINGERS_SPREAD", "HAND_ROTATION", "WRIST_BEND", "ARM_POSITION"]
    
    for i in range(user_limit):
        error_code = error_codes[i % len(error_codes)]
        response = service.get_feedback(f"test_{i}", error_code, "rate_test_user")
        assert response.success, f"Request {i+1} should succeed"
        print(f"Request {i+1}: {response.source}")
    
    # Check that we've hit the limit
    status = service.get_rate_limit_status("rate_test_user")
    print(f"After {user_limit} requests - User requests: {status['user_limits']['minute']['current']}")
    
    # Next request should be rate limited
    response = service.get_feedback("test_extra", "GENERAL_FORM", "rate_test_user")
    print(f"Extra request source: {response.source}")
    
    # Check if the response indicates rate limiting
    assert "rate_limited" in response.source, f"Should be rate limited, got source: {response.source}"
    
    print(f"✓ Rate limiting works correctly (limit: {user_limit})")

def test_caching():
    """Test caching functionality"""
    print("Testing caching...")
    
    service = BedrockService()
    
    # Clear cache to start fresh
    service.clear_cache()
    
    # First request should not be cached
    response1 = service.get_feedback("hello", "THUMB_LOW", "cache_test_user")
    assert not response1.cached, "First request should not be cached"
    
    # Second identical request should be cached
    response2 = service.get_feedback("hello", "THUMB_LOW", "cache_test_user")
    assert response2.cached, "Second identical request should be cached"
    
    # Different error code should not be cached
    response3 = service.get_feedback("hello", "FINGERS_SPREAD", "cache_test_user")
    assert not response3.cached, "Different error code should not be cached"
    
    print("✓ Caching works correctly")

def test_structured_response_format():
    """Test that responses follow the structured format"""
    print("Testing structured response format...")
    
    service = BedrockService()
    
    response = service.get_feedback("test", "THUMB_LOW", "format_test_user")
    
    # Check all required fields are present
    required_fields = ['success', 'feedback', 'error_code', 'sign', 'timestamp', 'source', 'cached']
    for field in required_fields:
        assert hasattr(response, field), f"Response missing required field: {field}"
    
    # Check field types
    assert isinstance(response.success, bool), "success should be boolean"
    assert isinstance(response.feedback, str), "feedback should be string"
    assert isinstance(response.error_code, str), "error_code should be string"
    assert isinstance(response.sign, str), "sign should be string"
    assert isinstance(response.cached, bool), "cached should be boolean"
    
    # Check that feedback is not empty
    assert len(response.feedback) > 0, "feedback should not be empty"
    
    print("✓ Response format is properly structured")

def test_statistics_tracking():
    """Test request statistics tracking"""
    print("Testing statistics tracking...")
    
    service = BedrockService()
    
    # Reset statistics
    service.reset_statistics()
    
    # Make some requests
    service.get_feedback("test1", "THUMB_LOW", "stats_user1")
    service.get_feedback("test2", "FINGERS_SPREAD", "stats_user2")
    service.get_feedback("test1", "THUMB_LOW", "stats_user1")  # This should be cached
    
    stats = service.request_stats
    
    # Check that statistics are being tracked
    assert stats['total_requests'] > 0, "Should track total requests"
    assert stats['cached_requests'] > 0, "Should track cached requests"
    assert stats['fallback_requests'] > 0, "Should track fallback requests"
    
    print("✓ Statistics tracking works correctly")

def main():
    """Run all tests"""
    print("Running enhanced feedback processing tests...\n")
    
    try:
        test_error_code_mapping()
        test_rate_limiting()
        test_caching()
        test_structured_response_format()
        test_statistics_tracking()
        
        print("\n✅ All tests passed! Enhanced feedback processing is working correctly.")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()