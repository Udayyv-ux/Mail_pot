document.addEventListener('DOMContentLoaded', () => {

    auth.checkUrlTokens();
    const loginScreen = document.getElementById('admin-login-screen');

    auth.getCurrentUser().then(user => {
        if (!user || user.role !== 'admin') {
            if (user && user.role !== 'admin') {
                window.location.href = '/client/';
                return;
            }
            loginScreen.style.display = 'flex';
        } else {
            loginScreen.style.display = 'none';
            initAdmin();
        }
    });

    // Auth Guard now relies on the /api/auth/google endpoint directly
    // The google auth button is hardcoded in the HTML to do window.location.href

    document.getElementById('btn-admin-logout').addEventListener('click', () => {
        auth.logout();
    });

    // Custom API wrapper for Admin
    const adminApi = {
        async fetchJSON(path, options = {}) {
            const token = localStorage.getItem('admin_token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;
            
            const res = await fetch(`/api${path}`, { ...options, headers });
            const data = await res.json();
            if (!res.ok) {
                if (res.status === 401) {
                    localStorage.removeItem('admin_token');
                    window.location.reload();
                }
                throw new Error(data.detail || "API Error");
            }
            return data;
        },
        get(path) { return this.fetchJSON(path); },
        post(path, body) { return this.fetchJSON(path, { method: 'POST', body: JSON.stringify(body) }); },
        put(path, body) { return this.fetchJSON(path, { method: 'PUT', body: JSON.stringify(body) }); },
        delete(path) { return this.fetchJSON(path, { method: 'DELETE' }); }
    };

    // Router
    const router = {
        routes: {},
        on(path, callback) { this.routes[path] = callback; },
        async navigate(path) {
            document.querySelectorAll('.page-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            
            const pageEl = document.getElementById(`page-${path}`);
            if (pageEl) pageEl.classList.add('active');
            
            const navEl = document.querySelector(`.nav-item[data-route="${path}"]`);
            if (navEl) navEl.classList.add('active');
            
            if (this.routes[path]) await this.routes[path]();
        },
        init() {
            document.querySelectorAll('.nav-item').forEach(el => {
                el.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.navigate(el.dataset.route);
                });
            });
            this.navigate('dashboard');
        }
    };

    let adminChart = null;

    function initAdmin() {
        router.on('dashboard', loadDashboard);
        router.on('users', loadUsers);
        router.on('plans', loadPlans);
        router.on('settings', loadSettings);
        router.on('policies', loadPolicies);
        router.init();
    }

    // --- Dashboard ---
    async function loadDashboard() {
        try {
            const stats = await adminApi.get('/admin/stats');
            document.getElementById('stat-users').textContent = stats.total_users || 0;
            document.getElementById('stat-plans').textContent = stats.active_plans || 0;
            document.getElementById('stat-emails').textContent = stats.emails_24h || 0;
            document.getElementById('stat-demos').textContent = stats.demo_requests || 0;

            loadDemoRequests();
            loadAnalyticsChart();
        } catch (e) {}
    }

    async function loadDemoRequests() {
        try {
            const demos = await adminApi.get('/admin/demos');
            const list = document.getElementById('demo-requests-list');
            list.innerHTML = '';
            demos.forEach(d => {
                const div = document.createElement('div');
                div.className = 'p-4 border-b border-white/10';
                div.innerHTML = `
                    <div class="flex justify-between items-start mb-2">
                        <strong class="text-white">${d.name} <span class="text-gray-400 text-sm font-normal">(${d.company || 'N/A'})</span></strong>
                        <span class="text-xs text-gray-500">${new Date(d.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="text-sm text-secondary mb-2">${d.email}</div>
                    <div class="text-sm text-gray-300 bg-dark/50 p-2 rounded">${d.message || 'No message provided.'}</div>
                `;
                list.appendChild(div);
            });
        } catch(e) {}
    }

    async function loadAnalyticsChart() {
        try {
            const stats = await adminApi.get('/admin/analytics/chart');
            const ctx = document.getElementById('admin-chart').getContext('2d');
            
            if(adminChart) adminChart.destroy();
            
            adminChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: stats.labels || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Total Platform Emails Sent',
                        data: stats.data || [0,0,0,0,0,0,0],
                        backgroundColor: '#ec4899',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        } catch(e) {
            console.log("Analytics error:", e);
        }
    }

    // --- Users ---
    async function loadUsers() {
        try {
            const clients = await adminApi.get('/admin/clients');
            const tbody = document.getElementById('client-list');
            tbody.innerHTML = '';
            clients.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="p-4 text-white">${c.email}</td>
                    <td class="p-4 text-gray-400">${c.company_name || '-'}</td>
                    <td class="p-4"><span class="px-3 py-1 rounded-full text-xs font-bold bg-primary/20 text-primary">${c.plan?.name || 'Free'}</span></td>
                    <td class="p-4 text-right space-x-2">
                        <button class="text-secondary hover:text-pink-400 font-semibold text-sm" onclick="openClientFeatures('${c.id}', '${c.email}')">Features</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch(e) {}
    }

    window.openClientFeatures = async (id, email) => {
        document.getElementById('cf-id').value = id;
        document.getElementById('cf-email').textContent = `Configuring features for ${email}`;
        
        // Fetch client specific features if endpoint exists
        try {
            const client = await adminApi.get(`/admin/clients/${id}`);
            let features = {};
            try { features = JSON.parse(client.features_json || "{}"); } catch(e){}
            document.getElementById('cf-ai').checked = !!features.ai_matcher;
            document.getElementById('cf-whitelabel').checked = !!features.whitelabel;
        } catch(e) {}

        document.getElementById('client-features-modal').classList.add('active');
    };

    document.getElementById('form-client-features').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('cf-id').value;
        const features = {
            ai_matcher: document.getElementById('cf-ai').checked,
            whitelabel: document.getElementById('cf-whitelabel').checked
        };
        try {
            await adminApi.put(`/admin/clients/${id}/features`, features);
            components.showToast("Client features updated", "success");
            document.getElementById('client-features-modal').classList.remove('active');
        } catch(err) {
            components.showToast(err.message, "error");
        }
    });

    // --- Plans ---
    async function loadPlans() {
        try {
            const plans = await adminApi.get('/admin/plans');
            const container = document.getElementById('admin-plan-list');
            container.innerHTML = '';
            plans.forEach(plan => {
                let features = [];
                try { features = JSON.parse(plan.features_json); } catch(e){}
                const card = document.createElement('div');
                card.className = 'glass p-6 rounded-2xl border border-white/10';
                card.innerHTML = `
                    <h3 class="text-xl font-bold mb-2">${plan.name}</h3>
                    <div class="mb-4"><span class="text-3xl font-extrabold">$${plan.price_monthly}</span>/mo</div>
                    <div class="text-sm text-gray-400 mb-4">Limit: ${plan.daily_limit}/day</div>
                    <ul class="text-sm text-gray-300 space-y-1 mb-6 h-20 overflow-y-auto">${features.map(f => `<li>✓ ${f}</li>`).join('')}</ul>
                    <div class="flex gap-2">
                        <button class="flex-1 bg-white/10 hover:bg-white/20 text-white font-bold py-2 rounded transition-colors text-sm" onclick="editPlan('${plan.id}')">Edit</button>
                        <button class="flex-1 bg-red-500/20 hover:bg-red-500/40 text-red-400 font-bold py-2 rounded transition-colors text-sm" onclick="deletePlan('${plan.id}')">Delete</button>
                    </div>
                `;
                container.appendChild(card);
            });
        } catch(e) {}
    }

    window.openPlanModal = () => {
        document.getElementById('form-plan').reset();
        document.getElementById('plan-id').value = '';
        document.getElementById('plan-modal-title').textContent = 'Create Plan';
        document.getElementById('plan-modal').classList.add('active');
    };

    window.editPlan = async (id) => {
        try {
            const plans = await adminApi.get('/admin/plans');
            const plan = plans.find(p => p.id === id);
            if(!plan) return;
            
            document.getElementById('plan-id').value = plan.id;
            document.getElementById('plan-name').value = plan.name;
            document.getElementById('plan-price').value = plan.price_monthly;
            document.getElementById('plan-limit').value = plan.daily_limit;
            document.getElementById('plan-features').value = plan.features_json;
            document.getElementById('plan-modal-title').textContent = 'Edit Plan';
            document.getElementById('plan-modal').classList.add('active');
        } catch(e){}
    };

    document.getElementById('form-plan').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('plan-id').value;
        const payload = {
            name: document.getElementById('plan-name').value,
            price_monthly: parseFloat(document.getElementById('plan-price').value),
            daily_limit: parseInt(document.getElementById('plan-limit').value),
            features_json: document.getElementById('plan-features').value
        };
        try {
            if(id) await adminApi.put(`/admin/plans/${id}`, payload);
            else await adminApi.post(`/admin/plans`, payload);
            document.getElementById('plan-modal').classList.remove('active');
            components.showToast("Plan saved", "success");
            loadPlans();
        } catch(err) { components.showToast(err.message, "error"); }
    });

    window.deletePlan = async (id) => {
        if(!confirm("Delete this plan?")) return;
        try { await adminApi.delete(`/admin/plans/${id}`); loadPlans(); } catch(e){}
    };

    // --- Global Settings ---
    async function loadSettings() {
        try {
            const settings = await adminApi.get('/admin/settings');
            const map = {};
            settings.forEach(s => map[s.key] = s.value);
            
            document.getElementById('admin-groq').value = map['default_groq_api_key'] || '';
            document.getElementById('admin-gcp-email').value = map['gcp_service_account_email'] || '';
            document.getElementById('admin-gcp-json').value = map['gcp_service_account_json'] || '';
            document.getElementById('admin-rzp-key').value = map['razorpay_key_id'] || '';
            document.getElementById('admin-rzp-secret').value = map['razorpay_key_secret'] || '';
        } catch(e) {}
    }

    document.getElementById('form-admin-settings').addEventListener('submit', async(e) => {
        e.preventDefault();
        const payload = {
            default_groq_api_key: document.getElementById('admin-groq').value,
            gcp_service_account_email: document.getElementById('admin-gcp-email').value,
            gcp_service_account_json: document.getElementById('admin-gcp-json').value,
            razorpay_key_id: document.getElementById('admin-rzp-key').value,
            razorpay_key_secret: document.getElementById('admin-rzp-secret').value,
        };
        try {
            await adminApi.post('/admin/settings', payload);
            components.showToast("Settings saved", "success");
        } catch(err) { components.showToast(err.message, "error"); }
    });

    // --- Policies ---
    async function loadPolicies() {
        try {
            const policies = await adminApi.get('/public/policies');
            const list = document.getElementById('policy-list');
            list.innerHTML = '';
            policies.forEach(p => {
                const div = document.createElement('div');
                div.className = 'flex justify-between items-center p-4 bg-dark/50 rounded-lg';
                div.innerHTML = `
                    <div><h4 class="font-bold text-white">${p.title}</h4><p class="text-xs text-gray-500">/${p.slug}</p></div>
                    <div class="space-x-2">
                        <button class="text-primary hover:text-indigo-400 text-sm font-semibold" onclick="editPolicy('${p.slug}')">Edit</button>
                        <button class="text-red-400 hover:text-red-300 text-sm font-semibold" onclick="deletePolicy('${p.slug}')">Delete</button>
                    </div>
                `;
                list.appendChild(div);
            });
        } catch(e) {}
    }

    window.openPolicyModal = () => {
        document.getElementById('form-policy').reset();
        document.getElementById('pol-slug').readOnly = false;
        document.getElementById('policy-modal').classList.add('active');
    };

    window.editPolicy = async (slug) => {
        try {
            const p = await adminApi.get(`/public/policies/${slug}`);
            document.getElementById('pol-slug').value = p.slug;
            document.getElementById('pol-slug').readOnly = true;
            document.getElementById('pol-title').value = p.title;
            document.getElementById('pol-content').value = p.content_md;
            document.getElementById('policy-modal').classList.add('active');
        } catch(e){}
    };

    document.getElementById('form-policy').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            slug: document.getElementById('pol-slug').value,
            title: document.getElementById('pol-title').value,
            content_md: document.getElementById('pol-content').value
        };
        try {
            await adminApi.post('/admin/policies', payload);
            document.getElementById('policy-modal').classList.remove('active');
            components.showToast("Policy saved", "success");
            loadPolicies();
        } catch(err) { components.showToast(err.message, "error"); }
    });

    window.deletePolicy = async (slug) => {
        if(!confirm("Delete this policy?")) return;
        try { await adminApi.delete(`/admin/policies/${slug}`); loadPolicies(); } catch(e){}
    };

    // --- Notifications ---
    document.getElementById('form-notif').addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = document.getElementById('notif-msg').value;
        try {
            await adminApi.post('/admin/notifications', { message: msg });
            components.showToast("Broadcast sent!", "success");
            document.getElementById('notif-modal').classList.remove('active');
            document.getElementById('form-notif').reset();
        } catch(err) { components.showToast(err.message, "error"); }
    });

});
