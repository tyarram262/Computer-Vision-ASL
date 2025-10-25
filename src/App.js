import { useEffect, useState } from 'react';
import './App.css';
import RealtimeAnalysis from './components/RealtimeAnalysis';
import VideoUpload from './components/VideoUpload';
import ConfigStatus from './components/ConfigStatus';
import fastApiService from './services/fastApiService';

function App() {
  const [availableSigns, setAvailableSigns] = useState([]);
  const [selectedSign, setSelectedSign] = useState(null);
  const [currentScore, setCurrentScore] = useState(0);
  const [currentFeedback, setCurrentFeedback] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [loading, setLoading] = useState(true);

  // Load available signs on startup
  useEffect(() => {
    const loadSigns = async () => {
      try {
        const result = await fastApiService.getAvailableSigns();
        if (result.success) {
          setAvailableSigns(result.signs);
          if (result.signs.length > 0) {
            setSelectedSign(result.signs[0]);
          }
        }
      } catch (error) {
        console.error('Error loading signs:', error);
      } finally {
        setLoading(false);
      }
    };

    loadSigns();
  }, []);

  const handleScoreUpdate = (score) => {
    setCurrentScore(score);
  };

  const handleFeedbackUpdate = (feedback) => {
    setCurrentFeedback(feedback);
  };

  const handleUploadComplete = (result) => {
    // Refresh available signs
    const loadSigns = async () => {
      const signsResult = await fastApiService.getAvailableSigns();
      if (signsResult.success) {
        setAvailableSigns(signsResult.signs);
        // Select the newly uploaded sign
        const newSign = signsResult.signs.find(s => s.name === result.video_path?.split('/').pop()?.replace('.mp4', ''));
        if (newSign) {
          setSelectedSign(newSign);
        }
      }
    };

    loadSigns();
    setShowUpload(false);
  };

  if (loading) {
    return (
      <div className="App">
        <div className="loading-screen">
          <h1>ASL Form Correction</h1>
          <p>Loading available signs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <ConfigStatus />
      <header className="App-header">
        <div className="header-content">
          <div>
            <h1>Real-time ASL Form Correction</h1>
            <p className="muted">Practice ASL signs with instant AI-powered feedback</p>
          </div>
          <div className="header-controls">
            <button
              className="upload-button"
              onClick={() => setShowUpload(!showUpload)}
              title="Upload new target video"
            >
              📤 Upload Video
            </button>
          </div>
        </div>
      </header>

      <div className="app-container">
        {/* Sign Selection */}
        <div className="panel sign-selection">
          <h3>Select Sign to Practice</h3>
          {availableSigns.length > 0 ? (
            <div className="sign-selector">
              {availableSigns.map((sign) => (
                <button
                  key={sign.name}
                  onClick={() => setSelectedSign(sign)}
                  className={`sign-option ${selectedSign?.name === sign.name ? 'selected' : ''}`}
                >
                  {sign.name.toUpperCase()}
                </button>
              ))}
            </div>
          ) : (
            <div className="no-signs">
              <p>No signs available. Upload a target video to get started.</p>
              <button
                className="primary"
                onClick={() => setShowUpload(true)}
              >
                Upload First Video
              </button>
            </div>
          )}
        </div>

        {/* Upload Panel */}
        {showUpload && (
          <div className="panel upload-panel">
            <VideoUpload onUploadComplete={handleUploadComplete} />
          </div>
        )}

        {/* Real-time Analysis */}
        {selectedSign && !showUpload && (
          <div className="panel analysis-panel">
            <RealtimeAnalysis
              selectedSign={selectedSign}
              onScoreUpdate={handleScoreUpdate}
              onFeedbackUpdate={handleFeedbackUpdate}
            />
          </div>
        )}

        {/* Results Summary */}
        {selectedSign && !showUpload && (
          <div className="panel results-panel">
            <div className="results-grid">
              <div className="score-summary">
                <h4>Current Score</h4>
                <div className="score-display">
                  <span className="score-value">{currentScore}%</span>
                </div>
              </div>

              {currentFeedback && (
                <div className="feedback-summary">
                  <h4>Latest Feedback</h4>
                  <p className="feedback-text">{currentFeedback}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;