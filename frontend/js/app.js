import { api, authState } from './api.js';

// State
let currentTab = 'dashboard';
let yieldChart = null;
let paretoChart = null;

// Toast helper
export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const borderColors = {
    success: 'border-emerald-500/80 text-emerald-800 bg-white shadow-[0_4px_20px_rgba(16,185,129,0.15)]',
    error: 'border-[#E7473C] text-[#E7473C] bg-white shadow-[0_4px_20px_rgba(231,71,60,0.2)]',
    info: 'border-zinc-300 text-zinc-800 bg-white shadow-[0_4px_20px_rgba(0,0,0,0.08)]',
    warning: 'border-amber-500 text-amber-800 bg-white shadow-[0_4px_20px_rgba(245,158,11,0.15)]'
  };

  toast.className = `flex items-center gap-3 px-4 py-3 rounded-xl border text-xs font-semibold transition-all transform duration-300 translate-y-2 opacity-0 ${borderColors[type] || borderColors.info}`;
  toast.innerHTML = `
    <span class="w-2 h-2 rounded-full ${type === 'success' ? 'bg-emerald-500' : type === 'error' ? 'bg-[#E7473C]' : 'bg-zinc-400'}"></span>
    <span class="flex-1">${message}</span>
    <button class="ml-2 text-zinc-400 hover:text-zinc-700 font-bold" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal helper
export function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    if (window.lucide) window.lucide.createIcons();
  }
}

export function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}
window.closeModal = closeModal;
window.openModal = openModal;

// Quick login personas (All 7 Roles Supported)
const PERSONAS = [
  { label: 'Operations Manager', email: 'emp-syn-001@testflow-demo.local', role: 'OPERATIONS_MGR', pass: 'DemoPass123!' },
  { label: 'QA Inspector', email: 'emp-syn-013@testflow-demo.local', role: 'QA_INSPECTOR', pass: 'DemoPass123!' },
  { label: 'Store Keeper', email: 'emp-syn-014@testflow-demo.local', role: 'STORE_KEEPER', pass: 'DemoPass123!' },
  { label: 'Test Lead', email: 'emp-syn-005@testflow-demo.local', role: 'TEST_SUPERVISOR', pass: 'DemoPass123!' },
  { label: 'Test Tech', email: 'emp-syn-007@testflow-demo.local', role: 'TEST_TECHNICIAN', pass: 'DemoPass123!' },
  { label: 'Super Admin', email: 'admin@testflow.local', role: 'SUPER_ADMIN', pass: 'Admin123!' },
  { label: 'HR Officer', email: 'emp-syn-003@testflow-demo.local', role: 'HR_OFFICER', pass: 'DemoPass123!' },
];

export async function loginAs(email, password = 'DemoPass123!') {
  try {
    const persona = PERSONAS.find(p => p.email === email);
    const pass = persona ? persona.pass : password;
    showToast(`Activating persona...`, 'info');
    await api.login(email, pass);
    showToast('Persona activated successfully!', 'success');
    renderUserBar();
    loadCurrentTab();
  } catch (err) {
    showToast(err.message, 'error');
  }
}
window.loginAs = loginAs;

function renderUserBar() {
  const userContainer = document.getElementById('user-profile-widget');
  const personaSelector = document.getElementById('persona-buttons');

  if (personaSelector) {
    personaSelector.innerHTML = PERSONAS.map(p => {
      const isActive = authState.user?.email === p.email;
      return `
        <button onclick="loginAs('${p.email}')" 
          class="text-xs px-3.5 py-1.5 rounded-lg font-medium transition-all duration-200 border ${
            isActive 
              ? 'bg-[#E7473C] text-white border-[#E7473C] shadow-sm font-semibold' 
              : 'bg-white text-zinc-600 border-zinc-300 hover:border-[#E7473C] hover:text-[#E7473C] hover:bg-red-50/50'
          }">
          <span>${p.label}</span>
        </button>
      `;
    }).join('');
  }

  if (userContainer) {
    if (authState.isAuthenticated() && authState.user) {
      userContainer.innerHTML = `
        <div class="flex items-center gap-3 bg-white border border-zinc-200 px-3.5 py-1.5 rounded-xl shadow-sm">
          <div class="w-7 h-7 rounded-lg bg-gradient-to-tr from-[#E7473C] to-[#d6382d] flex items-center justify-center font-bold text-xs text-white shadow-sm">
            ${authState.user.first_name[0]}${authState.user.last_name[0]}
          </div>
          <div class="text-left">
            <div class="text-xs font-semibold text-zinc-900 leading-tight">${authState.user.first_name} ${authState.user.last_name}</div>
            <div class="text-[10px] text-[#E7473C] font-mono leading-tight uppercase font-semibold">${authState.user.role}</div>
          </div>
          <button id="logout-btn" class="ml-2 text-xs px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-[#E7473C] text-zinc-600 hover:text-white border border-zinc-200 hover:border-[#E7473C] transition font-medium">
            Sign out
          </button>
        </div>
      `;
      document.getElementById('logout-btn')?.addEventListener('click', () => {
        api.logout();
        showToast('Signed out', 'info');
        window.location.href = '/login';
      });
    } else {
      userContainer.innerHTML = `
        <a href="/login" class="btn-red text-xs px-3.5 py-1.5 rounded-lg font-semibold shadow-sm flex items-center gap-1.5">
          <i data-lucide="log-in" class="w-3.5 h-3.5"></i>
          <span>Sign In</span>
        </a>
      `;
    }
  }
  if (window.lucide) window.lucide.createIcons();
}

// Tab navigation
export function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.nav-tab-item').forEach(el => {
    const isActive = el.getAttribute('data-tab') === tab;
    el.classList.toggle('nav-tab-active', isActive);
  });

  document.querySelectorAll('.tab-content').forEach(el => {
    const isTarget = el.id === `tab-${tab}`;
    el.classList.toggle('hidden', !isTarget);
    if (isTarget) {
      el.classList.remove('animate-fade-in');
      void el.offsetWidth; // trigger reflow for animation
      el.classList.add('animate-fade-in');
    }
  });

  loadCurrentTab();
  if (window.lucide) window.lucide.createIcons();
}
window.switchTab = switchTab;

export function loadCurrentTab() {
  switch (currentTab) {
    case 'dashboard':
      loadDashboard();
      break;
    case 'workbench':
      loadWorkbench();
      break;
    case 'quality':
      loadQuality();
      break;
    case 'batches':
      loadBatches();
      break;
    case 'dispatch':
      loadDispatch();
      break;
    case 'traceability':
      loadTraceability();
      break;
    case 'attendance':
      loadAttendance();
      break;
  }
}
window.loadCurrentTab = loadCurrentTab;

// -------------------------------------------------------------
// 1. DASHBOARD
// -------------------------------------------------------------
async function loadDashboard() {
  try {
    const overview = await api.getOverview();
    const quality = await api.getQualityDashboard();

    document.getElementById('kpi-yield').textContent = `${overview.overall_yield_percentage}%`;
    document.getElementById('kpi-tested').textContent = overview.tested_units;
    document.getElementById('kpi-passed').textContent = overview.passed_units;
    document.getElementById('kpi-failed').textContent = overview.failed_units;
    document.getElementById('kpi-defects').textContent = quality.total_defects;
    document.getElementById('kpi-attendance').textContent = `${overview.attendance_rate_today}%`;

    // Yield Doughnut Chart (Emerald, Bright Red #E7473C, Smoke Gray)
    const yieldCtx = document.getElementById('yield-chart')?.getContext('2d');
    if (yieldCtx) {
      if (yieldChart) yieldChart.destroy();
      yieldChart = new Chart(yieldCtx, {
        type: 'doughnut',
        data: {
          labels: ['Passed Units', 'Failed Units', 'Pending Testing'],
          datasets: [{
            data: [
              overview.passed_units,
              overview.failed_units,
              Math.max(0, overview.total_registered_units - overview.tested_units)
            ],
            backgroundColor: ['#10B981', '#E7473C', '#CBD5E1'],
            borderColor: '#FFFFFF',
            borderWidth: 3,
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { color: '#4B5563', boxWidth: 12, font: { family: 'Inter', size: 11, weight: '500' } } }
          },
          cutout: '72%'
        }
      });
    }

    // Defect Pareto Bar Chart (Bright Red #E7473C)
    const paretoCtx = document.getElementById('pareto-chart')?.getContext('2d');
    if (paretoCtx) {
      if (paretoChart) paretoChart.destroy();
      const codes = quality.top_defect_codes || [];
      paretoChart = new Chart(paretoCtx, {
        type: 'bar',
        data: {
          labels: codes.map(c => c.code),
          datasets: [{
            label: 'Incident Count',
            data: codes.map(c => c.count),
            backgroundColor: '#E7473C',
            hoverBackgroundColor: '#d6382d',
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#6B7280', font: { family: 'JetBrains Mono', size: 10 } }, grid: { display: false } },
            y: { ticks: { color: '#6B7280', stepSize: 1, font: { family: 'JetBrains Mono', size: 10 } }, grid: { color: '#F3F4F6' } }
          }
        }
      });
    }
  } catch (err) {
    showToast(`Dashboard error: ${err.message}`, 'error');
  }
}

// -------------------------------------------------------------
// 2. TESTING WORKBENCH
// -------------------------------------------------------------
async function loadWorkbench() {
  const container = document.getElementById('workbench-queue-list');
  if (!container) return;

  if (!authState.isAuthenticated()) {
    container.innerHTML = `
      <div class="p-10 text-center text-zinc-500 bg-white rounded-xl border border-zinc-200 shadow-sm">
        <i data-lucide="lock" class="w-8 h-8 mx-auto mb-3 text-[#E7473C]"></i>
        <h3 class="text-sm font-semibold text-zinc-900">Technician Authentication Required</h3>
        <p class="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">Please activate a technician persona to view and execute checklist testing.</p>
        <button onclick="loginAs('emp-syn-007@testflow-demo.local')" class="btn-red mt-4 px-4 py-2 rounded-lg text-xs font-semibold">
          1-Click Login as Technician (Tester 1)
        </button>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }

  container.innerHTML = `<div class="p-8 text-center text-zinc-400 font-mono text-xs">Loading queue...</div>`;
  try {
    const queue = await api.getMyQueue();
    if (!queue || queue.length === 0) {
      container.innerHTML = `
        <div class="p-10 text-center text-zinc-400 bg-white rounded-xl border border-zinc-200 shadow-sm">
          <i data-lucide="inbox" class="w-8 h-8 mx-auto mb-2 text-zinc-400"></i>
          <p class="text-sm text-zinc-700 font-medium">No active units allocated to your queue.</p>
          <p class="text-xs text-zinc-500 mt-1">Switch to Test Lead (EMP-SYN-005) to allocate new batches or units.</p>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    container.innerHTML = queue.map(group => `
      <div class="bg-white border border-zinc-200 rounded-xl p-5 mb-4 shadow-sm card-smoke">
        <div class="flex items-center justify-between border-b border-zinc-100 pb-3 mb-4">
          <div>
            <span class="text-xs uppercase font-mono px-2.5 py-0.5 rounded bg-red-50 text-[#E7473C] border border-red-200 font-bold mr-2">
              Batch ${group.batch_number}
            </span>
            <span class="text-sm font-bold text-zinc-900">${group.product_model || 'Product'}</span>
          </div>
          <span class="text-xs text-zinc-500 font-mono">Pending units: <strong class="text-zinc-900">${group.pending_units_count}</strong></span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          ${group.units.map(u => `
            <div class="bg-zinc-50/70 p-3.5 rounded-lg border border-zinc-200 flex items-center justify-between hover:border-zinc-300 transition">
              <div>
                <div class="font-mono text-xs font-bold text-zinc-900">${u.serial_number}</div>
                <div class="text-[10px] text-amber-600 font-semibold uppercase mt-0.5 font-mono">${u.status}</div>
              </div>
              <button onclick="openTestModal(${u.id}, '${u.serial_number}')" 
                class="btn-red px-3 py-1 text-xs rounded-md font-medium flex items-center gap-1.5 shadow-sm">
                <i data-lucide="play" class="w-3 h-3"></i> Test
              </button>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');

    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    if (err.message && err.message.includes('403')) {
      container.innerHTML = `
        <div class="p-10 text-center text-zinc-500 bg-white rounded-xl border border-zinc-200 shadow-sm card-smoke">
          <i data-lucide="shield-alert" class="w-8 h-8 mx-auto mb-3 text-amber-500"></i>
          <h3 class="text-sm font-semibold text-zinc-900">Role Restriction: Testing Workbench</h3>
          <p class="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">The Testing Workbench test queue is restricted to floor test technicians and supervisors.</p>
          <button onclick="loginAs('emp-syn-007@testflow-demo.local')" class="btn-red mt-4 px-4 py-2 rounded-lg text-xs font-semibold">
            Switch to Test Tech Persona
          </button>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }
    container.innerHTML = `<div class="p-6 text-center text-[#E7473C] text-xs font-mono">Error: ${err.message}</div>`;
  }
}

// Test Runner Modal
let activeTestingUnit = null;
let activeTemplate = null;

export async function openTestModal(unitId, serialNumber) {
  activeTestingUnit = { id: unitId, serial: serialNumber };
  document.getElementById('test-modal-serial').textContent = serialNumber;

  const container = document.getElementById('test-modal-params');
  container.innerHTML = '<div class="text-center p-4 text-xs text-zinc-400 font-mono">Fetching template criteria...</div>';
  openModal('test-execution-modal');

  try {
    const templates = await api.getTestTemplates();
    if (!templates || templates.length === 0) {
      container.innerHTML = '<div class="text-[#E7473C] text-xs">No active test template found.</div>';
      return;
    }

    const templateDetail = await api.getTemplate(templates[0].id);
    activeTemplate = templateDetail;

    container.innerHTML = `
      <div class="mb-3 text-xs text-[#E7473C] font-mono font-semibold">Template: ${templateDetail.name} (v${templateDetail.version})</div>
      <div class="space-y-3">
        ${templateDetail.parameters.map(p => `
          <div class="bg-zinc-50 p-3 rounded-lg border border-zinc-200 text-xs">
            <div class="flex justify-between mb-1.5 font-medium text-zinc-900">
              <span>${p.parameter_name} ${p.is_mandatory ? '<span class="text-[#E7473C] font-bold">*</span>' : ''}</span>
              <span class="text-zinc-500 font-mono text-[11px]">
                ${p.data_type === 'NUMERIC_RANGE' ? `[${p.min_limit} - ${p.max_limit} ${p.unit_of_measure || ''}]` : p.data_type}
              </span>
            </div>
            ${p.data_type === 'BOOLEAN' ? `
              <select id="param-${p.id}" class="w-full bg-white border border-zinc-300 rounded-md px-2.5 py-1.5 text-zinc-900 text-xs focus:border-[#E7473C] focus:outline-none">
                <option value="true">True / Pass</option>
                <option value="false">False / Fail</option>
              </select>
            ` : `
              <input type="text" id="param-${p.id}" placeholder="Measured value..." 
                class="w-full bg-white border border-zinc-300 rounded-md px-2.5 py-1.5 text-zinc-900 font-mono text-xs focus:border-[#E7473C] focus:outline-none transition" />
            `}
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="text-[#E7473C] text-xs">Failed to load template: ${err.message}</div>`;
  }
}
window.openTestModal = openTestModal;

export async function submitActiveTest() {
  if (!activeTestingUnit || !activeTemplate) return;

  const results = [];
  for (const p of activeTemplate.parameters) {
    const input = document.getElementById(`param-${p.id}`);
    if (input) {
      results.push({
        parameter_id: p.id,
        measured_value: input.value.trim()
      });
    }
  }

  try {
    const res = await api.submitManualTest({
      batch_item_id: activeTestingUnit.id,
      template_id: activeTemplate.id,
      results,
      remarks: 'Submitted via Web Console'
    });

    closeModal('test-execution-modal');
    if (res.overall_result === 'PASS') {
      showToast(`Unit ${activeTestingUnit.serial} PASSED inspection!`, 'success');
    } else {
      showToast(`Unit ${activeTestingUnit.serial} FAILED tolerances.`, 'warning');
    }
    loadWorkbench();
  } catch (err) {
    showToast(`Test submission rejected: ${err.message}`, 'error');
  }
}
window.submitActiveTest = submitActiveTest;

// -------------------------------------------------------------
// 3. QUALITY ASSURANCE
// -------------------------------------------------------------
async function loadQuality() {
  const container = document.getElementById('quality-defects-table');
  if (!container) return;

  container.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-zinc-400 font-mono text-xs">Loading defect logs...</td></tr>`;
  try {
    const defects = await api.getDefects();
    if (!defects || defects.length === 0) {
      container.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-zinc-500">No defect records logged. Clean quality run!</td></tr>`;
      return;
    }

    container.innerHTML = defects.map(d => `
      <tr class="border-b border-zinc-100 hover:bg-zinc-50 text-xs font-mono transition">
        <td class="p-3.5 text-[#E7473C] font-bold">${d.serial_number || 'N/A'}</td>
        <td class="p-3.5 text-zinc-900 font-semibold">${d.defect_code}</td>
        <td class="p-3.5">
          <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
            d.severity === 'CRITICAL' ? 'bg-red-50 text-[#E7473C] border border-red-200' :
            d.severity === 'MAJOR' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
            'bg-zinc-100 text-zinc-700 border border-zinc-200'
          }">${d.severity}</span>
        </td>
        <td class="p-3.5 font-sans text-zinc-700">${d.description}</td>
        <td class="p-3.5">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${d.is_resolved ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}">
            ${d.is_resolved ? 'RESOLVED' : 'OPEN'}
          </span>
        </td>
        <td class="p-3.5 text-right font-sans">
          <button onclick="openDispositionModal(${d.batch_item_id}, '${d.serial_number}')" 
            class="px-3 py-1 bg-white hover:bg-[#E7473C] text-zinc-700 hover:text-white border border-zinc-300 hover:border-[#E7473C] rounded-md text-xs font-medium transition shadow-sm">
            Review QA
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    container.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-[#E7473C]">Error: ${err.message}</td></tr>`;
  }
}

let activeDispositionItem = null;
export function openDispositionModal(itemId, serial) {
  activeDispositionItem = { id: itemId, serial };
  document.getElementById('disp-modal-serial').textContent = serial;
  openModal('qa-disposition-modal');
}
window.openDispositionModal = openDispositionModal;

export async function submitDisposition(decision) {
  if (!activeDispositionItem) return;

  const remarks = document.getElementById('disp-remarks')?.value || '';
  try {
    await api.submitDisposition(activeDispositionItem.id, decision, remarks);
    closeModal('qa-disposition-modal');
    showToast(`Disposition [${decision}] recorded for ${activeDispositionItem.serial}`, 'success');
    loadQuality();
  } catch (err) {
    showToast(`Disposition rejected: ${err.message}`, 'error');
  }
}
window.submitDisposition = submitDisposition;

// -------------------------------------------------------------
// 4. BATCHES & INVENTORY
// -------------------------------------------------------------
async function loadBatches() {
  const container = document.getElementById('batches-list-table');
  if (!container) return;

  container.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-zinc-400 font-mono text-xs">Loading batches...</td></tr>`;
  try {
    const batches = await api.getBatches();
    if (!batches || batches.length === 0) {
      container.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-zinc-500">No batches registered.</td></tr>`;
      return;
    }

    container.innerHTML = batches.map(b => `
      <tr class="border-b border-zinc-100 hover:bg-zinc-50 text-xs transition">
        <td class="p-3.5 font-mono font-bold text-zinc-900">${b.batch_number}</td>
        <td class="p-3.5 font-medium text-zinc-700">${b.client_name || 'N/A'}</td>
        <td class="p-3.5 font-mono text-zinc-500">${b.product_model_number || 'N/A'}</td>
        <td class="p-3.5 font-mono text-center text-zinc-900 font-semibold">${b.received_qty}</td>
        <td class="p-3.5 font-mono text-center text-emerald-600 font-bold">${b.passed_count || 0}</td>
        <td class="p-3.5 text-center">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
            b.current_status === 'TESTED' ? 'badge-passed' :
            b.current_status === 'DISPATCHED' ? 'badge-dispatched' :
            b.current_status === 'IN_TESTING' ? 'badge-allocated' : 'bg-zinc-100 text-zinc-700 border border-zinc-200'
          }">${b.current_status}</span>
        </td>
        <td class="p-3.5 text-right">
          <button onclick="viewBatchProgress(${b.id})" class="px-3 py-1 bg-white hover:bg-[#E7473C] text-zinc-700 hover:text-white rounded-md border border-zinc-300 hover:border-[#E7473C] transition text-xs font-medium shadow-sm">
            Yield Analytics
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    container.innerHTML = `
      <tr>
        <td colspan="7" class="p-8 text-center">
          <div class="inline-flex flex-col items-center gap-2">
            <span class="text-[#E7473C] text-xs font-mono font-semibold">Error: ${err.message}</span>
            <button onclick="loadBatches()" class="mt-2 px-3 py-1.5 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium rounded-lg border border-zinc-300 shadow-sm transition">
              ↻ Retry Loading Batches
            </button>
          </div>
        </td>
      </tr>
    `;
  }
}

export async function viewBatchProgress(batchId) {
  openModal('batch-progress-modal');
  const content = document.getElementById('batch-progress-content');
  content.innerHTML = '<div class="p-4 text-center text-xs text-zinc-400 font-mono">Calculating batch analytics...</div>';

  try {
    const prog = await api.getBatchProgress(batchId);
    content.innerHTML = `
      <div class="space-y-4">
        <div class="flex justify-between items-center border-b border-zinc-200 pb-3">
          <div>
            <div class="text-base font-bold text-zinc-900">${prog.batch_number}</div>
            <div class="text-xs text-[#E7473C] font-semibold">${prog.product_model_name}</div>
          </div>
          <div class="text-right">
            <div class="text-2xl font-mono font-bold text-emerald-600">${prog.first_pass_yield}%</div>
            <div class="text-[10px] text-zinc-500 uppercase tracking-wider font-mono">First-Pass Yield</div>
          </div>
        </div>

        <div>
          <div class="flex justify-between text-xs mb-1 font-medium">
            <span class="text-zinc-600">Testing Completion</span>
            <span class="font-mono text-zinc-900">${prog.completion_percentage}% (${prog.units_passed + prog.units_failed}/${prog.total_units})</span>
          </div>
          <div class="w-full bg-zinc-100 h-2.5 rounded-full overflow-hidden border border-zinc-200">
            <div class="bg-gradient-to-r from-[#E7473C] to-emerald-500 h-full transition-all duration-500" style="width: ${prog.completion_percentage}%"></div>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-2.5 text-center text-xs pt-2">
          <div class="bg-zinc-50 p-2.5 rounded-lg border border-zinc-200">
            <div class="text-[10px] text-zinc-500 uppercase font-semibold">Passed</div>
            <div class="font-mono font-bold text-emerald-600 text-base mt-0.5">${prog.units_passed}</div>
          </div>
          <div class="bg-zinc-50 p-2.5 rounded-lg border border-zinc-200">
            <div class="text-[10px] text-zinc-500 uppercase font-semibold">QA Approved</div>
            <div class="font-mono font-bold text-[#E7473C] text-base mt-0.5">${prog.units_qa_approved}</div>
          </div>
          <div class="bg-zinc-50 p-2.5 rounded-lg border border-zinc-200">
            <div class="text-[10px] text-zinc-500 uppercase font-semibold">Rework / Scrapped</div>
            <div class="font-mono font-bold text-amber-600 text-base mt-0.5">${prog.units_failed + prog.units_qa_rework}</div>
          </div>
        </div>

        <div class="text-[11px] text-zinc-600 pt-1">
          <strong class="text-zinc-900">Active Technicians:</strong> ${prog.active_technicians?.join(', ') || 'None assigned yet'}
        </div>
      </div>
    `;
  } catch (err) {
    content.innerHTML = `<div class="text-[#E7473C] text-xs">Error: ${err.message}</div>`;
  }
}
window.viewBatchProgress = viewBatchProgress;

// -------------------------------------------------------------
// 5. OUTBOUND DISPATCH
// -------------------------------------------------------------
async function loadDispatch() {
  const container = document.getElementById('dispatch-orders-table');
  if (!container) return;

  container.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-zinc-400 font-mono text-xs">Loading dispatches...</td></tr>`;
  try {
    const dispatches = await api.getDispatches();
    if (!dispatches || dispatches.length === 0) {
      container.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-zinc-500">No dispatch orders created yet.</td></tr>`;
      return;
    }

    container.innerHTML = dispatches.map(d => `
      <tr class="border-b border-zinc-100 hover:bg-zinc-50 text-xs transition">
        <td class="p-3.5 font-mono font-bold text-zinc-900">${d.dispatch_code}</td>
        <td class="p-3.5 font-mono text-zinc-600">${d.batch_number || 'N/A'}</td>
        <td class="p-3.5 text-zinc-800 font-semibold">${d.client_name || 'N/A'}</td>
        <td class="p-3.5 font-mono text-center text-zinc-900 font-semibold">${d.total_units} units</td>
        <td class="p-3.5 text-center">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
            d.status === 'DISPATCHED' ? 'badge-dispatched' :
            d.status === 'READY' ? 'badge-passed' :
            d.status === 'HELD' ? 'badge-allocated' : 'badge-failed'
          }">${d.status}</span>
        </td>
        <td class="p-3.5 text-zinc-600">${d.carrier_name || 'Carrier Pending'}</td>
        <td class="p-3.5 text-zinc-500 font-mono">${d.dispatch_date}</td>
      </tr>
    `).join('');
  } catch (err) {
    container.innerHTML = `
      <tr>
        <td colspan="7" class="p-8 text-center">
          <div class="inline-flex flex-col items-center gap-2">
            <span class="text-[#E7473C] text-xs font-mono font-semibold">Error: ${err.message}</span>
            <button onclick="loadDispatch()" class="mt-2 px-3 py-1.5 bg-white hover:bg-zinc-50 text-zinc-700 text-xs font-medium rounded-lg border border-zinc-300 shadow-sm transition">
              ↻ Retry Loading Dispatches
            </button>
          </div>
        </td>
      </tr>
    `;
  }
}

// -------------------------------------------------------------
// 6. UNIVERSAL TRACEABILITY QUERY
// -------------------------------------------------------------
async function loadTraceability() {
  const input = document.getElementById('traceability-input');
  if (input && !input.value) {
    input.value = 'SYN-TF-0017';
    performTraceabilityQuery('SYN-TF-0017');
  }
}

export async function performTraceabilityQuery(serial = null) {
  const query = serial || document.getElementById('traceability-input')?.value.trim();
  if (!query) {
    showToast('Please enter a serial number to trace', 'warning');
    return;
  }

  const resultContainer = document.getElementById('traceability-results');
  resultContainer.innerHTML = '<div class="p-8 text-center text-zinc-500 font-mono text-xs">Searching digital birth certificate for ' + query + '...</div>';

  try {
    const trace = await api.getTraceability(query);
    resultContainer.innerHTML = `
      <div class="bg-white border border-zinc-200 rounded-xl p-6 shadow-sm card-smoke">
        <!-- Certificate Header -->
        <div class="flex flex-col md:flex-row md:items-center justify-between border-b border-zinc-200 pb-4 mb-6">
          <div>
            <div class="text-[10px] font-mono text-[#E7473C] uppercase tracking-widest font-bold">Universal Serial Traceability</div>
            <div class="text-2xl font-mono font-extrabold text-zinc-900 tracking-wide mt-0.5">${trace.serial_number}</div>
            <div class="text-xs text-zinc-500 mt-1">QR Hash: <span class="font-mono text-zinc-700">${trace.qr_code_hash || 'N/A'}</span></div>
          </div>
          <div class="mt-4 md:mt-0 flex items-center gap-3">
            <span class="px-3 py-1 rounded-md text-xs font-bold uppercase ${
              trace.current_status === 'QA_APPROVED' ? 'badge-qa-approved' :
              trace.current_status === 'DISPATCHED' ? 'badge-dispatched' :
              trace.current_status === 'PASSED' ? 'badge-passed' : 'badge-allocated'
            }">${trace.current_status}</span>
          </div>
        </div>

        <!-- Vertical Timeline -->
        <div class="relative border-l-2 border-[#E7473C]/40 ml-4 pl-6 space-y-8">
          <!-- 1. Inward Lot -->
          <div class="relative">
            <div class="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-[#E7473C] border-4 border-white shadow-sm"></div>
            <div class="text-xs uppercase font-bold text-[#E7473C] tracking-wider font-mono">1. Inward Lot Receiving</div>
            <div class="bg-zinc-50 p-4 rounded-lg border border-zinc-200 mt-2 text-xs">
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div><span class="text-zinc-500">Batch Number:</span> <span class="font-mono text-zinc-900 font-bold">${trace.inward_batch.batch_number}</span></div>
                <div><span class="text-zinc-500">OEM Client:</span> <span class="text-zinc-900 font-medium">${trace.product.client_name}</span></div>
                <div><span class="text-zinc-500">Hardware Model:</span> <span class="text-zinc-900 font-medium">${trace.product.model_number}</span></div>
                <div><span class="text-zinc-500">Inward Date:</span> <span class="font-mono text-zinc-900">${trace.inward_batch.inward_date}</span></div>
              </div>
            </div>
          </div>

          <!-- 2. Test Execution -->
          <div class="relative">
            <div class="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-emerald-500 border-4 border-white shadow-sm"></div>
            <div class="text-xs uppercase font-bold text-emerald-600 tracking-wider font-mono">2. Testing & Measurement Verification</div>
            <div class="bg-zinc-50 p-4 rounded-lg border border-zinc-200 mt-2 text-xs space-y-3">
              ${(trace.test_history || []).map(sess => `
                <div class="border-b border-zinc-200 pb-2 last:border-b-0 last:pb-0">
                  <div class="flex justify-between text-zinc-700 mb-2 font-medium">
                    <span>Template: <strong class="text-zinc-900">${sess.template_name || 'Standard'}</strong></span>
                    <span class="font-bold ${sess.overall_result === 'PASS' ? 'text-emerald-600' : 'text-[#E7473C]'}">${sess.overall_result}</span>
                  </div>
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] font-mono">
                    ${(sess.measurements || []).map(m => `
                      <div class="bg-white p-2 rounded border border-zinc-200 shadow-sm">
                        <div class="text-zinc-500 text-[10px] truncate">${m.parameter_name}</div>
                        <div class="text-zinc-900 font-bold mt-0.5">${m.measured_value} (${m.result})</div>
                      </div>
                    `).join('')}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- 3. QA Disposition -->
          <div class="relative">
            <div class="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-amber-500 border-4 border-white shadow-sm"></div>
            <div class="text-xs uppercase font-bold text-amber-700 tracking-wider font-mono">3. Quality Inspector Disposition</div>
            <div class="bg-zinc-50 p-4 rounded-lg border border-zinc-200 mt-2 text-xs">
              ${trace.quality_review ? `
                <div class="flex justify-between items-center">
                  <div>
                    <span class="text-zinc-500">Inspector:</span> <strong class="text-zinc-900">${trace.quality_review.inspector_name || 'QA Team'}</strong>
                    <p class="text-zinc-700 mt-1 italic font-serif">"${trace.quality_review.remarks || 'Standard verification sign-off'}"</p>
                  </div>
                  <span class="px-2.5 py-1 rounded text-xs font-bold badge-qa-approved">${trace.quality_review.decision}</span>
                </div>
              ` : `
                <div class="text-zinc-500 italic">No formal QA disposition recorded yet.</div>
              `}
            </div>
          </div>

          <!-- 4. Outbound Dispatch -->
          <div class="relative">
            <div class="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-sky-500 border-4 border-white shadow-sm"></div>
            <div class="text-xs uppercase font-bold text-sky-700 tracking-wider font-mono">4. Outbound Logistics & Dispatch</div>
            <div class="bg-zinc-50 p-4 rounded-lg border border-zinc-200 mt-2 text-xs">
              ${trace.dispatch ? `
                <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
                  <div><span class="text-zinc-500">Challan:</span> <span class="font-mono text-zinc-900 font-bold">${trace.dispatch.dispatch_code}</span></div>
                  <div><span class="text-zinc-500">Carrier:</span> <span class="text-zinc-900 font-medium">${trace.dispatch.carrier_name || 'Direct'}</span></div>
                  <div><span class="text-zinc-500">Date:</span> <span class="font-mono text-zinc-900">${trace.dispatch.dispatch_date}</span></div>
                  <div><span class="text-zinc-500">Status:</span> <span class="font-bold text-sky-700">${trace.dispatch.status}</span></div>
                </div>
              ` : `
                <div class="text-zinc-500 italic">Unit currently in warehouse; not yet assigned to an outbound dispatch challan.</div>
              `}
            </div>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    resultContainer.innerHTML = `
      <div class="p-6 bg-red-50 border border-red-200 rounded-xl text-center text-[#E7473C] text-sm font-medium">
        <i data-lucide="alert-circle" class="w-6 h-6 mx-auto mb-2 text-[#E7473C]"></i>
        ${err.message}
      </div>
    `;
  }
}
window.performTraceabilityQuery = performTraceabilityQuery;

// -------------------------------------------------------------
// 7. ATTENDANCE & SHIFTS
// -------------------------------------------------------------
async function loadAttendance() {
  const container = document.getElementById('attendance-records-list');
  if (!container) return;

  container.innerHTML = '<div class="p-4 text-center text-zinc-400 font-mono text-xs">Loading attendance roll call...</div>';
  try {
    const today = await api.getTodayAttendance();
    document.getElementById('att-present-count').textContent = today.present_count || today.present || 0;
    document.getElementById('att-absent-count').textContent = today.absent_count || today.absent || 0;
    document.getElementById('att-rate').textContent = `${today.attendance_rate || today.present_percentage || 0}%`;

    const records = today.records || [];
    if (records.length === 0) {
      container.innerHTML = '<div class="p-6 text-center text-zinc-500 text-xs">No attendance punches recorded today yet. Use the buttons above to punch in.</div>';
      return;
    }

    container.innerHTML = records.map(r => `
      <div class="bg-zinc-50 p-3.5 rounded-lg border border-zinc-200 flex justify-between items-center text-xs hover:border-zinc-300 transition">
        <div>
          <div class="font-bold text-zinc-900">${r.employee_name || `${r.first_name || 'Staff'} ${r.last_name || ''}`}</div>
          <div class="text-zinc-500 font-mono text-[10px] mt-0.5">${r.emp_code} • Operations Shift</div>
        </div>
        <div class="text-right">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
            r.status === 'PRESENT' ? 'badge-passed' :
            r.status === 'ON_LEAVE' ? 'badge-allocated' : 'badge-failed'
          }">${r.status}</span>
          <div class="text-[10px] font-mono text-zinc-500 mt-1">${r.punch_in || '--:--'} - ${r.punch_out || '--:--'}</div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-[#E7473C] text-xs font-mono">Error loading roll call: ${err.message}</div>`;
  }
}

export async function handlePunch(type) {
  try {
    if (type === 'in') {
      await api.punchIn();
      showToast('Punch in recorded!', 'success');
    } else {
      await api.punchOut();
      showToast('Punch out recorded!', 'success');
    }
    loadAttendance();
  } catch (err) {
    showToast(err.message, 'error');
  }
}
window.handlePunch = handlePunch;

// Initialize on load with instant auto-login fallback
document.addEventListener('DOMContentLoaded', async () => {
  if (!authState.isAuthenticated()) {
    try {
      await api.login('emp-syn-001@testflow-demo.local', 'DemoPass123!');
    } catch (e) {
      console.warn('Auto-login notice:', e);
    }
  }
  renderUserBar();
  loadCurrentTab();
  if (window.lucide) window.lucide.createIcons();
});
