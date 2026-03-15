# MediScan Pneumonia Detection System

AI-powered chest X-ray analysis for pneumonia detection using Flask and TensorFlow Lite.

## Quick Start Guide

### 1. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

### Optional: Use MySQL Database

Set these environment variables before running `python app.py`:

```powershell
$env:MYSQL_HOST="127.0.0.1"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_password"
$env:MYSQL_DATABASE="pneumonia_sys"
```

The app will prefer MySQL when `MYSQL_DATABASE` is set.
You can also set `DATABASE_URL` directly, which has highest priority.

The server will start at:
- **Local access**: http://localhost:5000
- **Network access**: http://YOUR_IP:5000

### 3. Use the Application

1. Open your browser and go to http://localhost:5000
2. Click the upload area or drag and drop a chest X-ray image
3. Click "Analyze X-Ray" button
4. View the AI prediction results

## Project Structure

```
pneumonia-sys/
├── app.py                      # Flask backend
├── requirements.txt            # Python dependencies
├── pneumonia_model.tflite      # AI model (25MB)
├── model_metadata.json         # Model specifications
└── public/                     # Frontend files
    ├── index.html              # Main page
    ├── app.js                  # JavaScript logic
    ├── style.css               # Styling
    └── Med.png                 # Logo
```

## Technology Stack

- **Backend**: Flask 3.0 (Python)
- **AI Model**: TensorFlow Lite 2.15
- **Image Processing**: Pillow, NumPy
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)

## Model Information

- **Name**: MediScan Pneumonia Detection v2.0
- **Input**: 224x224 RGB images
- **Output**: Binary classification (NORMAL/PNEUMONIA)
- **Threshold**: 0.5
- **Accuracy**: 84.78%
- **AUC-ROC**: 0.913

## API Endpoints

### GET /
Serves the main HTML page

### POST /analyze
Analyzes uploaded X-ray image

**Request**: `multipart/form-data` with `image` file

**Response**:
```json
{
  "result": "PNEUMONIA" | "NORMAL",
  "confidence": 0.87,
  "probability": 0.87,
  "model_info": {
    "name": "MediScan Pneumonia Detection v2.0",
    "accuracy": "84.78%"
  }
}
```

### GET /health
Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

## Troubleshooting

### Model not loading
- Ensure `pneumonia_model.tflite` is in the root directory
- Check file size is ~25MB
- Verify TensorFlow is installed: `pip install tensorflow==2.15.0`

### Port already in use
Edit `app.py` line 127 to change port:
```python
app.run(host='0.0.0.0', port=5001, debug=True)
```

### Image upload fails
- Check file format (JPG, JPEG, PNG only)
- Ensure file size < 10MB
- Verify browser supports FormData API

## Next Steps (Optional)

- [ ] Add user authentication (login/logout)
- [ ] Implement patient records database
- [ ] Add prediction history
- [ ] Deploy to production server
- [ ] Set up HTTPS/SSL

## Medical Disclaimer

⚠️ This is an AI screening tool for educational and research purposes. Results should always be reviewed by qualified medical professionals. Do not use as the sole basis for medical diagnosis.

## License

For educational and research use only.
