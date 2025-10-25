import React, { useState, useEffect, useRef, useCallback } from 'react';
import realtimeAnalysisService from '../services/realtimeAnalysisService';
import fastApiService from '../services/fastApiService';

const RealtimeAnalysis = ({ selectedSign, onScoreUpdate, onFeedbackUpdate }) => {
    const videoRef = useRef(null);
    const webcamRef = useRef(null);
    const overlayCanvasRef = useRef(null);

    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [currentScore, setCurrentScore] = useState(0);
    const [feedback, setFeedback] = useState('');
    const [error, setError] = useState('');
    const [videoLoaded, setVideoLoaded] = useState(false);
    const [webcamReady, setWebcamReady] = useState(false);
    const [lastErrorCode, setLastErrorCode] = useState('');
    const [analysisStats, setAnalysisStats] = useState({
        framesProcessed: 0,
        avgScore: 0,
        bestScore: 0
    });

    // Initialize services
    useEffect(() => {
        const initServices = async () => {
            try {
                const realtimeReady = await realtimeAnalysisService.initialize();
                const fastApiReady = await fastApiService.initialize();

                if (!realtimeReady) {
                    setError('Failed to initialize MediaPipe - please refresh the page');
                }
                if (!fastApiReady) {
                    console.warn('FastAPI service not available - using fallback feedback');
                }
            } catch (err) {
                setError(`Initialization error: ${err.message}`);
            }
        };

        initServices();
    }, []);

    // Load target video and data when sign changes
    useEffect(() => {
        if (!selectedSign) return;

        const loadTargetData = async () => {
            try {
                setVideoLoaded(false);
                setError('');

                // Load target landmarks data
                const success = await realtimeAnalysisService.loadTargetData(selectedSign.name);
                if (!success) {
                    setError(`Failed to load data for ${selectedSign.name}. Please upload the video first.`);
                    return;
                }

                // Set video source
                if (videoRef.current) {
                    videoRef.current.src = fastApiService.getVideoUrl(selectedSign.name);
                }

            } catch (err) {
                setError(`Error loading target data: ${err.message}`);
            }
        };

        loadTargetData();
    }, [selectedSign]);

    // Setup webcam
    useEffect(() => {
        const setupWebcam = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: 640,
                        height: 480,
                        facingMode: 'user'
                    }
                });

                if (webcamRef.current) {
                    webcamRef.current.srcObject = stream;
                    webcamRef.current.onloadedmetadata = () => {
                        setWebcamReady(true);
                    };
                }
            } catch (err) {
                setError(`Webcam error: ${err.message}. Please allow camera access.`);
            }
        };

        setupWebcam();

        return () => {
            // Cleanup webcam stream
            if (webcamRef.current && webcamRef.current.srcObject) {
                const tracks = webcamRef.current.srcObject.getTracks();
                tracks.forEach(track => track.stop());
            }
        };
    }, []);

    // Real-time analysis callback - The core of the Smart Client model
    const handleAnalysisResults = useCallback(async (results) => {
        // Instantly calculate "Match Score" and update UI
        setCurrentScore(results.score);

        // Update statistics
        setAnalysisStats(prev => ({
            framesProcessed: prev.framesProcessed + 1,
            avgScore: Math.round((prev.avgScore * prev.framesProcessed + results.score) / (prev.framesProcessed + 1)),
            bestScore: Math.max(prev.bestScore, results.score)
        }));

        // Update parent components
        if (onScoreUpdate) {
            onScoreUpdate(results.score);
        }

        // Smart Feedback: When significant error detected (thumb angle > 15° deviation)
        if (results.errorCode !== lastErrorCode && results.worstError > 15) {
            setLastErrorCode(results.errorCode);

            // Asynchronously call FastAPI backend for AI tip
            try {
                const feedbackResponse = await fastApiService.getFeedback(
                    selectedSign?.name || 'unknown',
                    results.errorCode
                );

                if (feedbackResponse.success) {
                    setFeedback(feedbackResponse.feedback);
                    if (onFeedbackUpdate) {
                        onFeedbackUpdate(feedbackResponse.feedback);
                    }
                }
            } catch (err) {
                console.error('Error getting AI feedback:', err);
            }
        }

        // Draw user's skeleton on canvas and highlight errors (e.g., red thumb)
        drawVisualization(results);
    }, [selectedSign, lastErrorCode, onScoreUpdate, onFeedbackUpdate]);

    // UI Update: Draw skeleton and highlight errors
    const drawVisualization = (results) => {
        const canvas = overlayCanvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw user landmarks in blue (normal)
        if (results.details?.userHands > 0 || results.details?.userPose) {
            // Draw score in top-left
            ctx.fillStyle = 'rgba(59, 130, 246, 0.9)';
            ctx.font = 'bold 24px Arial';
            ctx.fillText(`${results.score}%`, 15, 35);

            // Highlight worst joint in red if error detected
            if (results.worstJoint && results.worstError > 15) {
                ctx.fillStyle = 'rgba(239, 68, 68, 0.9)';
                ctx.font = 'bold 16px Arial';
                ctx.fillText(`⚠️ ${results.worstJoint}`, 15, 65);

                // Draw error indicator
                ctx.fillStyle = 'rgba(239, 68, 68, 0.3)';
                ctx.fillRect(0, 0, canvas.width, 8);
            } else if (results.score > 80) {
                // Draw success indicator
                ctx.fillStyle = 'rgba(16, 185, 129, 0.3)';
                ctx.fillRect(0, 0, canvas.width, 8);
            }
        }

        // Draw frame counter
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.font = '12px Arial';
        ctx.fillText(`Frames: ${analysisStats.framesProcessed}`, canvas.width - 100, 20);
        ctx.fillText(`Best: ${analysisStats.bestScore}%`, canvas.width - 100, 35);
    };

    const startAnalysis = () => {
        if (!videoLoaded || !webcamReady || !selectedSign) {
            setError('Please ensure video is loaded and webcam is ready');
            return;
        }

        setIsAnalyzing(true);
        setError('');
        setFeedback('');
        setLastErrorCode('');
        setAnalysisStats({ framesProcessed: 0, avgScore: 0, bestScore: 0 });

        // Start video playback and simultaneously activate webcam
        if (videoRef.current) {
            videoRef.current.currentTime = 0;
            videoRef.current.play();
        }

        // Start the real-time processing loop
        realtimeAnalysisService.startAnalysis(
            videoRef.current,
            webcamRef.current,
            handleAnalysisResults
        );
    };

    const stopAnalysis = () => {
        setIsAnalyzing(false);

        // Stop video
        if (videoRef.current) {
            videoRef.current.pause();
            videoRef.current.currentTime = 0;
        }

        // Stop analysis loop
        realtimeAnalysisService.stopAnalysis();

        // Clear visualization
        if (overlayCanvasRef.current) {
            const ctx = overlayCanvasRef.current.getContext('2d');
            ctx.clearRect(0, 0, overlayCanvasRef.current.width, overlayCanvasRef.current.height);
        }
    };

    const handleVideoLoaded = () => {
        setVideoLoaded(true);

        // Setup overlay canvas dimensions to match webcam
        if (overlayCanvasRef.current && webcamRef.current) {
            overlayCanvasRef.current.width = 640;
            overlayCanvasRef.current.height = 480;
        }
    };

    const handleVideoEnded = () => {
        // Loop the video for continuous practice
        if (videoRef.current && isAnalyzing) {
            videoRef.current.currentTime = 0;
            videoRef.current.play();
        }
    };

    return (
        <div className="realtime-analysis">
            <div className="analysis-header">
                <h3>Real-time ASL Analysis</h3>
                {selectedSign && (
                    <p>Learning: <strong>{selectedSign.name.toUpperCase()}</strong></p>
                )}
            </div>

            {error && (
                <div className="error-message">
                    <p>⚠️ {error}</p>
                </div>
            )}

            <div className="video-container">
                {/* Target Video - plays simultaneously with webcam analysis */}
                <div className="target-video-section">
                    <h4>Target Sign</h4>
                    <div className="video-wrapper">
                        <video
                            ref={videoRef}
                            onLoadedMetadata={handleVideoLoaded}
                            onEnded={handleVideoEnded}
                            muted
                            className="target-video"
                        />
                        {!videoLoaded && selectedSign && (
                            <div className="loading-placeholder">
                                Loading {selectedSign.name} video...
                            </div>
                        )}
                    </div>
                </div>

                {/* User Webcam with Real-time Overlay */}
                <div className="webcam-section">
                    <h4>Your Practice</h4>
                    <div className="webcam-container">
                        <video
                            ref={webcamRef}
                            autoPlay
                            muted
                            className="webcam-video"
                        />
                        {/* Canvas overlay for skeleton drawing and error highlighting */}
                        <canvas
                            ref={overlayCanvasRef}
                            className="overlay-canvas"
                        />
                        {!webcamReady && (
                            <div className="loading-placeholder">
                                Setting up webcam...
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Controls */}
            <div className="analysis-controls">
                {!isAnalyzing ? (
                    <button
                        onClick={startAnalysis}
                        disabled={!videoLoaded || !webcamReady || !selectedSign}
                        className="start-analysis-btn"
                    >
                        🎯 Start Real-time Analysis
                    </button>
                ) : (
                    <button
                        onClick={stopAnalysis}
                        className="stop-analysis-btn"
                    >
                        ⏹️ Stop Analysis
                    </button>
                )}
            </div>

            {/* Real-time Results Display */}
            <div className="analysis-results">
                <div className="score-display">
                    <h4>Live Match Score</h4>
                    <div className="score-circle">
                        <span className="score-value">{currentScore}%</span>
                    </div>

                    {/* Analysis Statistics */}
                    <div className="stats-display">
                        <div className="stat-item">
                            <span className="stat-label">Frames:</span>
                            <span className="stat-value">{analysisStats.framesProcessed}</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-label">Average:</span>
                            <span className="stat-value">{analysisStats.avgScore}%</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-label">Best:</span>
                            <span className="stat-value">{analysisStats.bestScore}%</span>
                        </div>
                    </div>
                </div>

                {/* AI-Generated Feedback */}
                {feedback && (
                    <div className="feedback-display">
                        <h4>🤖 AI Instructor</h4>
                        <p className="feedback-text">{feedback}</p>
                    </div>
                )}
            </div>

            {/* System Status */}
            <div className="status-indicators">
                <div className={`status-item ${videoLoaded ? 'ready' : 'loading'}`}>
                    📹 Target Video: {videoLoaded ? 'Ready' : 'Loading...'}
                </div>
                <div className={`status-item ${webcamReady ? 'ready' : 'loading'}`}>
                    📷 Webcam: {webcamReady ? 'Ready' : 'Setting up...'}
                </div>
                <div className={`status-item ${isAnalyzing ? 'active' : 'inactive'}`}>
                    🔄 Analysis: {isAnalyzing ? 'Running' : 'Stopped'}
                </div>
            </div>

            {/* Instructions */}
            <div className="instructions">
                <h4>How it works:</h4>
                <ol>
                    <li><strong>Watch</strong> the target video to see the correct sign</li>
                    <li><strong>Practice</strong> the sign in front of your webcam</li>
                    <li><strong>Get instant feedback</strong> with skeleton overlay and match scores</li>
                    <li><strong>Receive AI tips</strong> when errors are detected</li>
                </ol>
            </div>
        </div>
    );
};

export default RealtimeAnalysis;