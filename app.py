"""
Pneumonia Detection System - Enhanced Flask Backend
Medical Web System with Dashboard, Patient Management, and Grad-CAM
"""

from flask import Flask, request, jsonify, send_from_directory
import tensorflow as tf
from PIL import Image
import numpy as np
import os
import re
from datetime import datetime, date
import cv2
import base64
from io import BytesIO
from urllib.parse import quote_plus
from sqlalchemy import func, text
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

try:
    import torch
    from torchvision import models, transforms
    TORCH_AVAILABLE = True
except Exception as e:
    TORCH_AVAILABLE = False
    TORCH_IMPORT_ERROR = str(e)

# Auth / DB
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)

app = Flask(__name__, static_folder='public')

# Basic config - override with environment variables in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')


def build_database_uri():
    # 1) Explicit DATABASE_URL always wins.
    explicit_uri = os.environ.get('DATABASE_URL')
    if explicit_uri:
        return explicit_uri

    # 2) Prefer MySQL when MYSQL_DATABASE is provided.
    mysql_db = os.environ.get('MYSQL_DATABASE')
    if mysql_db:
        mysql_user = os.environ.get('MYSQL_USER', 'root')
        mysql_password = os.environ.get('MYSQL_PASSWORD', '')
        mysql_host = os.environ.get('MYSQL_HOST', '127.0.0.1')
        mysql_port = os.environ.get('MYSQL_PORT', '3306')

        encoded_password = quote_plus(mysql_password)
        return (
            f"mysql+pymysql://{mysql_user}:{encoded_password}"
            f"@{mysql_host}:{mysql_port}/{mysql_db}"
        )

    # 3) Fallback to local SQLite for development.
    return 'sqlite:///pneumonia.db'


app.config['SQLALCHEMY_DATABASE_URI'] = build_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


def masked_db_uri(uri: str) -> str:
    if '://' not in uri or '@' not in uri:
        return uri
    scheme, rest = uri.split('://', 1)
    creds_host = rest.split('@', 1)
    if len(creds_host) != 2 or ':' not in creds_host[0]:
        return uri
    user, _password = creds_host[0].split(':', 1)
    return f"{scheme}://{user}:***@{creds_host[1]}"

# Initialize DB and login manager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Load TensorFlow Lite model at startup
print("Loading TensorFlow Lite model...")
interpreter = tf.lite.Interpreter(model_path="pneumonia_model.tflite")
interpreter.allocate_tensors()

# Get model input/output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print(f"✓ Model loaded successfully")
print(f"  Input shape: {input_details[0]['shape']}")
print(f"  Output shape: {output_details[0]['shape']}")

# Configuration
IMAGE_SIZE = (224, 224)
THRESHOLD = 0.5
CLASS_LABELS = {0: "NORMAL", 1: "PNEUMONIA"}

# Lobe localization model config (PyTorch)
LOBE_LABELS = ["Right Upper", "Right Middle", "Right Lower", "Left Upper", "Left Lower"]
LOBE_MODEL_PATH = os.environ.get('LOBE_MODEL_PATH', 'lobe_model.pt')
LOBE_INPUT_SIZE = (224, 224)

LOBE_MODEL = None
LOBE_DEVICE = None
LOBE_LOAD_ERROR = None

if TORCH_AVAILABLE:
    def build_lobe_model():
        model = models.densenet121(weights=None)
        num_features = model.classifier.in_features
        model.classifier = torch.nn.Linear(num_features, len(LOBE_LABELS))
        return model

    if os.path.exists(LOBE_MODEL_PATH):
        try:
            LOBE_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            LOBE_MODEL = build_lobe_model()
            state = torch.load(LOBE_MODEL_PATH, map_location=LOBE_DEVICE)
            LOBE_MODEL.load_state_dict(state)
            LOBE_MODEL.to(LOBE_DEVICE)
            LOBE_MODEL.eval()
            print(f"✓ Lobe model loaded: {LOBE_MODEL_PATH}")
        except Exception as e:
            LOBE_LOAD_ERROR = str(e)
            LOBE_MODEL = None
            print(f"⚠ Failed to load lobe model: {e}")
    else:
        LOBE_LOAD_ERROR = f"model not found at {LOBE_MODEL_PATH}"
        print(f"⚠ Lobe model not found at {LOBE_MODEL_PATH}")
else:
    LOBE_LOAD_ERROR = TORCH_IMPORT_ERROR

