// Anti Gravity LIMS - Frontend Application
const API_BASE = window.location.port === '8888' ? '/api' : 'http://127.0.0.1:8888/api';
let token = localStorage.getItem('lims_token');
let currentUser = null;
let currentPage = 'dashboard';

// ==================== API HELPER ====================
async function api(endpoint, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers: { ...headers, ...options.headers } });
    if (res.status === 401) { logout(); return null; }
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

async function apiForm(endpoint, formData) {
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}${endpoint}`, { method: 'POST', headers, body: formData });
    if (res.status === 401) { logout(); return null; }
    if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail || 'Failed'); }
    return res.json();
}

// ==================== AUTH ====================
function logout() {
    token = null; currentUser = null;
    localStorage.removeItem('lims_token');
    renderLogin();
}

async function login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: formData
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
    const data = await res.json();
    token = data.access_token;
    localStorage.setItem('lims_token', token);
    currentUser = await api('/auth/me');
    renderApp();
}

// ==================== RENDER LOGIN ====================
function renderLogin() {
    document.getElementById('app').innerHTML = `
    <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900">
        <div class="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">
            <div class="text-center mb-8">
                <div class="w-16 h-16 bg-blue-600 rounded-xl mx-auto mb-4 flex items-center justify-center">
                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
                </div>
                <h1 class="text-2xl font-bold text-gray-800">Anti Gravity LIMS</h1>
                <p class="text-gray-500 text-sm mt-1">Laboratory Information Management System</p>
            </div>
            <form id="loginForm" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Username</label>
                    <input type="text" id="loginUser" class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="Enter username" required>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
                    <input type="password" id="loginPass" class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" placeholder="Enter password" required>
                </div>
                <div id="loginError" class="text-red-500 text-sm hidden"></div>
                <button type="submit" class="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition">Sign In</button>
            </form>
            <p class="text-center text-xs text-gray-400 mt-6">21 CFR Part 11 Compliant • GxP Validated</p>
        </div>
    </div>`;
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            await login(document.getElementById('loginUser').value, document.getElementById('loginPass').value);
        } catch (err) {
            document.getElementById('loginError').textContent = err.message;
            document.getElementById('loginError').classList.remove('hidden');
        }
    });
}

// ==================== NAVIGATION ====================
const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'layout-dashboard' },
    { id: 'samples', label: 'Samples', icon: 'flask-conical' },
    { id: 'products', label: 'Products', icon: 'package' },
    { id: 'tests', label: 'Tests', icon: 'test-tubes' },
    { id: 'specifications', label: 'Specifications', icon: 'file-check' },
    { id: 'oos', label: 'OOS Investigations', icon: 'alert-triangle' },
    { id: 'instruments', label: 'Instruments', icon: 'microscope' },
    { id: 'stability', label: 'Stability', icon: 'thermometer' },
    { id: 'chemicals', label: 'Chemicals & Reagents', icon: 'beaker' },
    { id: 'standards', label: 'Reference Standards', icon: 'award' },
    { id: 'columns', label: 'Columns', icon: 'cylinder' },
    { id: 'volumetric', label: 'Volumetric Solutions', icon: 'droplets' },
    { id: 'sap', label: 'SAP Integration', icon: 'network' },
    { id: 'users', label: 'User Management', icon: 'users', roles: ['Admin'] },
    { id: 'audit', label: 'Audit Trail', icon: 'scroll-text' },
];

function getStatusColor(status) {
    const colors = {
        'Active': 'bg-green-100 text-green-700', 'Approved': 'bg-green-100 text-green-700',
        'Pending': 'bg-yellow-100 text-yellow-700', 'Pending Approval': 'bg-yellow-100 text-yellow-700',
        'Logged': 'bg-blue-100 text-blue-700', 'Received': 'bg-indigo-100 text-indigo-700',
        'Under Review': 'bg-purple-100 text-purple-700', 'Submitted': 'bg-purple-100 text-purple-700',
        'OOS Investigation': 'bg-red-100 text-red-700', 'Open': 'bg-red-100 text-red-700',
        'Rejected': 'bg-red-100 text-red-700', 'Closed': 'bg-gray-100 text-gray-700',
        'Inactive': 'bg-gray-100 text-gray-700', 'Expired': 'bg-red-100 text-red-700',
        'Scheduled': 'bg-blue-100 text-blue-700', 'Draft': 'bg-gray-100 text-gray-600',
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
}

// ==================== MAIN APP LAYOUT ====================
function renderApp() {
    const filteredNav = navItems.filter(n => !n.roles || n.roles.includes(currentUser.role));
    document.getElementById('app').innerHTML = `
    <div class="flex h-screen overflow-hidden">
        <aside class="sidebar w-64 bg-gradient-to-b from-slate-900 to-slate-800 text-white flex flex-col">
            <div class="p-4 border-b border-slate-700">
                <div class="flex items-center gap-3">
                    <div class="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
                        <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
                    </div>
                    <div><h2 class="font-bold text-sm">Anti Gravity LIMS</h2><p class="text-xs text-slate-400">v2.0</p></div>
                </div>
            </div>
            <nav class="flex-1 overflow-y-auto py-2">
                ${filteredNav.map(n => `
                    <a href="#" class="nav-item flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 ${currentPage === n.id ? 'active' : ''}" data-page="${n.id}">
                        <i data-lucide="${n.icon}" class="w-4 h-4"></i>${n.label}
                    </a>
                `).join('')}
            </nav>
            <div class="p-4 border-t border-slate-700">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-xs font-bold">${currentUser.full_name.charAt(0)}</div>
                    <div class="flex-1 min-w-0"><p class="text-sm font-medium truncate">${currentUser.full_name}</p><p class="text-xs text-slate-400">${currentUser.role}</p></div>
                    <button onclick="logout()" class="text-slate-400 hover:text-white"><i data-lucide="log-out" class="w-4 h-4"></i></button>
                </div>
            </div>
        </aside>
        <main class="flex-1 overflow-y-auto">
            <header class="bg-white border-b px-6 py-4 flex items-center justify-between">
                <h1 id="pageTitle" class="text-xl font-semibold text-gray-800"></h1>
                <div class="flex items-center gap-3">
                    <span class="text-sm text-gray-500">${new Date().toLocaleDateString()}</span>
                </div>
            </header>
            <div id="pageContent" class="p-6 fade-in"></div>
        </main>
    </div>`;
    document.querySelectorAll('.nav-item').forEach(el => {
        el.addEventListener('click', (e) => { e.preventDefault(); navigateTo(el.dataset.page); });
    });
    lucide.createIcons();
    navigateTo(currentPage);
}

function navigateTo(page) {
    currentPage = page;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.page === page));
    const titleMap = { dashboard: 'Dashboard', samples: 'Sample Management', products: 'Products', tests: 'Test Parameters', specifications: 'Specifications', oos: 'OOS Investigations', instruments: 'Instrument Management', stability: 'Stability Management', chemicals: 'Chemicals & Reagents', standards: 'Reference Standards', columns: 'Column Management', volumetric: 'Volumetric Solutions', sap: 'SAP Integration', users: 'User Management', audit: 'Audit Trail' };
    document.getElementById('pageTitle').textContent = titleMap[page] || page;
    loadPage(page);
}

// ==================== PAGE ROUTER ====================
async function loadPage(page) {
    const content = document.getElementById('pageContent');
    content.innerHTML = '<div class="flex justify-center py-12"><div class="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div></div>';
    try {
        switch(page) {
            case 'dashboard': await renderDashboard(content); break;
            case 'samples': await renderSamples(content); break;
            case 'products': await renderProducts(content); break;
            case 'tests': await renderTests(content); break;
            case 'specifications': await renderSpecifications(content); break;
            case 'oos': await renderOOS(content); break;
            case 'instruments': await renderInstruments(content); break;
            case 'stability': await renderStability(content); break;
            case 'chemicals': await renderChemicals(content); break;
            case 'standards': await renderStandards(content); break;
            case 'columns': await renderColumns(content); break;
            case 'volumetric': await renderVolumetric(content); break;
            case 'sap': await renderSAP(content); break;
            case 'users': await renderUsers(content); break;
            case 'audit': await renderAudit(content); break;
            default: content.innerHTML = '<p>Page not found</p>';
        }
    } catch(e) { content.innerHTML = `<div class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">${e.message}</div>`; }
}

