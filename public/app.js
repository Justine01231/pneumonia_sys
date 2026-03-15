// MediScan Medical Web System - JavaScript

// Global state
let selectedFile = null;
let currentPatient = {
  name: '',
  age: '',
  gender: ''
};
let authState = {
  loggedIn: false,
  username: null,
  role: null
};

const PROTECTED_PAGES = new Set(['dashboard', 'upload', 'history', 'about', 'settings']);
const ROLE_PAGES = {
  admin: new Set(['dashboard', 'history', 'about', 'settings']),
  doctor: new Set(['dashboard', 'upload', 'history', 'about', 'settings'])
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
  console.log('MediScan Medical System initialized');
  setupNavigation();
  setupAuth();
  setupUploadWorkflow();
  setupTheme();
  setupHistorySearch();
  await initAuth();

  // Auto-refresh dashboard every 30 seconds
  setInterval(() => {
    if (authState.loggedIn) {
      loadDashboardData();
    }
  }, 30000);
});

// ==================== NAVIGATION ====================

function setupNavigation() {
  const menuItems = document.querySelectorAll('.menu-item');

  menuItems.forEach(item => {
    item.addEventListener('click', () => {
      const pageName = item.getAttribute('data-page');
      navigateToPage(pageName);
    });
  });
}

function navigateToPage(pageName) {
  if (PROTECTED_PAGES.has(pageName) && !authState.loggedIn) {
    pageName = 'auth';
    showAuthMessage('Please login first to continue.', 'error');
  } else if (PROTECTED_PAGES.has(pageName) && authState.loggedIn && !canAccessPage(pageName)) {
    pageName = 'dashboard';
    showAuthMessage('Your account does not have access to that page.', 'error');
  }

  // Update menu active state
  document.querySelectorAll('.menu-item').forEach(item => {
    item.classList.remove('active');
  });
  const activeMenu = document.querySelector(`[data-page="${pageName}"]`);
  if (activeMenu) {
    activeMenu.classList.add('active');
  }

  // Update page visibility
  document.querySelectorAll('.page').forEach(page => {
    page.classList.remove('active');
  });
  const nextPage = document.getElementById(`${pageName}-page`);
  if (nextPage) {
    nextPage.classList.add('active');
  }

  // Load page-specific data
  if (pageName === 'dashboard' && authState.loggedIn) {
    loadDashboardData();
  } else if (pageName === 'history' && authState.loggedIn) {
    loadHistory();
  }
}

function updateMenuLocks() {
  document.querySelectorAll('.menu-item').forEach(item => {
    const pageName = item.getAttribute('data-page');
    if (PROTECTED_PAGES.has(pageName) && !authState.loggedIn) {
      item.classList.add('locked');
      item.classList.remove('hidden');
      return;
    }
    if (authState.loggedIn && PROTECTED_PAGES.has(pageName) && !canAccessPage(pageName)) {
      item.classList.add('hidden');
      item.classList.add('locked');
    } else {
      item.classList.remove('locked');
      item.classList.remove('hidden');
    }
  });
}

// ==================== AUTH ====================