LOBE_TRANSFORM = None
if TORCH_AVAILABLE:
    LOBE_TRANSFORM = transforms.Compose([
        transforms.Resize(LOBE_INPUT_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])


# -----------------------------
# Database models
# -----------------------------


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # Plain text for local testing only!
    role = db.Column(db.String(20), nullable=False, default='doctor')

    def set_password(self, password: str):
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        # Backward-compatible check for existing local plaintext users.
        if self.password == password:
            return True
        return check_password_hash(self.password, password)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    predictions = db.relationship('Prediction', backref='patient', cascade='all, delete-orphan')


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    result = db.Column(db.String(32), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    probability = db.Column(db.Float, nullable=False)
    gradcam_image = db.Column(db.Text, nullable=True)  # Base64 encoded heatmap
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create DB tables (safe to call multiple times)
with app.app_context():
    db.create_all()

    # SQLite-only legacy migration support.
    if db.engine.url.drivername.startswith('sqlite'):
        user_columns = {
            row[1] for row in db.session.execute(text('PRAGMA table_info("user")')).fetchall()
        }
        if 'password' not in user_columns:
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN password VARCHAR(128)'))
            db.session.commit()
            print("✓ Added missing 'password' column to user table")

            if 'password_hash' in user_columns:
                db.session.execute(
                    text('UPDATE "user" SET password = password_hash WHERE password IS NULL')
                )
                db.session.commit()
                print("✓ Backfilled 'password' from legacy 'password_hash' values")
        if 'role' not in user_columns:
            db.session.execute(text('ALTER TABLE "user" ADD COLUMN role VARCHAR(20)'))
            db.session.execute(text("UPDATE \"user\" SET role = 'doctor' WHERE role IS NULL"))
            db.session.commit()
            print("✓ Added missing 'role' column to user table")

    # First-run bootstrap: create a default admin user only if no users exist.
    # Override defaults with environment variables in production.
    if User.query.count() == 0:
        bootstrap_username = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin').strip()
        bootstrap_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')

        if bootstrap_username and bootstrap_password:
            admin_user = User(username=bootstrap_username, role='admin')
            admin_user.set_password(bootstrap_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"✓ Bootstrap admin user created: {bootstrap_username}")
        else:
            print("⚠ Bootstrap admin user was not created: missing username/password")


@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'ok': False, 'error': 'authentication required'}), 401


def validate_auth_fields(username, password, enforce_password_policy=True):
    if not username or not password:
        return 'username and password required'

    username = username.strip()
    if len(username) < 3 or len(username) > 30:
        return 'username must be 3-30 characters'

    if not re.fullmatch(r'[A-Za-z0-9_.-]+', username):
        return 'username can only contain letters, numbers, _, ., -'

    if enforce_password_policy and (len(password) < 6 or len(password) > 128):
        return 'password must be 6-128 characters'

    return None