// ==================== DASHBOARD ====================
async function renderDashboard(el) {
    const stats = await api('/dashboard');
    el.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="card bg-white rounded-xl p-5 border">
            <div class="flex items-center justify-between"><div><p class="text-sm text-gray-500">Total Samples</p><p class="text-2xl font-bold text-gray-800">${stats.total_samples}</p></div><div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center"><i data-lucide="flask-conical" class="w-5 h-5 text-blue-600"></i></div></div>
        </div>
        <div class="card bg-white rounded-xl p-5 border">
            <div class="flex items-center justify-between"><div><p class="text-sm text-gray-500">Pending Review</p><p class="text-2xl font-bold text-gray-800">${stats.pending_reviews}</p></div><div class="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center"><i data-lucide="clock" class="w-5 h-5 text-yellow-600"></i></div></div>
        </div>
        <div class="card bg-white rounded-xl p-5 border">
            <div class="flex items-center justify-between"><div><p class="text-sm text-gray-500">OOS Open</p><p class="text-2xl font-bold text-red-600">${stats.oos_open}</p></div><div class="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center"><i data-lucide="alert-triangle" class="w-5 h-5 text-red-600"></i></div></div>
        </div>
        <div class="card bg-white rounded-xl p-5 border">
            <div class="flex items-center justify-between"><div><p class="text-sm text-gray-500">Calibration Due</p><p class="text-2xl font-bold text-orange-600">${stats.instruments_due_calibration}</p></div><div class="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center"><i data-lucide="wrench" class="w-5 h-5 text-orange-600"></i></div></div>
        </div>
    </div>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="card bg-white rounded-xl p-5 border">
            <h3 class="font-semibold text-gray-800 mb-3">Today's Activity</h3>
            <div class="space-y-3">
                <div class="flex justify-between items-center"><span class="text-sm text-gray-600">Samples Logged</span><span class="font-semibold">${stats.samples_today}</span></div>
                <div class="flex justify-between items-center"><span class="text-sm text-gray-600">Batches Approved</span><span class="font-semibold text-green-600">${stats.approved_today}</span></div>
                <div class="flex justify-between items-center"><span class="text-sm text-gray-600">Batches Rejected</span><span class="font-semibold text-red-600">${stats.rejected_today}</span></div>
                <div class="flex justify-between items-center"><span class="text-sm text-gray-600">Pending Samples</span><span class="font-semibold text-yellow-600">${stats.pending_samples}</span></div>
            </div>
        </div>
        <div class="card bg-white rounded-xl p-5 border">
            <h3 class="font-semibold text-gray-800 mb-3">Quick Actions</h3>
            <div class="grid grid-cols-2 gap-2">
                <button onclick="navigateTo('samples')" class="p-3 bg-blue-50 rounded-lg text-sm text-blue-700 hover:bg-blue-100 transition">Log New Sample</button>
                <button onclick="navigateTo('instruments')" class="p-3 bg-green-50 rounded-lg text-sm text-green-700 hover:bg-green-100 transition">View Instruments</button>
                <button onclick="navigateTo('oos')" class="p-3 bg-red-50 rounded-lg text-sm text-red-700 hover:bg-red-100 transition">OOS Cases</button>
                <button onclick="navigateTo('sap')" class="p-3 bg-purple-50 rounded-lg text-sm text-purple-700 hover:bg-purple-100 transition">SAP Interface</button>
            </div>
        </div>
    </div>`;
    lucide.createIcons();
}

// ==================== SAMPLES PAGE ====================
async function renderSamples(el) {
    const samples = await api('/samples');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4">
        <p class="text-sm text-gray-500">${samples.length} samples total</p>
        <button onclick="showCreateSampleModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Log Sample</button>
    </div>
    <div class="bg-white rounded-xl border overflow-hidden">
        <table class="w-full text-sm">
            <thead class="bg-gray-50"><tr>
                <th class="px-4 py-3 text-left font-medium text-gray-600">Sample Code</th>
                <th class="px-4 py-3 text-left font-medium text-gray-600">Product</th>
                <th class="px-4 py-3 text-left font-medium text-gray-600">Batch</th>
                <th class="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th class="px-4 py-3 text-left font-medium text-gray-600">Logged</th>
                <th class="px-4 py-3 text-left font-medium text-gray-600">Actions</th>
            </tr></thead>
            <tbody>${samples.map(s => `<tr class="border-t hover:bg-gray-50">
                <td class="px-4 py-3 font-mono text-blue-600">${s.sample_code}</td>
                <td class="px-4 py-3">${s.product.name}</td>
                <td class="px-4 py-3">${s.batch_number}</td>
                <td class="px-4 py-3"><span class="status-badge ${getStatusColor(s.status)}">${s.status}</span></td>
                <td class="px-4 py-3 text-gray-500">${new Date(s.logged_at).toLocaleDateString()}</td>
                <td class="px-4 py-3">
                    ${s.status === 'Logged' ? `<button onclick="receiveSample(${s.id})" class="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded hover:bg-indigo-100">Receive</button>` : ''}
                    ${s.status === 'Under Review' ? `<button onclick="showReleaseModal(${s.id})" class="text-xs bg-green-50 text-green-700 px-2 py-1 rounded hover:bg-green-100">Release</button>` : ''}
                    <button onclick="showSampleDetail(${s.id})" class="text-xs bg-gray-50 text-gray-700 px-2 py-1 rounded hover:bg-gray-100 ml-1">View</button>
                </td>
            </tr>`).join('')}</tbody>
        </table>
    </div>`;
}