function setupAuth() {
  const showLoginBtn = document.getElementById('showLoginBtn');
  const showSignupBtn = document.getElementById('showSignupBtn');
  const toSignupLink = document.getElementById('toSignupLink');
  const toLoginLink = document.getElementById('toLoginLink');
  const loginForm = document.getElementById('loginForm');
  const signupForm = document.getElementById('signupForm');
  const logoutBtn = document.getElementById('logoutBtn');

  showLoginBtn.addEventListener('click', () => showAuthForm('login'));
  showSignupBtn.addEventListener('click', () => showAuthForm('signup'));

  toSignupLink.addEventListener('click', (event) => {
    event.preventDefault();
    showAuthForm('signup');
  });

  toLoginLink.addEventListener('click', (event) => {
    event.preventDefault();
    showAuthForm('login');
  });

  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    const validationError = validateCredentials(username, password);
    if (validationError) {
      showAuthMessage(validationError, 'error');
      return;
    }

    try {
      const response = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'same-origin'
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Login failed');
      }

      showAuthMessage('Login successful.', 'success');
      authState.loggedIn = true;
      authState.username = data.username;
      authState.role = data.role || null;
      setAuthUI();
      navigateToPage('dashboard');
      loginForm.reset();
      signupForm.reset();
    } catch (error) {
      showAuthMessage(error.message, 'error');
    }
  });

  signupForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const username = document.getElementById('signupUsername').value.trim();
    const password = document.getElementById('signupPassword').value;
    const confirmPassword = document.getElementById('signupConfirmPassword').value;

    const validationError = validateCredentials(username, password);
    if (validationError) {
      showAuthMessage(validationError, 'error');
      return;
    }

    if (password !== confirmPassword) {
      showAuthMessage('Passwords do not match.', 'error');
      return;
    }

    try {
      const response = await fetch('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: 'same-origin'
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Signup failed');
      }

      showAuthMessage('Signup complete. You can login now.', 'success');
      showAuthForm('login');
      document.getElementById('loginUsername').value = username;
      document.getElementById('loginPassword').focus();
    } catch (error) {
      showAuthMessage(error.message, 'error');
    }
  });

  logoutBtn.addEventListener('click', async () => {
    try {
      const response = await fetch('/logout', {
        method: 'POST',
        credentials: 'same-origin'
      });
      if (!response.ok) {
        throw new Error('Logout failed');
      }
    } catch (error) {
      console.error(error);
    } finally {
      authState.loggedIn = false;
      authState.username = null;
      authState.role = null;
      setAuthUI();
      navigateToPage('auth');
      showAuthMessage('You have logged out.', 'success');
    }
  });
}

async function initAuth() {
  try {
    const response = await fetch('/me', { credentials: 'same-origin' });
    const data = await response.json();

    authState.loggedIn = Boolean(data.logged_in);
    authState.username = data.username || null;
    authState.role = data.role || null;
  } catch (error) {
    authState.loggedIn = false;
    authState.username = null;
    authState.role = null;
  }

  setAuthUI();
  navigateToPage(authState.loggedIn ? 'dashboard' : 'auth');
}

function setAuthUI() {
  const userBadge = document.getElementById('userBadge');
  const logoutBtn = document.getElementById('logoutBtn');

  if (authState.loggedIn) {
    const roleLabel = authState.role ? ` (${authState.role})` : '';
    userBadge.textContent = `Signed in: ${authState.username}${roleLabel}`;
    logoutBtn.classList.remove('hidden');
  } else {
    userBadge.textContent = 'Not signed in';
    logoutBtn.classList.add('hidden');
  }

  updateMenuLocks();
}

function showAuthForm(mode) {
  const showLogin = mode === 'login';
  const loginForm = document.getElementById('loginForm');
  const signupForm = document.getElementById('signupForm');
  const showLoginBtn = document.getElementById('showLoginBtn');
  const showSignupBtn = document.getElementById('showSignupBtn');

  if (showLogin) {
    loginForm.classList.remove('hidden');
    signupForm.classList.add('hidden');
    showLoginBtn.classList.add('active');
    showSignupBtn.classList.remove('active');
  } else {
    signupForm.classList.remove('hidden');
    loginForm.classList.add('hidden');
    showSignupBtn.classList.add('active');
    showLoginBtn.classList.remove('active');
  }
}

function showAuthMessage(message, type) {
  const authMessage = document.getElementById('authMessage');
  authMessage.textContent = message;
  authMessage.classList.remove('hidden', 'error', 'success');
  authMessage.classList.add(type);
}

function validateCredentials(username, password) {
  const usernamePattern = /^[A-Za-z0-9_.-]+$/;

  if (!username || !password) {
    return 'Username and password are required.';
  }
  if (username.length < 3 || username.length > 30) {
    return 'Username must be 3-30 characters.';
  }
  if (!usernamePattern.test(username)) {
    return 'Username can only contain letters, numbers, _, ., -.';
  }
  if (password.length < 6 || password.length > 128) {
    return 'Password must be 6-128 characters.';
  }

  return null;
}

function handleUnauthorized() {
  authState.loggedIn = false;
  authState.username = null;
  authState.role = null;
  setAuthUI();
  navigateToPage('auth');
  showAuthMessage('Session expired. Please login again.', 'error');
}

function canAccessPage(pageName) {
  if (pageName === 'auth') {
    return true;
  }
  const role = authState.role || 'doctor';
  const allowedPages = ROLE_PAGES[role] || ROLE_PAGES.doctor;
  return allowedPages.has(pageName);
}

// ==================== DASHBOARD ====================

