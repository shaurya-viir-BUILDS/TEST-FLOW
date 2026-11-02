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
  const bgColors = {
    success: 'bg-emerald-900/90 border-emerald-500 text-emerald-200',
    error: 'bg-rose-900/90 border-rose-500 text-rose-200',
    info: 'bg-slate-800/95 border-indigo-500 text-slate-200',
    warning: 'bg-amber-900/90 border-amber-500 text-amber-200'
  };

  toast.className = `flex items-center gap-3 px-4 py-3 rounded-lg border shadow-xl text-sm transition-all transform duration-300 translate-y-2 opacity-0 ${bgColors[type] || bgColors.info}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button class="ml-auto text-xs opacity-70 hover:opacity-100" onclick="this.parentElement.remove()">✕</button>
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

// Quick login personas
const PERSONAS = [
  { label: 'Operations Mgr', email: 'emp-syn-001@testflow-demo.local', role: 'OPERATIONS_MGR', icon: 'shield' },
  { label: 'QA Inspector', email: 'emp-syn-013@testflow-demo.local', role: 'QA_INSPECTOR', icon: 'check-circle' },
  { label: 'Store Keeper', email: 'emp-syn-014@testflow-demo.local', role: 'STORE_KEEPER', icon: 'package' },
  { label: 'Test Lead', email: 'emp-syn-005@testflow-demo.local', role: 'TEST_SUPERVISOR', icon: 'activity' },
  { label: 'Test Tech', email: 'emp-syn-007@testflow-demo.local', role: 'TEST_TECHNICIAN', icon: 'tool' },
];

export async function loginAs(email) {
  try {
    showToast(`Authenticating as ${email.split('@')[0]}...`, 'info');
    await api.login(email, 'DemoPass123!');
    showToast('Login successful!', 'success');
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
    personaSelector.innerHTML = PERSONAS.map(p => `
      <button onclick="loginAs('${p.email}')" 
        class="text-xs px-2.5 py-1.5 rounded-md font-medium border border-slate-700 hover:border-indigo-500 hover:bg-slate-800 transition flex items-center gap-1.5 ${authState.user?.email === p.email ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500' : 'text-slate-400'}">
        <span>${p.label}</span>
      </button>
    `).join('');
  }

  if (userContainer) {
    if (authState.isAuthenticated() && authState.user) {
      userContainer.innerHTML = `
        <div class="flex items-center gap-3">
          <div class="text-right">
            <div class="text-xs font-semibold text-white">${authState.user.first_name} ${authState.user.last_name}</div>
            <div class="text-[10px] text-indigo-400 font-mono tracking-wide">${authState.user.role}</div>
          </div>
          <button id="logout-btn" class="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700">
            Sign out
          </button>
        </div>
      `;
      document.getElementById('logout-btn')?.addEventListener('click', () => {
        api.logout();
        showToast('Signed out', 'info');
        renderUserBar();
        loadCurrentTab();
      });
    } else {
      userContainer.innerHTML = `
        <button onclick="openModal('login-modal')" class="text-xs px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded font-medium shadow">
          Sign In
        </button>
      `;
    }
  }
  if (window.lucide) window.lucide.createIcons();
}

// Tab navigation
export function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.nav-tab').forEach(el => {
    const isActive = el.getAttribute('data-tab') === tab;
    el.classList.toggle('bg-slate-800', isActive);
    el.classList.toggle('text-white', isActive);
    el.classList.toggle('text-slate-400', !isActive);
  });

  document.querySelectorAll('.tab-content').forEach(el => {
    el.classList.toggle('hidden', el.id !== `tab-${tab}`);
  });

  loadCurrentTab();
}
window.switchTab = switchTab;

function loadCurrentTab() {
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

// -------------------------------------------------------------
// 1. DASHBOARD
// -------------------------------------------------------------
async function loadDashboard() {
  const container = document.getElementById('tab-dashboard');
  if (!container) return;

  try {
    const overview = await api.getOverview();
    const quality = await api.getQualityDashboard();

    document.getElementById('kpi-yield').textContent = `${overview.overall_yield_percentage}%`;
    document.getElementById('kpi-tested').textContent = overview.tested_units;
    document.getElementById('kpi-passed').textContent = overview.passed_units;
    document.getElementById('kpi-failed').textContent = overview.failed_units;
    document.getElementById('kpi-defects').textContent = quality.total_defects;
    document.getElementById('kpi-attendance').textContent = `${overview.attendance_rate_today}%`;

    // Yield Doughnut Chart
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
            backgroundColor: ['#10b981', '#f43f5e', '#64748b'],
            borderWidth: 0,
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 12 } }
          },
          cutout: '72%'
        }
      });
    }

    // Defect Pareto Bar Chart
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
            backgroundColor: '#6366f1',
            borderRadius: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
            y: { ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } }
          }
        }
      });
    }
  } catch (err) {
    showToast(`Error loading dashboard: ${err.message}`, 'error');
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
      <div class="p-8 text-center text-slate-400 bg-slate-900/50 rounded-xl border border-slate-800">
        <i data-lucide="lock" class="w-8 h-8 mx-auto mb-2 text-indigo-400"></i>
        <p>Please log in with a Technician or Supervisor account to view assigned testing tasks.</p>
        <button onclick="loginAs('emp-syn-007@testflow-demo.local')" class="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold">
          1-Click Login as Technician (Tester 1)
        </button>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();
    return;
  }

  container.innerHTML = `<div class="p-8 text-center text-slate-400">Loading technician queue...</div>`;
  try {
    const queue = await api.getMyQueue();
    if (!queue || queue.length === 0) {
      container.innerHTML = `
        <div class="p-8 text-center text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800">
          <p>No active units currently assigned to your queue.</p>
          <p class="text-xs text-slate-500 mt-1">Switch to Test Lead (EMP-SYN-005) to allocate new batches or units.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = queue.map(group => `
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 mb-4">
        <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
          <div>
            <span class="text-xs uppercase font-mono px-2 py-0.5 rounded bg-indigo-900/40 text-indigo-300 border border-indigo-700/50 mr-2">
              Batch ${group.batch_number}
            </span>
            <span class="text-sm font-semibold text-white">${group.product_model || 'Product'}</span>
          </div>
          <span class="text-xs text-slate-400">Pending units: <strong class="text-white">${group.pending_units_count}</strong></span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          ${group.units.map(u => `
            <div class="bg-slate-800/60 p-3 rounded-lg border border-slate-700/50 flex items-center justify-between">
              <div>
                <div class="font-mono text-xs font-medium text-white">${u.serial_number}</div>
                <div class="text-[10px] text-amber-400 uppercase mt-0.5">${u.status}</div>
              </div>
              <button onclick="openTestModal(${u.id}, '${u.serial_number}')" 
                class="px-2.5 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded font-medium shadow flex items-center gap-1">
                <i data-lucide="play" class="w-3 h-3"></i> Test
              </button>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');

    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-rose-400 text-xs">Error: ${err.message}</div>`;
  }
}

