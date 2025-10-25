# ML Backend Setup Guide

This guide will help you set up the Python Flask backend with your trained ASL CNN model.

## Prerequisites

- Python 3.8 or higher
- Your trained model file (`asl_cnn_augmented.keras`)
- Node.js and npm (for the React frontend)

## Quick Setup

### 1. Install Python Dependencies

```bash
cd my-react-app/backend
pip install -r requirements.txt
```

Or run the setup script:
```bash
python setup.py
```

### 2. Place Your Model File

Your trained model should be saved as one of these files:
- `backend/asl_cnn_augmented.keras` (recommended)
- `backend/models/asl_cnn_augmented.keras`
- `backend/asl_model.h5`

If you need to train the model first:
```bash
# Train your model using the provided script
python tidalhack_'25.py
# This will create asl_cnn_augmented.keras
```

### 3. Start the Backend Server

```bash
cd backend
python app.py
```

The server will start on `http://localhost:5000`

### 4. Start the React Frontend

In a new terminal:
```bash
cd my-react-app
npm run start:ml
```

The React app will start on `http://localhost:3000` and connect to your ML backend.

## API Endpoints

Your backend provides these endpoints:

### Health Check
```
GET /health
```
Returns server status and model loading status.

### Predict Sign
```
POST /predict
Content-Type: application/json

{
  "image": "data:image/jpeg;base64,..."
}
```
Returns the predicted ASL letter with confidence scores.

### Analyze Sign (Frontend Compatible)
```
POST /analyze-sign
Content-Type: application/json

{
  "imageDataUrl": "data:image/jpeg;base64,...",
  "targetSign": {
    "word": "HELLO",
    "meaning": "A friendly greeting",
    "tips": "Open hand by your temple..."
  }
}
```
Returns detailed analysis compatible with your React frontend.

### Available Signs
```
GET /available-signs
```
Returns list of ASL letters the model can recognize (A-Y, excluding J and Z).

## Model Information

Your CNN model:
- **Input**: 28x28 grayscale images
- **Output**: 25 classes (A-Y, no J/Z in ASL MNIST)
- **Architecture**: Conv2D → MaxPool → Conv2D → MaxPool → Dense → Dropout → Softmax
- **Training Data**: ASL MNIST dataset

## How It Works

1. **Image Preprocessing**: 
   - Converts webcam image to grayscale
   - Resizes to 28x28 pixels
   - Normalizes pixel values to [0, 1]

2. **Model Prediction**:
   - Runs inference on preprocessed image
   - Returns probability distribution over 25 classes
   - Calculates confidence scores

3. **Result Analysis**:
   - Compares prediction with target sign
   - Generates match percentage
   - Provides detailed feedback

## Testing the Backend

### Test with curl:
```bash
# Health check
curl http://localhost:5000/health

# Test prediction (you'll need a base64 image)
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"image": "data:image/jpeg;base64,/9j/4AAQ..."}'
```

### Test with the React app:
1. Start both backend and frontend
2. You should see "engine: ml-model" in the status
3. Try capturing a sign - you should get ML-powered feedback

## Troubleshooting

### "Model not loaded" error
- Check that your model file exists in the correct location
- Verify the model file isn't corrupted
- Check the Python console for detailed error messages

### "Failed to process image" error
- Ensure the image is properly base64 encoded
- Check that the image format is supported (JPEG, PNG)
- Verify the image isn't too large

### Import errors
- Make sure all requirements are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)
- Try creating a virtual environment

### CORS errors
- The backend includes CORS headers for localhost:3000
- If using a different port, update the CORS configuration in `app.py`

## Performance Optimization

### For Production:
1. Use Gunicorn instead of Flask dev server:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. Enable model caching and batch processing
3. Add request rate limiting
4. Use a reverse proxy (nginx)

### For Development:
- The current setup is optimized for development
- Model loads once on startup
- Images are processed individually

## Extending the Backend

### Adding New Models:
1. Update `ASL_LABELS` in `app.py`
2. Modify preprocessing if input size changes
3. Update the model loading logic

### Adding New Features:
- Hand landmark detection (integrate MediaPipe)
- Multi-hand recognition
- Gesture sequence analysis
- Real-time video processing

## Security Notes

- The backend accepts any image data - add validation for production
- No authentication is implemented - add if needed
- CORS is open for development - restrict for production
- Consider adding request size limits