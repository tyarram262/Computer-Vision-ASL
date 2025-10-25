import React, { useState } from 'react';
import fastApiService from '../services/fastApiService';

const VideoUpload = ({ onUploadComplete }) => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [signName, setSignName] = useState('');
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState(null);
    const [error, setError] = useState('');

    const handleFileSelect = (event) => {
        const file = event.target.files[0];
        if (file) {
            // Validate file type
            if (!file.type.startsWith('video/')) {
                setError('Please select a video file');
                return;
            }

            setSelectedFile(file);
            setError('');

            // Auto-generate sign name from filename if not set
            if (!signName) {
                const name = file.name.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9]/g, '');
                setSignName(name);
            }
        }
    };

    const handleUpload = async () => {
        if (!selectedFile || !signName.trim()) {
            setError('Please select a file and enter a sign name');
            return;
        }

        setUploading(true);
        setError('');
        setUploadResult(null);

        try {
            const result = await fastApiService.uploadVideo(selectedFile, signName.trim());

            setUploadResult(result);

            if (result.success && onUploadComplete) {
                onUploadComplete(result);
            }

            // Reset form
            setSelectedFile(null);
            setSignName('');

        } catch (err) {
            setError(`Upload failed: ${err.message}`);
        } finally {
            setUploading(false);
        }
    };

    const resetForm = () => {
        setSelectedFile(null);
        setSignName('');
        setUploadResult(null);
        setError('');
    };

    return (
        <div className="video-upload">
            <div className="upload-header">
                <h3>Upload Target Video</h3>
                <p>Upload a video demonstrating the correct ASL sign for analysis</p>
            </div>

            <div className="upload-form">
                <div className="form-group">
                    <label htmlFor="signName">Sign Name:</label>
                    <input
                        id="signName"
                        type="text"
                        value={signName}
                        onChange={(e) => setSignName(e.target.value)}
                        placeholder="e.g., Hello, Thank You, Yes"
                        disabled={uploading}
                        className="sign-name-input"
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="videoFile">Video File:</label>
                    <input
                        id="videoFile"
                        type="file"
                        accept="video/*"
                        onChange={handleFileSelect}
                        disabled={uploading}
                        className="file-input"
                    />
                    {selectedFile && (
                        <div className="file-info">
                            <p>Selected: {selectedFile.name}</p>
                            <p>Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                    )}
                </div>

                <div className="upload-actions">
                    <button
                        onClick={handleUpload}
                        disabled={!selectedFile || !signName.trim() || uploading}
                        className="upload-btn"
                    >
                        {uploading ? 'Processing...' : 'Upload & Process'}
                    </button>

                    <button
                        onClick={resetForm}
                        disabled={uploading}
                        className="reset-btn"
                    >
                        Reset
                    </button>
                </div>
            </div>

            {uploading && (
                <div className="upload-progress">
                    <div className="progress-spinner"></div>
                    <p>Uploading and processing video...</p>
                    <p className="progress-note">This may take a few minutes depending on video length</p>
                </div>
            )}

            {error && (
                <div className="error-message">
                    <p>❌ {error}</p>
                </div>
            )}

            {uploadResult && (
                <div className="upload-result">
                    {uploadResult.success ? (
                        <div className="success-message">
                            <h4>✅ Upload Successful!</h4>
                            <p>{uploadResult.message}</p>
                            <div className="result-details">
                                <p><strong>Frames processed:</strong> {uploadResult.frame_count}</p>
                                <p><strong>Video path:</strong> {uploadResult.video_path}</p>
                                <p><strong>Data path:</strong> {uploadResult.data_path}</p>
                            </div>
                        </div>
                    ) : (
                        <div className="error-message">
                            <h4>❌ Upload Failed</h4>
                            <p>{uploadResult.message}</p>
                        </div>
                    )}
                </div>
            )}

            <div className="upload-instructions">
                <h4>Instructions:</h4>
                <ul>
                    <li>Record a clear video of the ASL sign being performed correctly</li>
                    <li>Ensure good lighting and the hand is clearly visible</li>
                    <li>Keep the video short (5-10 seconds) for best results</li>
                    <li>Use MP4 format for best compatibility</li>
                    <li>The system will extract hand and pose landmarks from each frame</li>
                </ul>
            </div>
        </div>
    );
};

export default VideoUpload;