async function receiveSample(id) {
    if (!confirm('Confirm sample receipt?')) return;
    await api(`/samples/${id}/receive`, { method: 'POST' });
    navigateTo('samples');
}

async function showSampleDetail(id) {
    const samples = await api('/samples');
    const s = samples.find(x => x.id === id);
    if (!s) return;
    const content = document.getElementById('pageContent');
    content.innerHTML = `
    <button onclick="navigateTo('samples')" class="text-sm text-blue-600 mb-4 inline-block">&larr; Back to Samples</button>
    <div class="bg-white rounded-xl border p-6 mb-4">
        <div class="flex justify-between items-start mb-4">
            <div><h2 class="text-lg font-bold">${s.sample_code}</h2><p class="text-gray-500">${s.product.name} - Batch ${s.batch_number}</p></div>
            <span class="status-badge ${getStatusColor(s.status)}">${s.status}</span>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span class="text-gray-500">Quantity</span><p class="font-medium">${s.quantity_received} ${s.unit}</p></div>
            <div><span class="text-gray-500">Logged By</span><p class="font-medium">${s.logged_by || '-'}</p></div>
            <div><span class="text-gray-500">SAP Lot</span><p class="font-medium">${s.sap_inspection_lot || 'N/A'}</p></div>
            <div><span class="text-gray-500">SAP UD Posted</span><p class="font-medium">${s.sap_ud_posted ? 'Yes' : 'No'}</p></div>
        </div>
    </div>
    <div class="bg-white rounded-xl border p-6">
        <h3 class="font-semibold mb-3">Test Results</h3>
        <table class="w-full text-sm"><thead class="bg-gray-50"><tr>
            <th class="px-3 py-2 text-left">Test</th><th class="px-3 py-2 text-left">Limits</th><th class="px-3 py-2 text-left">Result</th><th class="px-3 py-2 text-left">Status</th><th class="px-3 py-2 text-left">OOS</th>
        </tr></thead><tbody>${s.results.map(r => `<tr class="border-t ${r.is_oos ? 'bg-red-50' : ''}">
            <td class="px-3 py-2">${r.test.name}</td>
            <td class="px-3 py-2 text-gray-500">${r.min_limit != null ? `${r.min_limit} - ${r.max_limit}` : r.expected_result || '-'}</td>
            <td class="px-3 py-2 font-medium">${r.result_value != null ? r.result_value : r.result_text || '-'}</td>
            <td class="px-3 py-2"><span class="status-badge ${getStatusColor(r.status)}">${r.status}</span></td>
            <td class="px-3 py-2">${r.is_oos ? '<span class="text-red-600 font-bold">YES</span>' : '-'}</td>
        </tr>`).join('')}</tbody></table>
    </div>`;
}

// ==================== CREATE SAMPLE MODAL ====================
async function showCreateSampleModal() {
    const products = await api('/products');
    const activeProducts = products.filter(p => p.status === 'Active');
    showModal('Log New Sample', `
        <form id="createSampleForm" class="space-y-3">
            <div><label class="block text-sm font-medium mb-1">Product</label>
                <select id="smpProduct" class="w-full border rounded-lg px-3 py-2" required>
                    <option value="">Select product...</option>
                    ${activeProducts.map(p => `<option value="${p.id}">${p.name} (${p.code})</option>`).join('')}
                </select></div>
            <div><label class="block text-sm font-medium mb-1">Batch Number</label>
                <input id="smpBatch" class="w-full border rounded-lg px-3 py-2" required></div>
            <div class="grid grid-cols-2 gap-3">
                <div><label class="block text-sm font-medium mb-1">Quantity</label>
                    <input id="smpQty" type="number" step="0.01" class="w-full border rounded-lg px-3 py-2" required></div>
                <div><label class="block text-sm font-medium mb-1">Unit</label>
                    <input id="smpUnit" class="w-full border rounded-lg px-3 py-2" value="mL" required></div>
            </div>
            <div><label class="block text-sm font-medium mb-1">SAP Inspection Lot (Optional)</label>
                <input id="smpSAPLot" class="w-full border rounded-lg px-3 py-2" placeholder="e.g., 000012345678"></div>
            <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Log Sample</button>
        </form>
    `);
    document.getElementById('createSampleForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            await api('/samples', { method: 'POST', body: JSON.stringify({
                product_id: parseInt(document.getElementById('smpProduct').value),
                batch_number: document.getElementById('smpBatch').value,
                quantity_received: parseFloat(document.getElementById('smpQty').value),
                unit: document.getElementById('smpUnit').value,
                sap_inspection_lot: document.getElementById('smpSAPLot').value || null
            })});
            closeModal(); navigateTo('samples');
        } catch(e) { alert(e.message); }
    });
}

