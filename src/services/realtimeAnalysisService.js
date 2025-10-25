/**
 * Real-time ASL Analysis Service - Smart Client Implementation
 * Handles client-side MediaPipe processing and advanced pose comparison
 */

import { HandLandmarker, PoseLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';

class RealtimeAnalysisService {
    constructor() {
        this.handLandmarker = null;
        this.poseLandmarker = null;
        this.isInitialized = false;
        this.targetData = null;
        this.currentVideoTime = 0;
        this.analysisCallback = null;
        this.animationFrameId = null;
        this.lastErrorCode = null;
        this.errorThreshold = 15; // degrees
    }

    async initialize() {
        if (this.isInitialized) return true;

        try {
            const vision = await FilesetResolver.forVisionTasks(
                "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
            );

            // Initialize Hand Landmarker
            this.handLandmarker = await HandLandmarker.createFromOptions(vision, {
                baseOptions: {
                    modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
                    delegate: "GPU"
                },
                runningMode: "VIDEO",
                numHands: 2
            });

            // Initialize Pose Landmarker
            this.poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
                baseOptions: {
                    modelAssetPath: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
                    delegate: "GPU"
                },
                runningMode: "VIDEO"
            });

            this.isInitialized = true;
            console.log("RealtimeAnalysisService initialized successfully");
            return true;

        } catch (error) {
            console.error("Failed to initialize RealtimeAnalysisService:", error);
            return false;
        }
    }

    async loadTargetData(signName) {
        try {
            const response = await fetch(`http://localhost:8000/static/data/${signName.toLowerCase()}_data.json`);
            if (!response.ok) {
                throw new Error(`Failed to load target data for ${signName}`);
            }

            this.targetData = await response.json();
            console.log(`Loaded target data for ${signName}:`, this.targetData);
            return true;
        } catch (error) {
            console.error("Error loading target data:", error);
            return false;
        }
    }

    startAnalysis(videoElement, webcamElement, callback) {
        if (!this.isInitialized || !this.targetData) {
            console.error("Service not initialized or target data not loaded");
            return;
        }

        this.analysisCallback = callback;
        this.runAnalysisLoop(videoElement, webcamElement);
    }

    stopAnalysis() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }

    // The "Game Loop" - Real-time analysis using requestAnimationFrame
    runAnalysisLoop(videoElement, webcamElement) {
        const analyze = async () => {
            try {
                // Get current video timestamp
                this.currentVideoTime = videoElement.currentTime;

                // Get user's live landmarks from webcam
                const userLandmarks = await this.getUserLandmarks(webcamElement);

                // Find corresponding landmarks from pre-fetched JSON
                const targetLandmarks = this.getTargetLandmarksAtTime(this.currentVideoTime);

                // Call the Comparison Logic - The "Secret Sauce"
                const results = this.comparePoses(userLandmarks, targetLandmarks);

                // Update UI and trigger feedback if needed
                if (this.analysisCallback) {
                    this.analysisCallback(results);
                }

                // Check for significant errors and trigger async feedback
                if (results.errorCode !== this.lastErrorCode && results.worstError > this.errorThreshold) {
                    this.lastErrorCode = results.errorCode;
                    // This will be handled by the React component
                }

            } catch (error) {
                console.error("Error in analysis loop:", error);
            }

            // Schedule next frame
            this.animationFrameId = requestAnimationFrame(analyze);
        };

        analyze();
    }

    async getUserLandmarks(webcamElement) {
        try {
            const timestamp = performance.now();

            // Run the live webcam frame through JS MediaPipe detectors
            const handResults = this.handLandmarker.detectForVideo(webcamElement, timestamp);
            const poseResults = this.poseLandmarker.detectForVideo(webcamElement, timestamp);

            return {
                hands: handResults.landmarks || [],
                pose: poseResults.landmarks?.[0] || null,
                timestamp: timestamp
            };

        } catch (error) {
            console.error("Error getting user landmarks:", error);
            return { hands: [], pose: null, timestamp: performance.now() };
        }
    }

    getTargetLandmarksAtTime(currentTime) {
        if (!this.targetData || !this.targetData.frames) {
            return null;
        }

        // Find the frame closest to current time
        const targetFrame = this.targetData.frames.find(frame =>
            Math.abs(frame.timestamp - currentTime) < (1 / this.targetData.fps)
        );

        if (!targetFrame) {
            return null;
        }

        return {
            hands: targetFrame.hand_landmarks || [],
            pose: targetFrame.pose_landmarks || null,
            timestamp: targetFrame.timestamp
        };
    }

    // The "Secret Sauce" - Advanced pose comparison with normalization and angle analysis
    comparePoses(userLandmarks, targetLandmarks) {
        if (!userLandmarks || !targetLandmarks) {
            return {
                score: 0,
                worstJoint: null,
                errorCode: "NO_DATA",
                worstError: 0,
                details: "Missing landmark data"
            };
        }

        let totalScore = 0;
        let comparisons = 0;
        let worstJoint = null;
        let worstError = 0;
        let errorCode = "GENERAL_FORM";
        let userAngleVector = [];
        let targetAngleVector = [];

        // Compare hand landmarks with advanced normalization
        if (userLandmarks.hands.length > 0 && targetLandmarks.hands.length > 0) {
            const handComparison = this.compareHandLandmarksAdvanced(
                userLandmarks.hands[0],
                targetLandmarks.hands[0]
            );

            totalScore += handComparison.score;
            comparisons++;
            userAngleVector = userAngleVector.concat(handComparison.userAngles);
            targetAngleVector = targetAngleVector.concat(handComparison.targetAngles);

            if (handComparison.maxError > worstError) {
                worstError = handComparison.maxError;
                worstJoint = handComparison.worstJoint;
                errorCode = handComparison.errorCode;
            }
        }

        // Compare pose landmarks with advanced normalization
        if (userLandmarks.pose && targetLandmarks.pose) {
            const poseComparison = this.comparePoseLandmarksAdvanced(
                userLandmarks.pose,
                targetLandmarks.pose
            );

            totalScore += poseComparison.score;
            comparisons++;
            userAngleVector = userAngleVector.concat(poseComparison.userAngles);
            targetAngleVector = targetAngleVector.concat(poseComparison.targetAngles);

            if (poseComparison.maxError > worstError) {
                worstError = poseComparison.maxError;
                worstJoint = poseComparison.worstJoint;
                errorCode = poseComparison.errorCode;
            }
        }

        // Calculate overall similarity using cosine similarity of angle vectors
        let finalScore = 0;
        if (userAngleVector.length > 0 && targetAngleVector.length > 0) {
            const cosineSimilarity = this.calculateCosineSimilarity(userAngleVector, targetAngleVector);
            finalScore = Math.round(Math.max(0, Math.min(100, cosineSimilarity * 100)));
        } else if (comparisons > 0) {
            finalScore = Math.round(totalScore / comparisons);
        }

        return {
            score: finalScore,
            worstJoint: worstJoint,
            errorCode: errorCode,
            worstError: worstError,
            details: {
                userHands: userLandmarks.hands.length,
                targetHands: targetLandmarks.hands.length,
                userPose: !!userLandmarks.pose,
                targetPose: !!targetLandmarks.pose,
                comparisons: comparisons,
                userAngleVector: userAngleVector,
                targetAngleVector: targetAngleVector
            }
        };
    }

    // Advanced hand comparison with normalization and angle calculation
    compareHandLandmarksAdvanced(userHand, targetHand) {
        if (!userHand || !targetHand || userHand.length !== targetHand.length) {
            return {
                score: 0,
                maxError: 100,
                worstJoint: null,
                errorCode: "HAND_MISSING",
                userAngles: [],
                targetAngles: []
            };
        }

        // Normalize both hands (center and scale)
        const normalizedUser = this.normalizeHandLandmarks(userHand);
        const normalizedTarget = this.normalizeHandLandmarks(targetHand);

        // Calculate key angles for both hands
        const userAngles = this.calculateHandAnglesAdvanced(normalizedUser);
        const targetAngles = this.calculateHandAnglesAdvanced(normalizedTarget);

        let totalError = 0;
        let maxError = 0;
        let worstJoint = null;
        let errorCode = "GENERAL_FORM";
        let validComparisons = 0;

        // Compare each angle
        for (const [jointName, userAngle] of Object.entries(userAngles)) {
            if (targetAngles[jointName] !== undefined) {
                const angleDiff = Math.abs(userAngle - targetAngles[jointName]);
                totalError += angleDiff;
                validComparisons++;

                if (angleDiff > maxError) {
                    maxError = angleDiff;
                    worstJoint = jointName;

                    // Determine specific error code based on joint and angle difference
                    if (jointName.includes('THUMB')) {
                        errorCode = userAngle > targetAngles[jointName] ? "THUMB_HIGH" : "THUMB_LOW";
                    } else if (jointName.includes('FINGER')) {
                        errorCode = angleDiff > 30 ? "FINGERS_SPREAD" : "FINGERS_CLOSED";
                    } else if (jointName.includes('WRIST')) {
                        errorCode = "WRIST_BEND";
                    } else {
                        errorCode = "HAND_ANGLE";
                    }
                }
            }
        }

        // Calculate score based on mean squared error
        const avgError = validComparisons > 0 ? totalError / validComparisons : 100;
        const score = Math.max(0, Math.min(100, 100 - (avgError * 1.5)));

        return {
            score: score,
            maxError: maxError,
            worstJoint: worstJoint,
            errorCode: errorCode,
            userAngles: Object.values(userAngles),
            targetAngles: Object.values(targetAngles)
        };
    }

    // Advanced pose comparison with normalization
    comparePoseLandmarksAdvanced(userPose, targetPose) {
        if (!userPose || !targetPose) {
            return {
                score: 0,
                maxError: 100,
                worstJoint: null,
                errorCode: "POSE_MISSING",
                userAngles: [],
                targetAngles: []
            };
        }

        // Normalize both poses (center on shoulders and scale)
        const normalizedUser = this.normalizePoseLandmarks(userPose);
        const normalizedTarget = this.normalizePoseLandmarks(targetPose);

        // Calculate key angles
        const userAngles = this.calculatePoseAnglesAdvanced(normalizedUser);
        const targetAngles = this.calculatePoseAnglesAdvanced(normalizedTarget);

        let totalError = 0;
        let maxError = 0;
        let worstJoint = null;
        let errorCode = "ARM_POSITION";
        let validComparisons = 0;

        // Compare each angle
        for (const [jointName, userAngle] of Object.entries(userAngles)) {
            if (targetAngles[jointName] !== undefined) {
                const angleDiff = Math.abs(userAngle - targetAngles[jointName]);
                totalError += angleDiff;
                validComparisons++;

                if (angleDiff > maxError) {
                    maxError = angleDiff;
                    worstJoint = jointName;
                    errorCode = "ARM_POSITION";
                }
            }
        }

        const avgError = validComparisons > 0 ? totalError / validComparisons : 100;
        const score = Math.max(0, Math.min(100, 100 - (avgError * 1.2)));

        return {
            score: score,
            maxError: maxError,
            worstJoint: worstJoint,
            errorCode: errorCode,
            userAngles: Object.values(userAngles),
            targetAngles: Object.values(targetAngles)
        };
    }

    // Normalization: Center and scale hand landmarks
    normalizeHandLandmarks(landmarks) {
        // Use wrist as center point
        const wrist = landmarks[0];

        // Calculate bounding box for scaling
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        landmarks.forEach(point => {
            minX = Math.min(minX, point.x);
            maxX = Math.max(maxX, point.x);
            minY = Math.min(minY, point.y);
            maxY = Math.max(maxY, point.y);
        });

        const scale = Math.max(maxX - minX, maxY - minY);

        // Normalize: center on wrist and scale
        return landmarks.map(point => ({
            x: (point.x - wrist.x) / scale,
            y: (point.y - wrist.y) / scale,
            z: (point.z - wrist.z) / scale
        }));
    }

    // Normalization: Center pose on shoulders and scale
    normalizePoseLandmarks(landmarks) {
        const leftShoulder = landmarks[11];
        const rightShoulder = landmarks[12];

        // Center point between shoulders
        const center = {
            x: (leftShoulder.x + rightShoulder.x) / 2,
            y: (leftShoulder.y + rightShoulder.y) / 2,
            z: (leftShoulder.z + rightShoulder.z) / 2
        };

        // Scale based on shoulder distance
        const shoulderDistance = Math.sqrt(
            Math.pow(rightShoulder.x - leftShoulder.x, 2) +
            Math.pow(rightShoulder.y - leftShoulder.y, 2) +
            Math.pow(rightShoulder.z - leftShoulder.z, 2)
        );

        // Normalize: center on shoulder midpoint and scale by shoulder distance
        return landmarks.map(point => ({
            x: (point.x - center.x) / shoulderDistance,
            y: (point.y - center.y) / shoulderDistance,
            z: (point.z - center.z) / shoulderDistance
        }));
    }

    // Advanced hand angle calculation
    calculateHandAnglesAdvanced(landmarks) {
        const angles = {};

        try {
            // Thumb angles
            angles.THUMB_CMC_ANGLE = this.getAngle(landmarks[0], landmarks[1], landmarks[2]);
            angles.THUMB_MCP_ANGLE = this.getAngle(landmarks[1], landmarks[2], landmarks[3]);
            angles.THUMB_IP_ANGLE = this.getAngle(landmarks[2], landmarks[3], landmarks[4]);

            // Index finger angles
            angles.INDEX_MCP_ANGLE = this.getAngle(landmarks[0], landmarks[5], landmarks[6]);
            angles.INDEX_PIP_ANGLE = this.getAngle(landmarks[5], landmarks[6], landmarks[7]);
            angles.INDEX_DIP_ANGLE = this.getAngle(landmarks[6], landmarks[7], landmarks[8]);

            // Middle finger angles
            angles.MIDDLE_MCP_ANGLE = this.getAngle(landmarks[0], landmarks[9], landmarks[10]);
            angles.MIDDLE_PIP_ANGLE = this.getAngle(landmarks[9], landmarks[10], landmarks[11]);
            angles.MIDDLE_DIP_ANGLE = this.getAngle(landmarks[10], landmarks[11], landmarks[12]);

            // Ring finger angles
            angles.RING_MCP_ANGLE = this.getAngle(landmarks[0], landmarks[13], landmarks[14]);
            angles.RING_PIP_ANGLE = this.getAngle(landmarks[13], landmarks[14], landmarks[15]);
            angles.RING_DIP_ANGLE = this.getAngle(landmarks[14], landmarks[15], landmarks[16]);

            // Pinky angles
            angles.PINKY_MCP_ANGLE = this.getAngle(landmarks[0], landmarks[17], landmarks[18]);
            angles.PINKY_PIP_ANGLE = this.getAngle(landmarks[17], landmarks[18], landmarks[19]);
            angles.PINKY_DIP_ANGLE = this.getAngle(landmarks[18], landmarks[19], landmarks[20]);

        } catch (error) {
            console.error("Error calculating hand angles:", error);
        }

        return angles;
    }

    // Advanced pose angle calculation
    calculatePoseAnglesAdvanced(landmarks) {
        const angles = {};

        try {
            // Left arm angles
            angles.LEFT_SHOULDER_ANGLE = this.getAngle(landmarks[11], landmarks[13], landmarks[15]);
            angles.LEFT_ELBOW_ANGLE = this.getAngle(landmarks[11], landmarks[13], landmarks[15]);

            // Right arm angles
            angles.RIGHT_SHOULDER_ANGLE = this.getAngle(landmarks[12], landmarks[14], landmarks[16]);
            angles.RIGHT_ELBOW_ANGLE = this.getAngle(landmarks[12], landmarks[14], landmarks[16]);

            // Torso angle
            angles.TORSO_ANGLE = this.getAngle(landmarks[11], landmarks[23], landmarks[24]);

        } catch (error) {
            console.error("Error calculating pose angles:", error);
        }

        return angles;
    }

    // Calculate angle between three 3D points
    getAngle(pointA, pointB, pointC) {
        const vectorBA = {
            x: pointA.x - pointB.x,
            y: pointA.y - pointB.y,
            z: pointA.z - pointB.z
        };

        const vectorBC = {
            x: pointC.x - pointB.x,
            y: pointC.y - pointB.y,
            z: pointC.z - pointB.z
        };

        const dotProduct = vectorBA.x * vectorBC.x + vectorBA.y * vectorBC.y + vectorBA.z * vectorBC.z;
        const magnitudeBA = Math.sqrt(vectorBA.x ** 2 + vectorBA.y ** 2 + vectorBA.z ** 2);
        const magnitudeBC = Math.sqrt(vectorBC.x ** 2 + vectorBC.y ** 2 + vectorBC.z ** 2);

        if (magnitudeBA === 0 || magnitudeBC === 0) return 0;

        const cosAngle = dotProduct / (magnitudeBA * magnitudeBC);
        const angle = Math.acos(Math.max(-1, Math.min(1, cosAngle))) * (180 / Math.PI);

        return angle;
    }

    // Calculate cosine similarity between two vectors
    calculateCosineSimilarity(vectorA, vectorB) {
        if (vectorA.length !== vectorB.length || vectorA.length === 0) {
            return 0;
        }

        let dotProduct = 0;
        let magnitudeA = 0;
        let magnitudeB = 0;

        for (let i = 0; i < vectorA.length; i++) {
            dotProduct += vectorA[i] * vectorB[i];
            magnitudeA += vectorA[i] ** 2;
            magnitudeB += vectorB[i] ** 2;
        }

        magnitudeA = Math.sqrt(magnitudeA);
        magnitudeB = Math.sqrt(magnitudeB);

        if (magnitudeA === 0 || magnitudeB === 0) {
            return 0;
        }

        return dotProduct / (magnitudeA * magnitudeB);
    }

    // Drawing utilities for visualization
    drawUserLandmarks(canvas, landmarks, color = 'blue') {
        const ctx = canvas.getContext('2d');

        if (landmarks.hands && landmarks.hands.length > 0) {
            this.drawHandLandmarks(ctx, landmarks.hands[0], color, canvas.width, canvas.height);
        }

        if (landmarks.pose) {
            this.drawPoseLandmarks(ctx, landmarks.pose, color, canvas.width, canvas.height);
        }
    }

    drawHandLandmarks(ctx, handLandmarks, color, width, height) {
        ctx.fillStyle = color;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        // Draw landmarks
        handLandmarks.forEach(landmark => {
            const x = landmark.x * width;
            const y = landmark.y * height;

            ctx.beginPath();
            ctx.arc(x, y, 3, 0, 2 * Math.PI);
            ctx.fill();
        });

        // Draw connections
        const connections = [
            [0, 1], [1, 2], [2, 3], [3, 4], // thumb
            [0, 5], [5, 6], [6, 7], [7, 8], // index
            [0, 9], [9, 10], [10, 11], [11, 12], // middle
            [0, 13], [13, 14], [14, 15], [15, 16], // ring
            [0, 17], [17, 18], [18, 19], [19, 20] // pinky
        ];

        connections.forEach(([start, end]) => {
            const startPoint = handLandmarks[start];
            const endPoint = handLandmarks[end];

            ctx.beginPath();
            ctx.moveTo(startPoint.x * width, startPoint.y * height);
            ctx.lineTo(endPoint.x * width, endPoint.y * height);
            ctx.stroke();
        });
    }

    drawPoseLandmarks(ctx, poseLandmarks, color, width, height) {
        ctx.fillStyle = color;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;

        // Draw key pose points
        const keyPoints = [11, 12, 13, 14, 15, 16]; // shoulders, elbows, wrists

        keyPoints.forEach(index => {
            if (poseLandmarks[index]) {
                const landmark = poseLandmarks[index];
                const x = landmark.x * width;
                const y = landmark.y * height;

                ctx.beginPath();
                ctx.arc(x, y, 4, 0, 2 * Math.PI);
                ctx.fill();
            }
        });

        // Draw arm connections
        const armConnections = [
            [11, 13], [13, 15], // left arm
            [12, 14], [14, 16], // right arm
            [11, 12] // shoulders
        ];

        armConnections.forEach(([start, end]) => {
            const startPoint = poseLandmarks[start];
            const endPoint = poseLandmarks[end];

            if (startPoint && endPoint) {
                ctx.beginPath();
                ctx.moveTo(startPoint.x * width, startPoint.y * height);
                ctx.lineTo(endPoint.x * width, endPoint.y * height);
                ctx.stroke();
            }
        });
    }
}

export default new RealtimeAnalysisService();