// Test Runner Modal
let activeTestingUnit = null;
let activeTemplate = null;

export async function openTestModal(unitId, serialNumber) {
  activeTestingUnit = { id: unitId, serial: serialNumber };
  document.getElementById('test-modal-serial').textContent = serialNumber;

  const container = document.getElementById('test-modal-params');
  container.innerHTML = '<div class="text-center p-4 text-xs text-slate-400">Fetching test template parameters...</div>';
  openModal('test-execution-modal');

  try {
    const templates = await api.getTestTemplates();
    if (!templates || templates.length === 0) {
      container.innerHTML = '<div class="text-rose-400 text-xs">No active test template found.</div>';
      return;
    }

    const templateDetail = await api.getTemplate(templates[0].id);
    activeTemplate = templateDetail;

    container.innerHTML = `
      <div class="mb-3 text-xs text-indigo-300 font-mono">Template: ${templateDetail.name} (v${templateDetail.version})</div>
      <div class="space-y-3">
        ${templateDetail.parameters.map(p => `
          <div class="bg-slate-800/80 p-3 rounded border border-slate-700 text-xs">
            <div class="flex justify-between mb-1 font-medium text-white">
              <span>${p.parameter_name} ${p.is_mandatory ? '<span class="text-rose-400 font-bold">*</span>' : ''}</span>
              <span class="text-slate-400 font-mono text-[11px]">
                ${p.data_type === 'NUMERIC_RANGE' ? `[${p.min_limit} - ${p.max_limit} ${p.unit_of_measure || ''}]` : p.data_type}
              </span>
            </div>
            ${p.data_type === 'BOOLEAN' ? `
              <select id="param-${p.id}" class="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white text-xs">
                <option value="true">True / Pass</option>
                <option value="false">False / Fail</option>
              </select>
            ` : `
              <input type="text" id="param-${p.id}" placeholder="Measured value..." 
                class="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white font-mono text-xs focus:border-indigo-500 focus:outline-none" />
            `}
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="text-rose-400 text-xs">Failed to load template: ${err.message}</div>`;
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

  container.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-400">Loading defect logs...</td></tr>`;
  try {
    const defects = await api.getDefects();
    if (!defects || defects.length === 0) {
      container.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400">No defect records logged. Clean quality run!</td></tr>`;
      return;
    }

    container.innerHTML = defects.map(d => `
      <tr class="border-b border-slate-800/80 hover:bg-slate-800/30 text-xs font-mono">
        <td class="p-3 text-indigo-400 font-semibold">${d.serial_number || 'N/A'}</td>
        <td class="p-3 text-white font-medium">${d.defect_code}</td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
            d.severity === 'CRITICAL' ? 'bg-rose-900/50 text-rose-300 border border-rose-700' :
            d.severity === 'MAJOR' ? 'bg-amber-900/50 text-amber-300 border border-amber-700' :
            'bg-slate-800 text-slate-300 border border-slate-700'
          }">${d.severity}</span>
        </td>
        <td class="p-3 font-sans text-slate-300">${d.description}</td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded text-[10px] ${d.is_resolved ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-800' : 'bg-amber-900/30 text-amber-400 border border-amber-800'}">
            ${d.is_resolved ? 'RESOLVED' : 'OPEN'}
          </span>
        </td>
        <td class="p-3 text-right font-sans">
          <button onclick="openDispositionModal(${d.batch_item_id}, '${d.serial_number}')" 
            class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs">
            Review QA
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    container.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-rose-400">Error: ${err.message}</td></tr>`;
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

  container.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-slate-400">Loading inward batches...</td></tr>`;
  try {
    const batches = await api.getBatches();
    if (!batches || batches.length === 0) {
      container.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400">No batches registered.</td></tr>`;
      return;
    }

    container.innerHTML = batches.map(b => `
      <tr class="border-b border-slate-800 hover:bg-slate-800/30 text-xs">
        <td class="p-3 font-mono font-semibold text-white">${b.batch_number}</td>
        <td class="p-3 font-medium text-slate-300">${b.client_name || 'N/A'}</td>
        <td class="p-3 text-slate-400">${b.product_model_number || 'N/A'}</td>
        <td class="p-3 font-mono text-center">${b.received_qty}</td>
        <td class="p-3 font-mono text-center text-emerald-400 font-semibold">${b.passed_count || 0}</td>
        <td class="p-3 text-center">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
            b.current_status === 'TESTED' ? 'badge-passed' :
            b.current_status === 'DISPATCHED' ? 'badge-dispatched' :
            b.current_status === 'IN_TESTING' ? 'badge-allocated' : 'bg-slate-800 text-slate-300'
          }">${b.current_status}</span>
        </td>
        <td class="p-3 text-right">
          <button onclick="viewBatchProgress(${b.id})" class="px-2.5 py-1 bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white rounded border border-slate-700 transition">
            Yield Progress
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    container.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-rose-400">Error: ${err.message}</td></tr>`;
  }
}

export async function viewBatchProgress(batchId) {
  openModal('batch-progress-modal');
  const content = document.getElementById('batch-progress-content');
  content.innerHTML = '<div class="p-4 text-center text-xs text-slate-400">Calculating batch analytics...</div>';

  try {
    const prog = await api.getBatchProgress(batchId);
    content.innerHTML = `
      <div class="space-y-4">
        <div class="flex justify-between items-center border-b border-slate-800 pb-3">
          <div>
            <div class="text-base font-bold text-white">${prog.batch_number}</div>
            <div class="text-xs text-indigo-400">${prog.product_model_name}</div>
          </div>
          <div class="text-right">
            <div class="text-xl font-mono font-bold text-emerald-400">${prog.first_pass_yield}%</div>
            <div class="text-[10px] text-slate-400 uppercase tracking-wider">First-Pass Yield</div>
          </div>
        </div>

        <div>
          <div class="flex justify-between text-xs mb-1">
            <span class="text-slate-400">Completion</span>
            <span class="font-mono text-white">${prog.completion_percentage}% (${prog.units_passed + prog.units_failed}/${prog.total_units})</span>
          </div>
          <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div class="bg-indigo-500 h-full transition-all duration-500" style="width: ${prog.completion_percentage}%"></div>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-2 text-center text-xs pt-2">
          <div class="bg-slate-800/60 p-2 rounded border border-slate-700/50">
            <div class="text-[10px] text-slate-400">Passed</div>
            <div class="font-mono font-bold text-emerald-400 text-sm mt-0.5">${prog.units_passed}</div>
          </div>
          <div class="bg-slate-800/60 p-2 rounded border border-slate-700/50">
            <div class="text-[10px] text-slate-400">QA Approved</div>
            <div class="font-mono font-bold text-indigo-400 text-sm mt-0.5">${prog.units_qa_approved}</div>
          </div>
          <div class="bg-slate-800/60 p-2 rounded border border-slate-700/50">
            <div class="text-[10px] text-slate-400">Failed / Rework</div>
            <div class="font-mono font-bold text-rose-400 text-sm mt-0.5">${prog.units_failed + prog.units_qa_rework}</div>
          </div>
        </div>

        <div class="text-[11px] text-slate-400">
          <strong>Active Technicians:</strong> ${prog.active_technicians?.join(', ') || 'None assigned yet'}
        </div>
      </div>
    `;
  } catch (err) {
    content.innerHTML = `<div class="text-rose-400 text-xs">Error: ${err.message}</div>`;
  }
}
window.viewBatchProgress = viewBatchProgress;

// -------------------------------------------------------------
// 5. OUTBOUND DISPATCH
// -------------------------------------------------------------
async function loadDispatch() {
  const container = document.getElementById('dispatch-orders-table');
  if (!container) return;

  container.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-slate-400">Loading dispatch records...</td></tr>`;
  try {
    const dispatches = await api.getDispatches();
    if (!dispatches || dispatches.length === 0) {
      container.innerHTML = `<tr><td colspan="7" class="p-6 text-center text-slate-400">No dispatch orders created yet.</td></tr>`;
      return;
    }

    container.innerHTML = dispatches.map(d => `
      <tr class="border-b border-slate-800 hover:bg-slate-800/30 text-xs">
        <td class="p-3 font-mono font-semibold text-white">${d.dispatch_code}</td>
        <td class="p-3 font-mono text-indigo-300">${d.batch_number || 'N/A'}</td>
        <td class="p-3 text-slate-300 font-medium">${d.client_name || 'N/A'}</td>
        <td class="p-3 font-mono text-center text-white">${d.total_units} units</td>
        <td class="p-3">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
            d.status === 'DISPATCHED' ? 'badge-dispatched' :
            d.status === 'READY' ? 'badge-passed' :
            d.status === 'HELD' ? 'badge-allocated' : 'badge-failed'
          }">${d.status}</span>
        </td>
        <td class="p-3 text-slate-400">${d.carrier_name || 'Carrier Pending'}</td>
        <td class="p-3 text-slate-400 font-mono">${d.dispatch_date}</td>
      </tr>
    `).join('');
  } catch (err) {
    container.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-rose-400">Error: ${err.message}</td></tr>`;
  }
}

// -------------------------------------------------------------
// 6. UNIVERSAL TRACEABILITY QUERY
// -------------------------------------------------------------
async function loadTraceability() {
  const input = document.getElementById('traceability-input');
  if (input && !input.value) {
    input.value = 'SYN-TF-0017'; // default demo serial
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
  resultContainer.innerHTML = '<div class="p-8 text-center text-slate-400">Searching digital birth certificate for ' + query + '...</div>';

  try {
    const trace = await api.getTraceability(query);
    resultContainer.innerHTML = `
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 glow-brand">
        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-800 pb-4 mb-6">
          <div>
            <div class="text-[10px] font-mono text-indigo-400 uppercase tracking-widest">Serial Number Traceability</div>
            <div class="text-2xl font-mono font-bold text-white tracking-wide mt-0.5">${trace.serial_number}</div>
            <div class="text-xs text-slate-400 mt-1">Hash: <span class="font-mono text-slate-300">${trace.qr_code_hash || 'N/A'}</span></div>
          </div>
          <div class="mt-4 md:mt-0 flex items-center gap-3">
            <span class="px-3 py-1 rounded text-xs font-bold uppercase ${
              trace.current_status === 'QA_APPROVED' ? 'badge-qa-approved' :
              trace.current_status === 'DISPATCHED' ? 'badge-dispatched' :
              trace.current_status === 'PASSED' ? 'badge-passed' : 'badge-allocated'
            }">${trace.current_status}</span>
          </div>
        </div>

        <!-- Vertical Timeline -->
        <div class="relative border-l-2 border-indigo-500/40 ml-4 pl-6 space-y-8">
          <!-- 1. Inward Lot -->
          <div class="relative">
            <div class="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-indigo-500 border-4 border-slate-900"></div>
            <div class="text-xs uppercase font-bold text-indigo-400 tracking-wider">1. Inward Lot Receiving</div>
            <div class="bg-slate-800/60 p-4 rounded-lg border border-slate-700/60 mt-2 text-xs">
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div><span class="text-slate-400">Batch Number:</span> <span class="font-mono text-white">${trace.inward_batch.batch_number}</span></div>
                <div><span class="text-slate-400">OEM Client:</span> <span class="text-white">${trace.product.client_name}</span></div>
                <div><span class="text-slate-400">Hardware Model:</span> <span class="text-white">${trace.product.model_number}</span></div>
                <div><span class="text-slate-400">Inward Date:</span> <span class="font-mono text-white">${trace.inward_batch.inward_date}</span></div>
              </div>
            </div>
          </div>

          <!-- 2. Test Execution -->
          <div class="relative">
            <div class="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-emerald-500 border-4 border-slate-900"></div>
            <div class="text-xs uppercase font-bold text-emerald-400 tracking-wider">2. Testing & Measurement Verification</div>
            <div class="bg-slate-800/60 p-4 rounded-lg border border-slate-700/60 mt-2 text-xs space-y-3">
              ${(trace.test_history || []).map(sess => `
                <div class="border-b border-slate-700/50 pb-2 last:border-b-0 last:pb-0">
                  <div class="flex justify-between text-slate-300 mb-2">
                    <span>Template: <strong>${sess.template_name || 'Standard'}</strong></span>
                    <span class="font-bold ${sess.overall_result === 'PASS' ? 'text-emerald-400' : 'text-rose-400'}">${sess.overall_result}</span>
                  </div>
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] font-mono">
                    ${(sess.measurements || []).map(m => `
                      <div class="bg-slate-900/60 p-2 rounded border border-slate-800">
                        <div class="text-slate-400 text-[10px] truncate">${m.parameter_name}</div>
                        <div class="text-white font-bold mt-0.5">${m.measured_value} (${m.result})</div>
                      </div>
                    `).join('')}
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- 3. QA Disposition -->
          <div class="relative">
            <div class="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-amber-500 border-4 border-slate-900"></div>
            <div class="text-xs uppercase font-bold text-amber-400 tracking-wider">3. Quality Inspector Disposition</div>
            <div class="bg-slate-800/60 p-4 rounded-lg border border-slate-700/60 mt-2 text-xs">
              ${trace.quality_review ? `
                <div class="flex justify-between items-center">
                  <div>
                    <span class="text-slate-400">Inspector:</span> <strong class="text-white">${trace.quality_review.inspector_name || 'QA Team'}</strong>
                    <p class="text-slate-300 mt-1 italic">"${trace.quality_review.remarks || 'Standard sign-off'}"</p>
                  </div>
                  <span class="px-2.5 py-1 rounded text-xs font-bold badge-qa-approved">${trace.quality_review.decision}</span>
                </div>
              ` : `
                <div class="text-slate-400 italic">No formal QA disposition recorded yet.</div>
              `}
            </div>
          </div>

          <!-- 4. Outbound Dispatch -->
          <div class="relative">
            <div class="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-sky-500 border-4 border-slate-900"></div>
            <div class="text-xs uppercase font-bold text-sky-400 tracking-wider">4. Outbound Logistics & Dispatch</div>
            <div class="bg-slate-800/60 p-4 rounded-lg border border-slate-700/60 mt-2 text-xs">
              ${trace.dispatch ? `
                <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
                  <div><span class="text-slate-400">Challan:</span> <span class="font-mono text-white">${trace.dispatch.dispatch_code}</span></div>
                  <div><span class="text-slate-400">Carrier:</span> <span class="text-white">${trace.dispatch.carrier_name || 'Direct'}</span></div>
                  <div><span class="text-slate-400">Date:</span> <span class="font-mono text-white">${trace.dispatch.dispatch_date}</span></div>
                  <div><span class="text-slate-400">Status:</span> <span class="font-bold text-sky-400">${trace.dispatch.status}</span></div>
                </div>
              ` : `
                <div class="text-slate-400 italic">Unit currently in warehouse; not yet assigned to an outbound dispatch challan.</div>
              `}
            </div>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    resultContainer.innerHTML = `
      <div class="p-6 bg-rose-900/20 border border-rose-800 rounded-xl text-center text-rose-300 text-sm">
        <i data-lucide="alert-circle" class="w-6 h-6 mx-auto mb-2 text-rose-400"></i>
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

  container.innerHTML = '<div class="p-4 text-center text-slate-400">Loading attendance roll call...</div>';
  try {
    const today = await api.getTodayAttendance();
    document.getElementById('att-present-count').textContent = today.present_count || 0;
    document.getElementById('att-absent-count').textContent = today.absent_count || 0;
    document.getElementById('att-rate').textContent = `${today.attendance_rate || 0}%`;

    const records = today.records || [];
    container.innerHTML = records.map(r => `
      <div class="bg-slate-800/60 p-3 rounded-lg border border-slate-700/50 flex justify-between items-center text-xs">
        <div>
          <div class="font-semibold text-white">${r.first_name} ${r.last_name}</div>
          <div class="text-slate-400 font-mono text-[10px]">${r.emp_code} • ${r.department_name || 'Floor'}</div>
        </div>
        <div class="text-right">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
            r.status === 'PRESENT' ? 'badge-passed' :
            r.status === 'ON_LEAVE' ? 'badge-allocated' : 'badge-failed'
          }">${r.status}</span>
          <div class="text-[10px] font-mono text-slate-400 mt-1">${r.punch_in || '--:--'} - ${r.punch_out || '--:--'}</div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-rose-400 text-xs">Error: ${err.message}</div>`;
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

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  renderUserBar();
  loadCurrentTab();
  if (window.lucide) window.lucide.createIcons();
});