async function loadDashboardData() {
  console.log('Loading dashboard data...');
  try {
    // Load statistics
    console.log('Fetching dashboard stats...');
    const statsResponse = await fetch('/api/dashboard/stats', { credentials: 'same-origin' });
    console.log('Stats response status:', statsResponse.status);

    if (statsResponse.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!statsResponse.ok) {
      const errorText = await statsResponse.text();
      console.error('Stats API error:', errorText);
      throw new Error(`Stats API failed: ${statsResponse.status}`);
    }

    const stats = await statsResponse.json();
    console.log('Stats data:', stats);

    document.getElementById('totalScans').textContent = stats.total_scans || 0;
    document.getElementById('patientsToday').textContent = stats.patients_today || 0;
    document.getElementById('normalCount').textContent = stats.normal_count || 0;
    document.getElementById('pneumoniaCount').textContent = stats.pneumonia_count || 0;

    // Load recent patients
    console.log('Fetching recent patients...');
    const recentResponse = await fetch('/api/patients/recent', { credentials: 'same-origin' });
    console.log('Recent patients response status:', recentResponse.status);

    if (recentResponse.status === 401) {
      handleUnauthorized();
      return;
    }

    if (!recentResponse.ok) {
      const errorText = await recentResponse.text();
      console.error('Recent patients API error:', errorText);
      throw new Error(`Recent patients API failed: ${recentResponse.status}`);
    }

    const recentPatients = await recentResponse.json();
    console.log('Recent patients data:', recentPatients);
    console.log('Number of recent patients:', recentPatients.length);

    const tableBody = document.getElementById('recentPatientsTable');

    if (!tableBody) {
      console.error('Table body element not found!');
      return;
    }

    if (recentPatients.length === 0) {
      console.log('No recent patients, showing empty message');
      tableBody.innerHTML = '<tr><td colspan="6" class="no-data">No recent scans</td></tr>';
    } else {
      console.log('Rendering', recentPatients.length, 'patients');
      tableBody.innerHTML = recentPatients.map(patient => `
                <tr>
                    <td>${patient.patient_name}</td>
                    <td>${patient.age || 'N/A'}</td>
                    <td>${patient.gender || 'N/A'}</td>
                    <td>${formatDate(patient.scan_date)}</td>
                    <td><span class="result-badge ${patient.result.toLowerCase()}">${patient.result}</span></td>
                    <td>${(patient.confidence * 100).toFixed(1)}%</td>
                </tr>
            `).join('');
      console.log('Table updated successfully');
    }
  } catch (error) {
    console.error('Error loading dashboard data:', error);
    console.error('Error stack:', error.stack);

    // Show error in UI
    const tableBody = document.getElementById('recentPatientsTable');
    if (tableBody) {
      tableBody.innerHTML = '<tr><td colspan="6" class="no-data" style="color: red;">Error loading data. Check console for details.</td></tr>';
    }
  }
}

// ==================== UPLOAD WORKFLOW ====================

function setupUploadWorkflow() {
  const patientForm = document.getElementById('patientForm');
  const nameInput = document.getElementById('patientName');
  const ageInput = document.getElementById('patientAge');
  const genderSelect = document.getElementById('patientGender');
  const nextBtn = document.getElementById('nextToUploadBtn');
  const imageInput = document.getElementById('imageInput');
  const uploadArea = document.getElementById('uploadArea');

  // Real-time form validation
  function validateForm() {
    const isValid = nameInput.value.trim() !== '' &&
      ageInput.value !== '' &&
      genderSelect.value !== '';
    nextBtn.disabled = !isValid;
  }

  nameInput.addEventListener('input', validateForm);
  ageInput.addEventListener('input', validateForm);
  genderSelect.addEventListener('change', validateForm);

  // Next button - move to step 2
  nextBtn.addEventListener('click', () => {
    currentPatient = {
      name: nameInput.value.trim(),
      age: ageInput.value,
      gender: genderSelect.value
    };

    // Show patient summary
    document.getElementById('patientSummary').innerHTML = `
            <h3><i class="fas fa-user"></i> Patient Information</h3>
            <p><strong>Name:</strong> ${currentPatient.name}</p>
            <p><strong>Age:</strong> ${currentPatient.age} years</p>
            <p><strong>Gender:</strong> ${currentPatient.gender}</p>
        `;

    // Switch to step 2
    document.getElementById('step1').classList.remove('active');
    document.getElementById('step2').classList.add('active');
    document.getElementById('step1-indicator').classList.remove('active');
    document.getElementById('step2-indicator').classList.add('active');
  });

  // File input change
  imageInput.addEventListener('change', handleFileSelect);

  // Drag and drop
  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
  });

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
  });

  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    handleFile(file);
  }
}

