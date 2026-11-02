/**
 * TestFlow API Client
 * Seamlessly interfaces with FastAPI backend with JWT token management
 */

const API_BASE = '/api/v1';

export const authState = {
  token: localStorage.getItem('tf_token') || null,
  user: JSON.parse(localStorage.getItem('tf_user') || 'null'),
  
  setAuth(token, user) {
    this.token = token;
    this.user = user;
    localStorage.setItem('tf_token', token);
    localStorage.setItem('tf_user', JSON.stringify(user));
  },
  
  clear() {
    this.token = null;
    this.user = null;
    localStorage.removeItem('tf_token');
    localStorage.removeItem('tf_user');
  },
  
  isAuthenticated() {
    return !!this.token;
  }
};

export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  if (authState.token) {
    headers['Authorization'] = `Bearer ${authState.token}`;
  }

  // Handle FormData
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  try {
    const res = await fetch(url, { ...options, headers });
    
    if (res.status === 401) {
      authState.clear();
      window.dispatchEvent(new CustomEvent('auth-changed'));
      throw new Error('Authentication expired or unauthorized. Please log in.');
    }

    if (!res.ok) {
      let errMsg = `Request failed (${res.status})`;
      try {
        const errorData = await res.json();
        errMsg = errorData.detail || errorData.message || errMsg;
      } catch (e) {
        // Not JSON
      }
      throw new Error(errMsg);
    }

    // Check if 204 No Content
    if (res.status === 204) return null;
    return await res.json();
  } catch (err) {
    console.error(`API Error [${endpoint}]:`, err);
    throw err;
  }
}

// API Endpoints
export const api = {
  // Auth
  async login(email, password) {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
    authState.setAuth(data.access_token, data.user);
    window.dispatchEvent(new CustomEvent('auth-changed'));
    return data;
  },

  async getMe() {
    return await apiRequest('/auth/me');
  },

  logout() {
    authState.clear();
    window.dispatchEvent(new CustomEvent('auth-changed'));
  },

  // Dashboard
  async getOverview() {
    return await apiRequest('/dashboard/overview');
  },

  async getTestingDashboard() {
    return await apiRequest('/dashboard/testing');
  },

  async getQualityDashboard() {
    return await apiRequest('/dashboard/quality');
  },

  async getAttendanceReport() {
    return await apiRequest('/dashboard/reports/attendance');
  },

  // Batches
  async getBatches() {
    return await apiRequest('/batches/');
  },

  async getBatchItems(batchId, status = null) {
    const query = status ? `?status_filter=${status}` : '';
    return await apiRequest(`/batches/${batchId}/items${query}`);
  },

  async createBatch(batchData) {
    return await apiRequest('/batches/', {
      method: 'POST',
      body: JSON.stringify(batchData)
    });
  },

  async bulkImportSerials(batchId, serialNumbers) {
    return await apiRequest(`/batches/${batchId}/serials/bulk-import`, {
      method: 'POST',
      body: JSON.stringify({ serial_numbers: serialNumbers })
    });
  },

  async autoGenerateSerials(batchId, prefix, count) {
    return await apiRequest(`/batches/${batchId}/serials/auto-generate`, {
      method: 'POST',
      body: JSON.stringify({ prefix, count })
    });
  },

  async getClients() {
    return await apiRequest('/clients/');
  },

  async getProducts() {
    return await apiRequest('/products/');
  },

  // Testing
  async getMyQueue() {
    return await apiRequest('/testing/my-queue');
  },

  async getTestTemplates() {
    return await apiRequest('/test-templates/');
  },

  async getTemplate(id) {
    return await apiRequest(`/test-templates/${id}`);
  },

  async submitManualTest(payload) {
    return await apiRequest('/testing/manual', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  async uploadBenchCsv(templateId, file) {
    const formData = new FormData();
    formData.append('file', file);
    return await apiRequest(`/testing/upload-bench-csv?template_id=${templateId}`, {
      method: 'POST',
      body: formData
    });
  },

  async getBatchProgress(batchId) {
    return await apiRequest(`/testing/batch-progress/${batchId}`);
  },

  // Quality
  async getDefects(status = null) {
    const query = status !== null ? `?is_resolved=${status}` : '';
    return await apiRequest(`/quality/defects${query}`);
  },

  async submitDisposition(batchItemId, decision, remarks = '') {
    return await apiRequest('/quality/disposition', {
      method: 'POST',
      body: JSON.stringify({
        batch_item_id: batchItemId,
        decision,
        remarks
      })
    });
  },

  async logDefect(defectData) {
    return await apiRequest('/quality/defects', {
      method: 'POST',
      body: JSON.stringify(defectData)
    });
  },

  async getQualityHistory(batchItemId) {
    return await apiRequest(`/quality/history/${batchItemId}`);
  },

  async getDefectSummary() {
    return await apiRequest('/quality/defect-summary');
  },

  // Dispatch
  async getDispatches() {
    return await apiRequest('/dispatch/');
  },

  async createDispatch(payload) {
    return await apiRequest('/dispatch/', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  // Traceability
  async getTraceability(serialNumber) {
    return await apiRequest(`/traceability/${encodeURIComponent(serialNumber.trim().toUpperCase())}`);
  },

  // Attendance
  async getTodayAttendance() {
    return await apiRequest('/attendance/today');
  },

  async punchIn() {
    return await apiRequest('/attendance/punch-in', { method: 'POST' });
  },

  async punchOut() {
    return await apiRequest('/attendance/punch-out', { method: 'POST' });
  }
};
