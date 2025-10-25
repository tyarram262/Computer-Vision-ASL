/**
 * FastAPI Service
 * Handles communication with the FastAPI backend
 */

class FastApiService {
    constructor() {
        this.baseUrl = process.env.REACT_APP_FASTAPI_URL || 'http://localhost:8000';
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return true;

        try {
            const response = await fetch(`${this.baseUrl}/health`);
            const data = await response.json();

            this.initialized = data.status === 'healthy';
            return this.initialized;
        } catch (error) {
            console.warn('FastAPI service not available:', error);
            return false;
        }
    }

    async uploadVideo(file, signName) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('sign_name', signName);

            const response = await fetch(`${this.baseUrl}/upload_video?sign_name=${signName}`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error uploading video:', error);
            throw error;
        }
    }

    async getFeedback(sign, errorCode, userLandmarks = null, targetLandmarks = null) {
        try {
            const response = await fetch(`${this.baseUrl}/get_feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    sign,
                    error_code: errorCode,
                    user_landmarks: userLandmarks,
                    target_landmarks: targetLandmarks
                })
            });

            if (!response.ok) {
                throw new Error(`Feedback request failed: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error getting feedback:', error);
            // Return fallback feedback
            return {
                success: false,
                feedback: "Keep practicing - you're doing great!",
                error: error.message
            };
        }
    }

    async getAvailableSigns() {
        try {
            const response = await fetch(`${this.baseUrl}/available_signs`);

            if (!response.ok) {
                throw new Error(`Failed to get available signs: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error getting available signs:', error);
            return {
                success: false,
                signs: [],
                error: error.message
            };
        }
    }

    async getTargetData(signName) {
        try {
            const response = await fetch(`${this.baseUrl}/static/data/${signName.toLowerCase()}_data.json`);

            if (!response.ok) {
                throw new Error(`Failed to get target data for ${signName}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error getting target data:', error);
            throw error;
        }
    }

    getVideoUrl(signName) {
        return `${this.baseUrl}/static/videos/${signName.toLowerCase()}.mp4`;
    }

    getDataUrl(signName) {
        return `${this.baseUrl}/static/data/${signName.toLowerCase()}_data.json`;
    }

    async checkHealth() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return await response.json();
        } catch (error) {
            console.error('Health check failed:', error);
            return { status: 'unhealthy', error: error.message };
        }
    }
}

export default new FastApiService();