function handleFile(file) {
  // Validate file type
  const validTypes = ['image/jpeg', 'image/jpg', 'image/png'];
  if (!validTypes.includes(file.type)) {
    alert('Please upload a valid image file (JPG, JPEG, or PNG)');
    return;
  }

  // Validate file size (10MB max)
  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    alert('File size must be less than 10MB');
    return;
  }

  selectedFile = file;

  // Show preview
  const reader = new FileReader();
  reader.onload = (e) => {
    const preview = document.getElementById('imagePreview');
    preview.src = e.target.result;

    document.getElementById('previewSection').classList.remove('hidden');
    document.getElementById('analyzeBtn').disabled = false;
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  selectedFile = null;
  document.getElementById('imageInput').value = '';
  document.getElementById('previewSection').classList.add('hidden');
  document.getElementById('analyzeBtn').disabled = true;
  document.getElementById('resultSection').classList.add('hidden');
}

async function analyzeImage() {
  if (!selectedFile) {
    alert('Please select an image first');
    return;
  }

  // Hide previous results
  document.getElementById('resultSection').classList.add('hidden');

  // Show loading
  document.getElementById('loadingSection').classList.remove('hidden');
  document.getElementById('analyzeBtn').disabled = true;

  try {
    // Create form data
    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('patient_name', currentPatient.name);
    formData.append('patient_age', currentPatient.age);
    formData.append('patient_gender', currentPatient.gender);

    // Send to Flask backend
    const response = await fetch('/analyze', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin'
    });

    if (response.status === 401) {
      handleUnauthorized();
      return;
    }

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

    const data = await response.json();

    // Display results
    displayResults(data);

  } catch (error) {
    console.error('Analysis error:', error);
    alert('Analysis failed. Please try again.\n\nError: ' + error.message);
  } finally {
    // Hide loading
    document.getElementById('loadingSection').classList.add('hidden');
    document.getElementById('analyzeBtn').disabled = false;
  }
}

function displayResults(data) {
  // Show result section
  document.getElementById('resultSection').classList.remove('hidden');

  // Set diagnosis
  const diagnosisValue = document.getElementById('diagnosisValue');
  diagnosisValue.textContent = data.result;

  // Color code based on result
  const diagnosisBox = document.getElementById('diagnosisBox');
  if (data.result === 'PNEUMONIA') {
    diagnosisBox.className = 'diagnosis pneumonia';
  } else {
    diagnosisBox.className = 'diagnosis normal';
  }

  // Set confidence
  const confidencePercent = (data.confidence * 100).toFixed(1);
  document.getElementById('confidenceText').textContent = confidencePercent + '%';

  const confidenceFill = document.getElementById('confidenceFill');
  confidenceFill.style.width = confidencePercent + '%';

  // Color code confidence bar
  if (data.confidence >= 0.8) {
    confidenceFill.style.background = 'linear-gradient(90deg, #4CAF50, #45a049)';
  } else if (data.confidence >= 0.6) {
    confidenceFill.style.background = 'linear-gradient(90deg, #FFC107, #FFB300)';
  } else {
    confidenceFill.style.background = 'linear-gradient(90deg, #FF9800, #F57C00)';
  }

  // Display Grad-CAM if available
  if (data.gradcam) {
    document.getElementById('gradcamSection').classList.remove('hidden');
    document.getElementById('gradcamImage').src = data.gradcam;
  } else {
    document.getElementById('gradcamSection').classList.add('hidden');
  }

  // Lobe probabilities + Grad-CAM per lobe
  const lobeSection = document.getElementById('lobeSection');
  const lobeTable = document.getElementById('lobeTable');
  const lobeSelect = document.getElementById('lobeSelect');
  const lobeGradcamImage = document.getElementById('lobeGradcamImage');
  const lobeUnavailable = document.getElementById('lobeUnavailable');

  if (data.lobe && data.lobe.available && data.lobe.probs) {
    const entries = Object.entries(data.lobe.probs);
    entries.sort((a, b) => b[1] - a[1]);

    lobeTable.innerHTML = entries.map(([name, value]) => `
        <div class="lobe-item">
          <span class="lobe-name">${name}</span>
          <span class="lobe-value">${(value * 100).toFixed(1)}%</span>
        </div>
      `).join('');

    lobeSelect.innerHTML = entries.map(([name]) => `<option value="${name}">${name}</option>`).join('');

    const updateLobeImage = () => {
      const selected = lobeSelect.value;
      const img = data.lobe.gradcam ? data.lobe.gradcam[selected] : null;
      if (img) {
        lobeGradcamImage.src = img;
        lobeGradcamImage.classList.remove('hidden');
        lobeUnavailable.classList.add('hidden');
      } else {
        lobeGradcamImage.classList.add('hidden');
        lobeUnavailable.textContent = 'Lobe Grad-CAM unavailable.';
        lobeUnavailable.classList.remove('hidden');
      }
    };

    lobeSelect.onchange = updateLobeImage;
    lobeSelect.value = entries[0][0];
    updateLobeImage();

    lobeUnavailable.classList.add('hidden');
    lobeSection.classList.remove('hidden');
  } else {
    lobeTable.innerHTML = '';
    lobeSelect.innerHTML = '';
    lobeGradcamImage.classList.add('hidden');
    lobeUnavailable.textContent = data.lobe && data.lobe.error
      ? `Lobe model unavailable: ${data.lobe.error}`
      : 'Lobe model unavailable.';
    lobeUnavailable.classList.remove('hidden');
    lobeSection.classList.remove('hidden');
  }

  // Set model info
  document.getElementById('modelName').textContent = data.model_info.name;
  document.getElementById('modelAccuracy').textContent = data.model_info.accuracy;

  // Scroll to results
  document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth' });
}