def get_user_role():
    role = getattr(current_user, 'role', None)
    return role or 'doctor'


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                return unauthorized()
            if get_user_role() not in roles:
                return jsonify({'ok': False, 'error': 'forbidden'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# -----------------------------
# Grad-CAM Visualization Helper
# -----------------------------

def generate_gradcam(img_array, prediction_prob):
    """
    Generate a simple Grad-CAM-style heatmap visualization
    For TFLite models, we'll create a simulated heatmap based on image gradients
    """
    try:
        # Get the original image (remove batch dimension and denormalize)
        img = (img_array[0] * 255).astype(np.uint8)
        
        # Convert to grayscale for gradient calculation
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Calculate gradients (Sobel)
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Normalize gradient magnitude
        gradient_magnitude = cv2.normalize(gradient_magnitude, None, 0, 255, cv2.NORM_MINMAX)
        gradient_magnitude = gradient_magnitude.astype(np.uint8)
        
        # Apply Gaussian blur to smooth the heatmap
        heatmap = cv2.GaussianBlur(gradient_magnitude, (15, 15), 0)
        
        # Apply colormap (COLORMAP_JET for medical visualization)
        heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        
        # Overlay heatmap on original image
        overlay = cv2.addWeighted(img, 0.6, heatmap_colored, 0.4, 0)
        
        # Convert to PIL Image
        overlay_pil = Image.fromarray(overlay)
        
        # Encode to base64
        buffered = BytesIO()
        overlay_pil.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Grad-CAM generation error: {e}")
        return None


class _GradCamHook:
    def __init__(self, target_layer):
        self.activations = None
        self.gradients = None
        self._fwd = target_layer.register_forward_hook(self._forward_hook)
        self._bwd = target_layer.register_full_backward_hook(self._backward_hook)

    def _forward_hook(self, _module, _inputs, output):
        self.activations = output

    def _backward_hook(self, _module, _grad_input, grad_output):
        self.gradients = grad_output[0]

    def remove(self):
        self._fwd.remove()
        self._bwd.remove()

    def cam(self):
        if self.activations is None or self.gradients is None:
            return None
        grads = self.gradients
        activations = self.activations
        weights = grads.mean(dim=(2, 3), keepdim=True)
        cam = (weights * activations).sum(dim=1).squeeze()
        cam = torch.relu(cam)
        cam = cam - cam.min()
        if cam.max() > 0:
            cam = cam / cam.max()
        return cam.detach().cpu().numpy()


def _encode_overlay(overlay_rgb):
    overlay_pil = Image.fromarray(overlay_rgb)
    buffered = BytesIO()
    overlay_pil.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def generate_lobe_predictions_and_gradcam(pil_img):
    if not TORCH_AVAILABLE:
        return None, f"torch not available: {LOBE_LOAD_ERROR}"
    if LOBE_MODEL is None:
        return None, LOBE_LOAD_ERROR or "lobe model not loaded"

    img_resized = pil_img.resize(LOBE_INPUT_SIZE)
    img_rgb = np.array(img_resized, dtype=np.uint8)

    input_tensor = LOBE_TRANSFORM(img_resized).unsqueeze(0).to(LOBE_DEVICE)

    target_layer = LOBE_MODEL.features[-1]
    hook = _GradCamHook(target_layer)

    with torch.set_grad_enabled(True):
        outputs = LOBE_MODEL(input_tensor)
        probs = torch.sigmoid(outputs).detach().cpu().numpy()[0]

        gradcams = {}
        for idx, label in enumerate(LOBE_LABELS):
            LOBE_MODEL.zero_grad()
            retain = idx < len(LOBE_LABELS) - 1
            outputs[0, idx].backward(retain_graph=retain)
            cam = hook.cam()
            if cam is None:
                gradcams[label] = None
                continue
            cam_resized = cv2.resize(cam, (img_rgb.shape[1], img_rgb.shape[0]))
            cam_uint8 = np.uint8(255 * cam_resized)
            heatmap = cv2.applyColorMap(cam_uint8, cv2.COLORMAP_JET)
            heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
            overlay = cv2.addWeighted(img_rgb, 0.6, heatmap_rgb, 0.4, 0)
            gradcams[label] = _encode_overlay(overlay)

    hook.remove()

    prob_map = {label: float(prob) for label, prob in zip(LOBE_LABELS, probs)}
    return {"probs": prob_map, "gradcam": gradcams}, None


# -----------------------------
# Routes
# -----------------------------

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('public', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (CSS, JS, images)"""
    return send_from_directory('public', path)


@app.route('/analyze', methods=['POST'])
@login_required
@require_role('doctor')
def analyze():
    """
    Analyze uploaded X-ray image for pneumonia detection
    
    Expects: multipart/form-data with 'image' file and optional patient info
    Returns: JSON with prediction result, confidence, and Grad-CAM heatmap
    """
    try:
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get patient info from form data
        patient_name = request.form.get('patient_name')
        patient_age = request.form.get('patient_age')
        patient_gender = request.form.get('patient_gender')
        
        # Preprocess image
        print(f"Processing image: {file.filename}")
        
        # Open and convert image
        img = Image.open(file)
        
        # Convert to RGB (handle RGBA, grayscale, etc.)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to model input size (224x224)
        img = img.resize(IMAGE_SIZE)
        
        # Convert to numpy array and normalize (0-255 → 0-1)
        img_array = np.array(img, dtype=np.float32)
        img_array = img_array / 255.0
        
        # Add batch dimension: (224, 224, 3) → (1, 224, 224, 3)
        img_array = np.expand_dims(img_array, axis=0)
        
        # Run inference
        interpreter.set_tensor(input_details[0]['index'], img_array)
        interpreter.invoke()
        
        # Get prediction output
        output = interpreter.get_tensor(output_details[0]['index'])
        probability = float(output[0][0])
        
        # Interpret result
        class_id = 1 if probability > THRESHOLD else 0
        result = CLASS_LABELS[class_id]
        confidence = probability if class_id == 1 else (1 - probability)
        
        print(f"  Prediction: {result} (confidence: {confidence:.2%})")
        
        # Generate Grad-CAM heatmap
        gradcam_img = generate_gradcam(img_array, probability)

        # Lobe model predictions + Grad-CAM (explanation only)
        lobe_payload, lobe_error = generate_lobe_predictions_and_gradcam(img)
        
        # Create or get patient record
        patient = None
        if patient_name:
            try:
                age_int = int(patient_age) if patient_age else None
                patient = Patient(
                    name=patient_name,
                    age=age_int,
                    gender=patient_gender
                )
                db.session.add(patient)
                db.session.flush()  # Get the patient ID
            except Exception as e:
                print(f"Warning: failed to create patient: {e}")
        
        # Save prediction to database
        try:
            pred = Prediction(
                patient_id=patient.id if patient else None,
                user_id=current_user.id if current_user and hasattr(current_user, 'id') and current_user.is_authenticated else None,
                result=result,
                confidence=float(confidence),
                probability=float(probability),
                gradcam_image=gradcam_img
            )
            db.session.add(pred)
            db.session.commit()
        except Exception as e:
            print(f"Warning: failed to save prediction: {e}")
            db.session.rollback()

        # Return result
        response_payload = {
            'result': result,
            'confidence': round(confidence, 4),
            'probability': round(probability, 4),
            'gradcam': gradcam_img,
            'lobe': {
                'available': lobe_payload is not None,
                'error': lobe_error,
                'probs': lobe_payload['probs'] if lobe_payload else None,
                'gradcam': lobe_payload['gradcam'] if lobe_payload else None
            },
            'model_info': {
                'name': 'MediScan Pneumonia Detection v2.0',
                'accuracy': '84.78%'
            }
        }
        return jsonify(response_payload)
    
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': True
    })


# -----------------------------
# Dashboard API
# -----------------------------

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
@require_role('admin', 'doctor')
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Total scans
        total_scans = Prediction.query.count()
        
        # Today's patients (unique patients with scans today)
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        patients_today = db.session.query(func.count(func.distinct(Prediction.patient_id))).\
            filter(Prediction.created_at >= today_start).\
            filter(Prediction.created_at <= today_end).\
            filter(Prediction.patient_id.isnot(None)).\
            scalar()
        
        # Normal vs Pneumonia counts
        normal_count = Prediction.query.filter_by(result='NORMAL').count()
        pneumonia_count = Prediction.query.filter_by(result='PNEUMONIA').count()
        
        return jsonify({
            'total_scans': total_scans,
            'patients_today': patients_today or 0,
            'normal_count': normal_count,
            'pneumonia_count': pneumonia_count
        })
    except Exception as e:
        print(f"Dashboard stats error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/patients/recent', methods=['GET'])
@login_required
@require_role('admin', 'doctor')
def recent_patients():
    """Get recent patient scans for dashboard"""
    try:
        # Get last 10 predictions with patient info
        recent = db.session.query(Prediction, Patient).\
            outerjoin(Patient, Prediction.patient_id == Patient.id).\
            order_by(Prediction.created_at.desc()).\
            limit(10).\
            all()
        
        results = []
        for pred, patient in recent:
            results.append({
                'id': pred.id,
                'patient_name': patient.name if patient else 'Unknown',
                'age': patient.age if patient else None,
                'gender': patient.gender if patient else None,
                'scan_date': pred.created_at.isoformat(),
                'result': pred.result,
                'confidence': round(pred.confidence, 4)
            })
        
        return jsonify(results)
    except Exception as e:
        print(f"Recent patients error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
@login_required
@require_role('admin', 'doctor')
def scan_history():
    """Get all scan history with optional search"""
    try:
        search_query = request.args.get('search', '').strip()
        
        # Base query
        query = db.session.query(Prediction, Patient).\
            outerjoin(Patient, Prediction.patient_id == Patient.id)
        
        # Apply search filter if provided
        if search_query:
            query = query.filter(Patient.name.ilike(f'%{search_query}%'))
        
        # Order by most recent
        results_query = query.order_by(Prediction.created_at.desc()).all()
        
        results = []
        for pred, patient in results_query:
            results.append({
                'id': pred.id,
                'patient_name': patient.name if patient else 'Unknown',
                'age': patient.age if patient else None,
                'gender': patient.gender if patient else None,
                'scan_date': pred.created_at.isoformat(),
                'result': pred.result,
                'confidence': round(pred.confidence, 4)
            })
        
        return jsonify(results)
    except Exception as e:
        print(f"History error: {e}")
        return jsonify({'error': str(e)}), 500


# -----------------------------
# Authentication Routes
# -----------------------------

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    validation_error = validate_auth_fields(username, password, enforce_password_policy=True)
    if validation_error:
        return jsonify({'error': validation_error}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'username exists'}), 400

    user = User(username=username, role='doctor')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'ok': True, 'username': user.username, 'role': user.role or 'doctor'})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    validation_error = validate_auth_fields(username, password, enforce_password_policy=False)
    if validation_error:
        return jsonify({'error': validation_error}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'ok': False, 'error': 'invalid credentials'}), 401

    login_user(user)
    return jsonify({'ok': True, 'username': user.username, 'role': user.role or 'doctor'})


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'ok': True})


@app.route('/me', methods=['GET'])
def me():
    if current_user and hasattr(current_user, 'id') and current_user.is_authenticated:
        return jsonify({
            'logged_in': True,
            'username': current_user.username,
            'id': current_user.id,
            'role': get_user_role()
        })
    return jsonify({'logged_in': False})


# -----------------------------
# Patient CRUD
# -----------------------------

@app.route('/patients', methods=['GET'])
@login_required
@require_role('doctor')
def list_patients():
    patients = Patient.query.order_by(Patient.created_at.desc()).all()
    out = []
    for p in patients:
        out.append({
            'id': p.id,
            'name': p.name,
            'age': p.age,
            'gender': p.gender,
            'dob': p.dob.isoformat() if p.dob else None,
            'notes': p.notes
        })
    return jsonify(out)


@app.route('/patients', methods=['POST'])
@login_required
@require_role('doctor')
def create_patient():
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': 'name required'}), 400
    
    age = data.get('age')
    gender = data.get('gender')
    dob = None
    if data.get('dob'):
        try:
            dob = datetime.fromisoformat(data.get('dob')).date()
        except Exception:
            dob = None

    p = Patient(name=name, age=age, gender=gender, dob=dob, notes=data.get('notes'))
    db.session.add(p)
    db.session.commit()
    return jsonify({'id': p.id, 'name': p.name})


@app.route('/patients/<int:pid>', methods=['GET'])
@login_required
@require_role('doctor')
def get_patient(pid):
    p = Patient.query.get_or_404(pid)
    return jsonify({
        'id': p.id,
        'name': p.name,
        'age': p.age,
        'gender': p.gender,
        'dob': p.dob.isoformat() if p.dob else None,
        'notes': p.notes
    })


@app.route('/patients/<int:pid>', methods=['PUT'])
@login_required
@require_role('doctor')
def update_patient(pid):
    p = Patient.query.get_or_404(pid)
    data = request.get_json() or {}
    if 'name' in data:
        p.name = data.get('name')
    if 'age' in data:
        p.age = data.get('age')
    if 'gender' in data:
        p.gender = data.get('gender')
    if 'notes' in data:
        p.notes = data.get('notes')
    if 'dob' in data:
        try:
            p.dob = datetime.fromisoformat(data.get('dob')).date()
        except Exception:
            pass
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/patients/<int:pid>', methods=['DELETE'])
@login_required
@require_role('doctor')
def delete_patient(pid):
    p = Patient.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({'ok': True})


@app.route('/patients/<int:pid>/predictions', methods=['GET'])
@login_required
@require_role('doctor')
def patient_predictions(pid):
    p = Patient.query.get_or_404(pid)
    out = []
    for pr in p.predictions:
        out.append({
            'id': pr.id,
            'result': pr.result,
            'confidence': pr.confidence,
            'probability': pr.probability,
            'created_at': pr.created_at.isoformat()
        })
    return jsonify(out)


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🏥 MediScan Pneumonia Detection System")
    print("="*50)
    print(f"Database: {masked_db_uri(app.config['SQLALCHEMY_DATABASE_URI'])}")
    print(f"Server running at: http://localhost:5000")
    print(f"Access from network: http://<your-ip>:5000")
    print("="*50 + "\n")
    
    app.run(
        host='0.0.0.0',  # Allow network access
        port=5000,
        debug=True       # Enable auto-reload during development
    )