// ==================== PRODUCTS PAGE ====================
async function renderProducts(el) {
    const products = await api('/products');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4">
        <p class="text-sm text-gray-500">${products.length} products</p>
        ${currentUser.role === 'Admin' ? '<button onclick="showCreateProductModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Add Product</button>' : ''}
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        ${products.map(p => `<div class="card bg-white rounded-xl border p-5">
            <div class="flex justify-between items-start mb-2"><h3 class="font-semibold text-gray-800">${p.name}</h3><span class="status-badge ${getStatusColor(p.status)}">${p.status}</span></div>
            <p class="text-sm text-gray-500 mb-3">Code: ${p.code}</p>
            <p class="text-xs text-gray-400">${p.description || ''}</p>
            ${p.status === 'Pending Approval' && ['Supervisor','QA'].includes(currentUser.role) ? `<button onclick="approveProduct(${p.id})" class="mt-3 text-xs bg-green-50 text-green-700 px-3 py-1.5 rounded-lg hover:bg-green-100">Approve</button>` : ''}
        </div>`).join('')}
    </div>`;
}

async function approveProduct(id) {
    const pwd = prompt('Enter password for E-Signature:');
    if (!pwd) return;
    try { await api(`/products/${id}/approve`, { method: 'POST', body: JSON.stringify({ password: pwd }) }); navigateTo('products'); }
    catch(e) { alert(e.message); }
}

// ==================== TESTS PAGE ====================
async function renderTests(el) {
    const tests = await api('/tests');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4">
        <p class="text-sm text-gray-500">${tests.length} test parameters</p>
        ${currentUser.role === 'Admin' ? '<button onclick="showCreateTestModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Add Test</button>' : ''}
    </div>
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Code</th><th class="px-4 py-3 text-left">Name</th><th class="px-4 py-3 text-left">Type</th><th class="px-4 py-3 text-left">Unit</th><th class="px-4 py-3 text-left">Category</th><th class="px-4 py-3 text-left">Status</th></tr></thead>
        <tbody>${tests.map(t => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3 font-mono">${t.code}</td><td class="px-4 py-3">${t.name}</td><td class="px-4 py-3">${t.type}</td><td class="px-4 py-3">${t.unit || '-'}</td><td class="px-4 py-3">${t.category || '-'}</td><td class="px-4 py-3"><span class="status-badge ${getStatusColor(t.status)}">${t.status}</span></td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function showCreateTestModal() {
    showModal('Add Test Parameter', `<form id="createTestForm" class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
            <div><label class="block text-sm font-medium mb-1">Code</label><input id="tstCode" class="w-full border rounded-lg px-3 py-2" required></div>
            <div><label class="block text-sm font-medium mb-1">Name</label><input id="tstName" class="w-full border rounded-lg px-3 py-2" required></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
            <div><label class="block text-sm font-medium mb-1">Type</label><select id="tstType" class="w-full border rounded-lg px-3 py-2"><option>Quantitative</option><option>Qualitative</option><option>Statistical-1</option><option>Statistical-2</option></select></div>
            <div><label class="block text-sm font-medium mb-1">Unit</label><input id="tstUnit" class="w-full border rounded-lg px-3 py-2"></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
            <div><label class="block text-sm font-medium mb-1">Category</label><input id="tstCat" class="w-full border rounded-lg px-3 py-2" placeholder="e.g., Chemical"></div>
            <div><label class="block text-sm font-medium mb-1">Technique</label><input id="tstTech" class="w-full border rounded-lg px-3 py-2" placeholder="e.g., HPLC"></div>
        </div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Create Test</button>
    </form>`);
    document.getElementById('createTestForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/tests', { method: 'POST', body: JSON.stringify({ code: document.getElementById('tstCode').value, name: document.getElementById('tstName').value, type: document.getElementById('tstType').value, unit: document.getElementById('tstUnit').value, category: document.getElementById('tstCat').value, technique: document.getElementById('tstTech').value }) }); closeModal(); navigateTo('tests'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== SPECIFICATIONS PAGE ====================
async function renderSpecifications(el) {
    const specs = await api('/specifications');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4"><p class="text-sm text-gray-500">${specs.length} specifications</p></div>
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Product</th><th class="px-4 py-3 text-left">Version</th><th class="px-4 py-3 text-left">Tests</th><th class="px-4 py-3 text-left">Status</th><th class="px-4 py-3 text-left">Actions</th></tr></thead>
        <tbody>${specs.map(s => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3">${s.product.name}</td><td class="px-4 py-3">v${s.version}</td><td class="px-4 py-3">${s.tests.length} tests</td><td class="px-4 py-3"><span class="status-badge ${getStatusColor(s.status)}">${s.status}</span></td>
            <td class="px-4 py-3">${s.status === 'Pending Approval' && ['Supervisor','QA'].includes(currentUser.role) ? `<button onclick="approveSpec(${s.id})" class="text-xs bg-green-50 text-green-700 px-2 py-1 rounded hover:bg-green-100">Approve</button>` : ''}</td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function approveSpec(id) {
    const pwd = prompt('Enter password for E-Signature:');
    if (!pwd) return;
    try { await api(`/specifications/${id}/approve`, { method: 'POST', body: JSON.stringify({ password: pwd }) }); navigateTo('specifications'); }
    catch(e) { alert(e.message); }
}

// ==================== OOS PAGE ====================
async function renderOOS(el) {
    const oos = await api('/oos');
    el.innerHTML = `
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">ID</th><th class="px-4 py-3 text-left">Test</th><th class="px-4 py-3 text-left">Phase 1 Comments</th><th class="px-4 py-3 text-left">Status</th><th class="px-4 py-3 text-left">Created</th><th class="px-4 py-3 text-left">Actions</th></tr></thead>
        <tbody>${oos.map(o => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3">#${o.id}</td><td class="px-4 py-3">${o.test.name}</td><td class="px-4 py-3 max-w-xs truncate">${o.phase1_comments}</td><td class="px-4 py-3"><span class="status-badge ${getStatusColor(o.status)}">${o.status}</span></td><td class="px-4 py-3">${new Date(o.created_at).toLocaleDateString()}</td>
            <td class="px-4 py-3">${o.status === 'Open' && ['Supervisor','QA'].includes(currentUser.role) ? `<button onclick="showCloseOOSModal(${o.id})" class="text-xs bg-green-50 text-green-700 px-2 py-1 rounded hover:bg-green-100">Close</button>` : ''}</td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function showCloseOOSModal(id) {
    showModal('Close OOS Investigation', `<form id="closeOOSForm" class="space-y-3">
        <div><label class="block text-sm font-medium mb-1">Root Cause</label><textarea id="oosRoot" class="w-full border rounded-lg px-3 py-2" rows="3" required></textarea></div>
        <div><label class="block text-sm font-medium mb-1">Corrective Action</label><textarea id="oosCapa" class="w-full border rounded-lg px-3 py-2" rows="3" required></textarea></div>
        <div><label class="block text-sm font-medium mb-1">Password (E-Sign)</label><input type="password" id="oosPwd" class="w-full border rounded-lg px-3 py-2" required></div>
        <button type="submit" class="w-full bg-green-600 text-white py-2 rounded-lg font-medium hover:bg-green-700">Close Investigation</button>
    </form>`);
    document.getElementById('closeOOSForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api(`/oos/${id}/close`, { method: 'POST', body: JSON.stringify({ root_cause: document.getElementById('oosRoot').value, corrective_action: document.getElementById('oosCapa').value, password: document.getElementById('oosPwd').value }) }); closeModal(); navigateTo('oos'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== INSTRUMENTS PAGE ====================
async function renderInstruments(el) {
    const instruments = await api('/instruments');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4">
        <p class="text-sm text-gray-500">${instruments.length} instruments</p>
        ${currentUser.role === 'Admin' ? '<button onclick="showCreateInstrumentModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Add Instrument</button>' : ''}
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        ${instruments.map(i => `<div class="card bg-white rounded-xl border p-5">
            <div class="flex justify-between items-start mb-2"><h3 class="font-semibold">${i.name}</h3><span class="status-badge ${getStatusColor(i.status)}">${i.status}</span></div>
            <p class="text-sm text-gray-500">Code: ${i.code} | ${i.category || ''}</p>
            <p class="text-xs text-gray-400 mt-1">${i.manufacturer || ''} ${i.model_number || ''}</p>
            <div class="mt-3 text-xs text-gray-500">
                <p>Location: ${i.location || 'N/A'}</p>
                <p>Cal Due: ${i.calibration_due_date ? new Date(i.calibration_due_date).toLocaleDateString() : 'N/A'}</p>
            </div>
        </div>`).join('')}
    </div>`;
}

async function showCreateInstrumentModal() {
    showModal('Add Instrument', `<form id="createInstrForm" class="space-y-3">
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Code</label><input id="instrCode" class="w-full border rounded-lg px-3 py-2" required></div><div><label class="block text-sm font-medium mb-1">Name</label><input id="instrName" class="w-full border rounded-lg px-3 py-2" required></div></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Category</label><select id="instrCat" class="w-full border rounded-lg px-3 py-2"><option>HPLC</option><option>GC</option><option>UV-Vis</option><option>Balance</option><option>pH Meter</option><option>Karl Fischer</option><option>Dissolution</option><option>Other</option></select></div><div><label class="block text-sm font-medium mb-1">Location</label><input id="instrLoc" class="w-full border rounded-lg px-3 py-2"></div></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Manufacturer</label><input id="instrMfr" class="w-full border rounded-lg px-3 py-2"></div><div><label class="block text-sm font-medium mb-1">Model</label><input id="instrModel" class="w-full border rounded-lg px-3 py-2"></div></div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Add Instrument</button>
    </form>`);
    document.getElementById('createInstrForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/instruments', { method: 'POST', body: JSON.stringify({ code: document.getElementById('instrCode').value, name: document.getElementById('instrName').value, category: document.getElementById('instrCat').value, location: document.getElementById('instrLoc').value, manufacturer: document.getElementById('instrMfr').value, model_number: document.getElementById('instrModel').value }) }); closeModal(); navigateTo('instruments'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== STABILITY PAGE ====================
async function renderStability(el) {
    const protocols = await api('/stability/protocols');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4">
        <p class="text-sm text-gray-500">${protocols.length} stability protocols</p>
        ${['Admin','Supervisor'].includes(currentUser.role) ? '<button onclick="showCreateProtocolModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ New Protocol</button>' : ''}
    </div>
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Protocol</th><th class="px-4 py-3 text-left">Product</th><th class="px-4 py-3 text-left">Condition</th><th class="px-4 py-3 text-left">Duration</th><th class="px-4 py-3 text-left">Type</th><th class="px-4 py-3 text-left">Status</th></tr></thead>
        <tbody>${protocols.map(p => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3 font-mono">${p.protocol_code}</td><td class="px-4 py-3">${p.product.name}</td><td class="px-4 py-3">${p.condition}</td><td class="px-4 py-3">${p.duration_months} months</td><td class="px-4 py-3">${p.study_type || '-'}</td><td class="px-4 py-3"><span class="status-badge ${getStatusColor(p.status)}">${p.status}</span></td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function showCreateProtocolModal() {
    const products = await api('/products');
    showModal('New Stability Protocol', `<form id="createProtoForm" class="space-y-3">
        <div><label class="block text-sm font-medium mb-1">Product</label><select id="protoProduct" class="w-full border rounded-lg px-3 py-2" required>${products.filter(p=>p.status==='Active').map(p=>`<option value="${p.id}">${p.name}</option>`).join('')}</select></div>
        <div><label class="block text-sm font-medium mb-1">Condition</label><select id="protoCond" class="w-full border rounded-lg px-3 py-2"><option>25°C/60%RH</option><option>30°C/65%RH</option><option>40°C/75%RH</option></select></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Duration (months)</label><input id="protoDur" type="number" class="w-full border rounded-lg px-3 py-2" value="24" required></div><div><label class="block text-sm font-medium mb-1">Study Type</label><select id="protoType" class="w-full border rounded-lg px-3 py-2"><option>Long Term</option><option>Accelerated</option><option>Intermediate</option></select></div></div>
        <div><label class="block text-sm font-medium mb-1">Testing Frequency</label><input id="protoFreq" class="w-full border rounded-lg px-3 py-2" value="0,3,6,9,12,18,24" placeholder="months comma separated"></div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Create Protocol</button>
    </form>`);
    document.getElementById('createProtoForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/stability/protocols', { method: 'POST', body: JSON.stringify({ product_id: parseInt(document.getElementById('protoProduct').value), condition: document.getElementById('protoCond').value, duration_months: parseInt(document.getElementById('protoDur').value), study_type: document.getElementById('protoType').value, testing_frequency: document.getElementById('protoFreq').value }) }); closeModal(); navigateTo('stability'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== CHEMICALS PAGE ====================
async function renderChemicals(el) {
    const chems = await api('/chemicals');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4"><p class="text-sm text-gray-500">${chems.length} chemicals/reagents</p>
        ${currentUser.role === 'Admin' ? '<button onclick="showCreateChemModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Add Chemical</button>' : ''}</div>
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Code</th><th class="px-4 py-3 text-left">Name</th><th class="px-4 py-3 text-left">Grade</th><th class="px-4 py-3 text-left">Qty Remaining</th><th class="px-4 py-3 text-left">Expiry</th><th class="px-4 py-3 text-left">Status</th></tr></thead>
        <tbody>${chems.map(c => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3 font-mono">${c.code}</td><td class="px-4 py-3">${c.name}</td><td class="px-4 py-3">${c.grade || '-'}</td><td class="px-4 py-3">${c.quantity_remaining || '-'} ${c.unit || ''}</td><td class="px-4 py-3">${c.expiry_date ? new Date(c.expiry_date).toLocaleDateString() : '-'}</td><td class="px-4 py-3"><span class="status-badge ${getStatusColor(c.status)}">${c.status}</span></td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function showCreateChemModal() {
    showModal('Add Chemical/Reagent', `<form id="createChemForm" class="space-y-3">
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Code</label><input id="chemCode" class="w-full border rounded-lg px-3 py-2" required></div><div><label class="block text-sm font-medium mb-1">Name</label><input id="chemName" class="w-full border rounded-lg px-3 py-2" required></div></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Grade</label><select id="chemGrade" class="w-full border rounded-lg px-3 py-2"><option>AR</option><option>LR</option><option>HPLC</option><option>GR</option></select></div><div><label class="block text-sm font-medium mb-1">Manufacturer</label><input id="chemMfr" class="w-full border rounded-lg px-3 py-2"></div></div>
        <div class="grid grid-cols-3 gap-3"><div><label class="block text-sm font-medium mb-1">Quantity</label><input id="chemQty" type="number" step="0.01" class="w-full border rounded-lg px-3 py-2"></div><div><label class="block text-sm font-medium mb-1">Unit</label><input id="chemUnit" class="w-full border rounded-lg px-3 py-2" value="mL"></div><div><label class="block text-sm font-medium mb-1">CAS No.</label><input id="chemCAS" class="w-full border rounded-lg px-3 py-2"></div></div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Add Chemical</button>
    </form>`);
    document.getElementById('createChemForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/chemicals', { method: 'POST', body: JSON.stringify({ code: document.getElementById('chemCode').value, name: document.getElementById('chemName').value, grade: document.getElementById('chemGrade').value, manufacturer: document.getElementById('chemMfr').value, quantity_received: parseFloat(document.getElementById('chemQty').value) || null, unit: document.getElementById('chemUnit').value, cas_number: document.getElementById('chemCAS').value }) }); closeModal(); navigateTo('chemicals'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== REFERENCE STANDARDS PAGE ====================
async function renderStandards(el) {
    const stds = await api('/reference-standards');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4"><p class="text-sm text-gray-500">${stds.length} reference standards</p>
        ${currentUser.role === 'Admin' ? '<button onclick="showCreateStdModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Add Standard</button>' : ''}</div>
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Code</th><th class="px-4 py-3 text-left">Name</th><th class="px-4 py-3 text-left">Lot</th><th class="px-4 py-3 text-left">Potency</th><th class="px-4 py-3 text-left">Qty Remaining</th><th class="px-4 py-3 text-left">Expiry</th><th class="px-4 py-3 text-left">Status</th></tr></thead>
        <tbody>${stds.map(s => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3 font-mono">${s.code}</td><td class="px-4 py-3">${s.name}</td><td class="px-4 py-3">${s.lot_number || '-'}</td><td class="px-4 py-3">${s.potency ? s.potency + '%' : '-'}</td><td class="px-4 py-3">${s.quantity_remaining || '-'} ${s.unit || ''}</td><td class="px-4 py-3">${s.expiry_date ? new Date(s.expiry_date).toLocaleDateString() : '-'}</td><td class="px-4 py-3"><span class="status-badge ${getStatusColor(s.status)}">${s.status}</span></td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function showCreateStdModal() {
    showModal('Add Reference Standard', `<form id="createStdForm" class="space-y-3">
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Code</label><input id="stdCode" class="w-full border rounded-lg px-3 py-2" required></div><div><label class="block text-sm font-medium mb-1">Name</label><input id="stdName" class="w-full border rounded-lg px-3 py-2" required></div></div>
        <div class="grid grid-cols-3 gap-3"><div><label class="block text-sm font-medium mb-1">Lot Number</label><input id="stdLot" class="w-full border rounded-lg px-3 py-2"></div><div><label class="block text-sm font-medium mb-1">Potency (%)</label><input id="stdPotency" type="number" step="0.01" class="w-full border rounded-lg px-3 py-2"></div><div><label class="block text-sm font-medium mb-1">Category</label><select id="stdCat" class="w-full border rounded-lg px-3 py-2"><option>Primary</option><option>Secondary</option><option>Working</option></select></div></div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Add Standard</button>
    </form>`);
    document.getElementById('createStdForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/reference-standards', { method: 'POST', body: JSON.stringify({ code: document.getElementById('stdCode').value, name: document.getElementById('stdName').value, lot_number: document.getElementById('stdLot').value, potency: parseFloat(document.getElementById('stdPotency').value) || null, category: document.getElementById('stdCat').value }) }); closeModal(); navigateTo('standards'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== COLUMNS PAGE ====================
async function renderColumns(el) {
    const cols = await api('/columns');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4"><p class="text-sm text-gray-500">${cols.length} columns</p>
        ${currentUser.role === 'Admin' ? '<button onclick="showCreateColModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Add Column</button>' : ''}</div>
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Code</th><th class="px-4 py-3 text-left">Name</th><th class="px-4 py-3 text-left">Type</th><th class="px-4 py-3 text-left">Dimensions</th><th class="px-4 py-3 text-left">Injections</th><th class="px-4 py-3 text-left">Status</th></tr></thead>
        <tbody>${cols.map(c => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3 font-mono">${c.code}</td><td class="px-4 py-3">${c.name}</td><td class="px-4 py-3">${c.type || '-'}</td><td class="px-4 py-3">${c.dimensions || '-'}</td><td class="px-4 py-3">${c.current_injections}${c.max_injections ? '/'+c.max_injections : ''}</td><td class="px-4 py-3"><span class="status-badge ${getStatusColor(c.status)}">${c.status}</span></td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function showCreateColModal() {
    showModal('Add Column', `<form id="createColForm" class="space-y-3">
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Code</label><input id="colCode" class="w-full border rounded-lg px-3 py-2" required></div><div><label class="block text-sm font-medium mb-1">Name</label><input id="colName" class="w-full border rounded-lg px-3 py-2" required></div></div>
        <div class="grid grid-cols-3 gap-3"><div><label class="block text-sm font-medium mb-1">Type</label><select id="colType" class="w-full border rounded-lg px-3 py-2"><option>C18</option><option>C8</option><option>HILIC</option><option>Phenyl</option><option>CN</option></select></div><div><label class="block text-sm font-medium mb-1">Dimensions</label><input id="colDim" class="w-full border rounded-lg px-3 py-2" placeholder="250x4.6mm, 5um"></div><div><label class="block text-sm font-medium mb-1">Max Injections</label><input id="colMaxInj" type="number" class="w-full border rounded-lg px-3 py-2"></div></div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Add Column</button>
    </form>`);
    document.getElementById('createColForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/columns', { method: 'POST', body: JSON.stringify({ code: document.getElementById('colCode').value, name: document.getElementById('colName').value, type: document.getElementById('colType').value, dimensions: document.getElementById('colDim').value, max_injections: parseInt(document.getElementById('colMaxInj').value) || null }) }); closeModal(); navigateTo('columns'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== VOLUMETRIC SOLUTIONS PAGE ====================
async function renderVolumetric(el) {
    const sols = await api('/volumetric-solutions');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4"><p class="text-sm text-gray-500">${sols.length} volumetric solutions</p>
        <button onclick="showCreateVSModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Add Solution</button></div>
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Code</th><th class="px-4 py-3 text-left">Name</th><th class="px-4 py-3 text-left">Concentration</th><th class="px-4 py-3 text-left">Factor</th><th class="px-4 py-3 text-left">Prepared By</th><th class="px-4 py-3 text-left">Expiry</th><th class="px-4 py-3 text-left">Status</th></tr></thead>
        <tbody>${sols.map(s => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3 font-mono">${s.code}</td><td class="px-4 py-3">${s.name}</td><td class="px-4 py-3">${s.concentration || '-'}</td><td class="px-4 py-3">${s.standardization_factor || '-'}</td><td class="px-4 py-3">${s.prepared_by || '-'}</td><td class="px-4 py-3">${s.expiry_date ? new Date(s.expiry_date).toLocaleDateString() : '-'}</td><td class="px-4 py-3"><span class="status-badge ${getStatusColor(s.status)}">${s.status}</span></td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function showCreateVSModal() {
    showModal('Add Volumetric Solution', `<form id="createVSForm" class="space-y-3">
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Code</label><input id="vsCode" class="w-full border rounded-lg px-3 py-2" required></div><div><label class="block text-sm font-medium mb-1">Name</label><input id="vsName" class="w-full border rounded-lg px-3 py-2" required></div></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Concentration</label><input id="vsConc" class="w-full border rounded-lg px-3 py-2" placeholder="e.g., 0.1N"></div><div><label class="block text-sm font-medium mb-1">Standardization Factor</label><input id="vsFactor" type="number" step="0.0001" class="w-full border rounded-lg px-3 py-2"></div></div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Add Solution</button>
    </form>`);
    document.getElementById('createVSForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/volumetric-solutions', { method: 'POST', body: JSON.stringify({ code: document.getElementById('vsCode').value, name: document.getElementById('vsName').value, concentration: document.getElementById('vsConc').value, standardization_factor: parseFloat(document.getElementById('vsFactor').value) || null }) }); closeModal(); navigateTo('volumetric'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== SAP INTEGRATION PAGE ====================
async function renderSAP(el) {
    const logs = await api('/sap/logs').catch(() => []);
    el.innerHTML = `
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="bg-white rounded-xl border p-5">
            <h3 class="font-semibold mb-3">Read Batch Data from SAP</h3>
            <p class="text-sm text-gray-500 mb-3">Fetch material/batch info from SAP QM inspection lot</p>
            <form id="sapReadForm" class="space-y-3">
                <input id="sapLot" class="w-full border rounded-lg px-3 py-2" placeholder="SAP Inspection Lot Number" required>
                <button type="submit" class="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 w-full">Fetch from SAP</button>
            </form>
            <div id="sapReadResult" class="mt-3"></div>
        </div>
        <div class="bg-white rounded-xl border p-5">
            <h3 class="font-semibold mb-3">Post Usage Decision to SAP</h3>
            <p class="text-sm text-gray-500 mb-3">Send batch verdict (Accept/Reject) to SAP QM via ZLIMS_PROCESS_UD4</p>
            <form id="sapUDForm" class="space-y-3">
                <input id="sapUDSample" type="number" class="w-full border rounded-lg px-3 py-2" placeholder="Sample ID" required>
                <select id="sapUDCode" class="w-full border rounded-lg px-3 py-2"><option value="A">Accept (A)</option><option value="R">Reject (R)</option></select>
                <input type="password" id="sapUDPwd" class="w-full border rounded-lg px-3 py-2" placeholder="Password (E-Sign)" required>
                <button type="submit" class="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 w-full">Post Usage Decision</button>
            </form>
            <div id="sapUDResult" class="mt-3"></div>
        </div>
    </div>
    <div class="bg-white rounded-xl border p-5">
        <h3 class="font-semibold mb-3">Integration Log</h3>
        <table class="w-full text-sm"><thead class="bg-gray-50"><tr><th class="px-3 py-2 text-left">Time</th><th class="px-3 py-2 text-left">Type</th><th class="px-3 py-2 text-left">Direction</th><th class="px-3 py-2 text-left">Lot</th><th class="px-3 py-2 text-left">Status</th><th class="px-3 py-2 text-left">User</th></tr></thead>
        <tbody>${logs.map(l => `<tr class="border-t"><td class="px-3 py-2 text-xs">${new Date(l.created_at).toLocaleString()}</td><td class="px-3 py-2">${l.transaction_type}</td><td class="px-3 py-2">${l.direction}</td><td class="px-3 py-2">${l.sap_inspection_lot || '-'}</td><td class="px-3 py-2"><span class="status-badge ${l.status === 'Success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">${l.status}</span></td><td class="px-3 py-2">${l.created_by || '-'}</td></tr>`).join('')}</tbody></table>
    </div>`;
    document.getElementById('sapReadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const data = await api('/sap/read-batch', { method: 'POST', body: JSON.stringify({ inspection_lot: document.getElementById('sapLot').value }) });
            document.getElementById('sapReadResult').innerHTML = `<div class="bg-green-50 border border-green-200 rounded p-3 text-sm"><pre>${JSON.stringify(data, null, 2)}</pre></div>`;
        } catch(e) { document.getElementById('sapReadResult').innerHTML = `<div class="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">${e.message}</div>`; }
    });
    document.getElementById('sapUDForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const data = await api('/sap/usage-decision', { method: 'POST', body: JSON.stringify({ sample_id: parseInt(document.getElementById('sapUDSample').value), ud_code: document.getElementById('sapUDCode').value, password: document.getElementById('sapUDPwd').value }) });
            document.getElementById('sapUDResult').innerHTML = `<div class="bg-green-50 border border-green-200 rounded p-3 text-sm">${data.message}</div>`;
        } catch(e) { document.getElementById('sapUDResult').innerHTML = `<div class="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700">${e.message}</div>`; }
    });
}

// ==================== USERS PAGE ====================
async function renderUsers(el) {
    const users = await api('/users');
    el.innerHTML = `
    <div class="flex justify-between items-center mb-4"><p class="text-sm text-gray-500">${users.length} users</p>
        <button onclick="showCreateUserModal()" class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ Add User</button></div>
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Username</th><th class="px-4 py-3 text-left">Full Name</th><th class="px-4 py-3 text-left">Role</th><th class="px-4 py-3 text-left">Department</th><th class="px-4 py-3 text-left">Active</th><th class="px-4 py-3 text-left">Actions</th></tr></thead>
        <tbody>${users.map(u => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3 font-mono">${u.username}</td><td class="px-4 py-3">${u.full_name}</td><td class="px-4 py-3">${u.role}</td><td class="px-4 py-3">${u.department || '-'}</td><td class="px-4 py-3">${u.is_active ? '<span class="text-green-600">●</span>' : '<span class="text-red-600">●</span>'}</td>
            <td class="px-4 py-3"><button onclick="toggleUser(${u.id}, ${!u.is_active})" class="text-xs ${u.is_active ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'} px-2 py-1 rounded">${u.is_active ? 'Deactivate' : 'Activate'}</button></td></tr>`).join('')}</tbody>
    </table></div>`;
}

async function toggleUser(id, active) {
    await api(`/users/${id}`, { method: 'PUT', body: JSON.stringify({ is_active: active }) });
    navigateTo('users');
}

async function showCreateUserModal() {
    showModal('Add User', `<form id="createUserForm" class="space-y-3">
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Username</label><input id="newUsername" class="w-full border rounded-lg px-3 py-2" required></div><div><label class="block text-sm font-medium mb-1">Password</label><input id="newPassword" type="password" class="w-full border rounded-lg px-3 py-2" required></div></div>
        <div><label class="block text-sm font-medium mb-1">Full Name</label><input id="newFullName" class="w-full border rounded-lg px-3 py-2" required></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Role</label><select id="newRole" class="w-full border rounded-lg px-3 py-2"><option>Admin</option><option>Analyst</option><option>Supervisor</option><option>QA</option></select></div><div><label class="block text-sm font-medium mb-1">Department</label><input id="newDept" class="w-full border rounded-lg px-3 py-2"></div></div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Create User</button>
    </form>`);
    document.getElementById('createUserForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/users', { method: 'POST', body: JSON.stringify({ username: document.getElementById('newUsername').value, password: document.getElementById('newPassword').value, full_name: document.getElementById('newFullName').value, role: document.getElementById('newRole').value, department: document.getElementById('newDept').value }) }); closeModal(); navigateTo('users'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== AUDIT TRAIL PAGE ====================
async function renderAudit(el) {
    const logs = await api('/audit-logs?limit=50');
    el.innerHTML = `
    <div class="bg-white rounded-xl border overflow-hidden"><table class="w-full text-sm">
        <thead class="bg-gray-50"><tr><th class="px-4 py-3 text-left">Timestamp</th><th class="px-4 py-3 text-left">User</th><th class="px-4 py-3 text-left">Action</th><th class="px-4 py-3 text-left">Table</th><th class="px-4 py-3 text-left">Record</th><th class="px-4 py-3 text-left">Comments</th></tr></thead>
        <tbody>${logs.map(l => `<tr class="border-t hover:bg-gray-50"><td class="px-4 py-3 text-xs text-gray-500">${new Date(l.timestamp).toLocaleString()}</td><td class="px-4 py-3">${l.username}</td><td class="px-4 py-3 font-mono text-xs">${l.action}</td><td class="px-4 py-3">${l.table_name}</td><td class="px-4 py-3">#${l.record_id || '-'}</td><td class="px-4 py-3 max-w-xs truncate text-xs text-gray-500">${l.comments || '-'}</td></tr>`).join('')}</tbody>
    </table></div>`;
}

// ==================== PRODUCT CREATION MODAL ====================
async function showCreateProductModal() {
    showModal('Add Product', `<form id="createProdForm" class="space-y-3">
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Code</label><input id="prodCode" class="w-full border rounded-lg px-3 py-2" required></div><div><label class="block text-sm font-medium mb-1">Name</label><input id="prodName" class="w-full border rounded-lg px-3 py-2" required></div></div>
        <div><label class="block text-sm font-medium mb-1">Description</label><textarea id="prodDesc" class="w-full border rounded-lg px-3 py-2" rows="2"></textarea></div>
        <div class="grid grid-cols-2 gap-3"><div><label class="block text-sm font-medium mb-1">Material Type</label><select id="prodType" class="w-full border rounded-lg px-3 py-2"><option value="">Select...</option><option>RM</option><option>PM</option><option>FG</option><option>IP</option></select></div><div><label class="block text-sm font-medium mb-1">Retest Period (days)</label><input id="prodRetest" type="number" class="w-full border rounded-lg px-3 py-2"></div></div>
        <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg font-medium hover:bg-blue-700">Create Product</button>
    </form>`);
    document.getElementById('createProdForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api('/products', { method: 'POST', body: JSON.stringify({ code: document.getElementById('prodCode').value, name: document.getElementById('prodName').value, description: document.getElementById('prodDesc').value, material_type: document.getElementById('prodType').value || null, retest_period_days: parseInt(document.getElementById('prodRetest').value) || null }) }); closeModal(); navigateTo('products'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== RELEASE MODAL ====================
async function showReleaseModal(sampleId) {
    showModal('Release Batch', `<form id="releaseForm" class="space-y-3">
        <div><label class="block text-sm font-medium mb-1">Verdict</label><select id="releaseVerdict" class="w-full border rounded-lg px-3 py-2"><option value="Approved">Approved</option><option value="Rejected">Rejected</option></select></div>
        <div><label class="block text-sm font-medium mb-1">Comments</label><textarea id="releaseComments" class="w-full border rounded-lg px-3 py-2" rows="2"></textarea></div>
        <div><label class="block text-sm font-medium mb-1">Password (E-Sign)</label><input type="password" id="releasePwd" class="w-full border rounded-lg px-3 py-2" required></div>
        <button type="submit" class="w-full bg-green-600 text-white py-2 rounded-lg font-medium hover:bg-green-700">Release Batch</button>
    </form>`);
    document.getElementById('releaseForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const verdict = document.getElementById('releaseVerdict').value;
        try { await api(`/samples/${sampleId}/release?verdict=${verdict}`, { method: 'POST', body: JSON.stringify({ password: document.getElementById('releasePwd').value, comments: document.getElementById('releaseComments').value }) }); closeModal(); navigateTo('samples'); }
        catch(e) { alert(e.message); }
    });
}

// ==================== MODAL UTILITY ====================
function showModal(title, content) {
    const modal = document.createElement('div');
    modal.id = 'modal';
    modal.className = 'fixed inset-0 z-50 flex items-center justify-center modal-overlay bg-black/40';
    modal.innerHTML = `<div class="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between p-5 border-b"><h3 class="font-semibold text-lg">${title}</h3><button onclick="closeModal()" class="text-gray-400 hover:text-gray-600 text-xl">&times;</button></div>
        <div class="p-5">${content}</div>
    </div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
}

function closeModal() {
    const modal = document.getElementById('modal');
    if (modal) modal.remove();
}

// ==================== INIT ====================
(async function init() {
    if (token) {
        try { currentUser = await api('/auth/me'); renderApp(); }
        catch(e) { renderLogin(); }
    } else { renderLogin(); }
})();