function analyzeAnother() {
  clearImage();
  document.getElementById('resultSection').classList.add('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function backToPatientInfo() {
  // Switch back to step 1
  document.getElementById('step2').classList.remove('active');
  document.getElementById('step1').classList.add('active');
  document.getElementById('step2-indicator').classList.remove('active');
  document.getElementById('step1-indicator').classList.add('active');

  // Clear upload
  clearImage();
}

// ==================== HISTORY ====================

function setupHistorySearch() {
  const searchInput = document.getElementById('historySearch');

  searchInput.addEventListener('input', (e) => {
    const searchTerm = e.target.value.trim();
    loadHistory(searchTerm);
  });
}

async function loadHistory(searchTerm = '') {
  try {
    const url = searchTerm ? `/api/history?search=${encodeURIComponent(searchTerm)}` : '/api/history';
    const response = await fetch(url, { credentials: 'same-origin' });

    if (response.status === 401) {
      handleUnauthorized();
      return;
    }

    const history = await response.json();

    const tableBody = document.getElementById('historyTable');

    if (history.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="6" class="no-data">No scan history</td></tr>';
    } else {
      tableBody.innerHTML = history.map(record => `
                <tr>
                    <td>${record.patient_name}</td>
                    <td>${record.age || 'N/A'}</td>
                    <td>${record.gender || 'N/A'}</td>
                    <td>${formatDate(record.scan_date)}</td>
                    <td><span class="result-badge ${record.result.toLowerCase()}">${record.result}</span></td>
                    <td>${(record.confidence * 100).toFixed(1)}%</td>
                </tr>
            `).join('');
    }
  } catch (error) {
    console.error('Error loading history:', error);
  }
}

// ==================== THEME ====================

function setupTheme() {
  const themeButtons = document.querySelectorAll('.theme-btn');

  // Load saved theme
  const savedTheme = localStorage.getItem('theme') || 'light';
  applyTheme(savedTheme);

  // Theme button click handlers
  themeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.getAttribute('data-theme');
      applyTheme(theme);
      localStorage.setItem('theme', theme);
    });
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);

  // Update button states
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.getAttribute('data-theme') === theme) {
      btn.classList.add('active');
    }
  });
}

// ==================== UTILITY FUNCTIONS ====================

function formatDate(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) {
    return 'Just now';
  } else if (diffMins < 60) {
    return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
  } else if (diffHours < 24) {
    return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  } else if (diffDays < 7) {
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  } else {
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
