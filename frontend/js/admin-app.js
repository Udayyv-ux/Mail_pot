document.addEventListener('DOMContentLoaded', () => {

    // Parse OAuth tokens from URL, then check auth
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

    document.getElementById('btn-admin-logout')?.addEventListener('click', () => {
        auth.logout();
    });

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
            // Backend endpoint: GET /api/admin/dashboard
            // Returns: { total_clients, active_campaigns, total_emails_sent, total_revenue }
            const stats = await api.get('/admin/dashboard');
            const el = (id) => document.getElementById(id);
            
            if(el('stat-users')) el('stat-users').textContent = stats.total_clients || 0;
            if(el('stat-plans')) el('stat-plans').textContent = '-';
            if(el('stat-emails')) el('stat-emails').textContent = stats.total_emails_sent || 0;
            if(el('stat-demos')) el('stat-demos').textContent = '-';

            loadDemoRequests();
            loadAnalyticsChart();
        } catch (e) {
            console.error("Admin dashboard error:", e);
        }
    }

    async function loadDemoRequests() {
        try {
            // Backend endpoint: GET /api/admin/demo-requests
            const demos = await api.get('/admin/demo-requests');
            const list = document.getElementById('demo-requests-list');
            if(!list) return;
            list.innerHTML = '';
            
            if(!demos || demos.length === 0) {
                list.innerHTML = '<div class="p-4 text-center text-gray-500">No demo requests yet.</div>';
                return;
            }
            
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
        } catch(e) {
            console.log("Demo requests error:", e);
        }
    }

    async function loadAnalyticsChart() {
        try {
            // Backend endpoint: GET /api/admin/analytics/chart
            const stats = await api.get('/admin/analytics/chart');
            const canvas = document.getElementById('admin-chart');
            if(!canvas) return;
            const ctx = canvas.getContext('2d');
            
            if(adminChart) adminChart.destroy();
            
            adminChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: stats.labels || [],
                    datasets: [{
                        label: 'Total Platform Emails Sent',
                        data: stats.data || [],
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
            console.log("Admin analytics chart error:", e);
        }
    }

    // --- Users ---
    async function loadUsers() {
        try {
            // Backend endpoint: GET /api/admin/clients
            // Returns: [{ id, company_name, status, emails_sent_today }]
            const clients = await api.get('/admin/clients');
            const tbody = document.getElementById('client-list');
            if(!tbody) return;
            tbody.innerHTML = '';
            
            if(!clients || clients.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-500">No clients registered yet.</td></tr>';
                return;
            }
            
            clients.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="p-4 text-white">${c.company_name || '-'}</td>
                    <td class="p-4 text-gray-400">${c.status || 'active'}</td>
                    <td class="p-4"><span class="px-3 py-1 rounded-full text-xs font-bold bg-primary/20 text-primary">${c.emails_sent_today || 0} sent today</span></td>
                    <td class="p-4 text-right space-x-2">
                        <button class="text-secondary hover:text-pink-400 font-semibold text-sm" onclick="openClientFeatures('${c.id}', '${c.company_name || "Client"}')">Features</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch(e) {
            console.error("Load users error:", e);
        }
    }

    window.openClientFeatures = async (id, name) => {
        const cfId = document.getElementById('cf-id');
        const cfEmail = document.getElementById('cf-email');
        if(cfId) cfId.value = id;
        if(cfEmail) cfEmail.textContent = `Configuring features for ${name}`;
        
        try {
            const client = await api.get(`/admin/clients/${id}`);
            let features = {};
            try { features = JSON.parse(client.features_json || "{}"); } catch(e){}
            const cfAi = document.getElementById('cf-ai');
            const cfWl = document.getElementById('cf-whitelabel');
            if(cfAi) cfAi.checked = !!features.ai_matcher;
            if(cfWl) cfWl.checked = !!features.whitelabel;
        } catch(e) {}

        document.getElementById('client-features-modal')?.classList.add('active');
    };

    document.getElementById('form-client-features')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('cf-id').value;
        const features = {
            ai_matcher: document.getElementById('cf-ai').checked,
            whitelabel: document.getElementById('cf-whitelabel').checked
        };
        try {
            await api.put(`/admin/clients/${id}/features`, features);
            if(window.showToast) showToast("Client features updated", "success");
            document.getElementById('client-features-modal')?.classList.remove('active');
        } catch(err) {
            if(window.showToast) showToast(err.message, "error");
        }
    });

    // --- Plans ---
    async function loadPlans() {
        try {
            // Backend endpoint: GET /api/admin/plans
            const plans = await api.get('/admin/plans');
            const container = document.getElementById('admin-plan-list');
            if(!container) return;
            container.innerHTML = '';
            
            if(!plans || plans.length === 0) {
                container.innerHTML = '<div class="col-span-3 text-center text-gray-500 p-8">No plans created yet. Click "Add Plan" to create one.</div>';
                return;
            }
            
            plans.forEach(plan => {
                let features = [];
                try { features = JSON.parse(plan.features_json); } catch(e){}
                const card = document.createElement('div');
                card.className = 'glass p-6 rounded-2xl border border-white/10';
                card.innerHTML = `
                    <h3 class="text-xl font-bold mb-2">${plan.name}</h3>
                    <div class="mb-4"><span class="text-3xl font-extrabold">$${plan.price_monthly}</span>/mo</div>
                    <div class="text-sm text-gray-400 mb-4">Limit: ${plan.email_limit_daily}/day</div>
                    <ul class="text-sm text-gray-300 space-y-1 mb-6 h-20 overflow-y-auto">${features.map(f => `<li>✓ ${f}</li>`).join('')}</ul>
                    <div class="flex gap-2">
                        <button class="flex-1 bg-white/10 hover:bg-white/20 text-white font-bold py-2 rounded transition-colors text-sm" onclick="editPlan('${plan.id}')">Edit</button>
                        <button class="flex-1 bg-red-500/20 hover:bg-red-500/40 text-red-400 font-bold py-2 rounded transition-colors text-sm" onclick="deletePlan('${plan.id}')">Delete</button>
                    </div>
                `;
                container.appendChild(card);
            });
        } catch(e) {
            console.error("Load plans error:", e);
        }
    }

    window.openPlanModal = () => {
        document.getElementById('form-plan')?.reset();
        const planId = document.getElementById('plan-id');
        if(planId) planId.value = '';
        const title = document.getElementById('plan-modal-title');
        if(title) title.textContent = 'Create Plan';
        document.getElementById('plan-modal')?.classList.add('active');
    };

    window.editPlan = async (id) => {
        try {
            const plans = await api.get('/admin/plans');
            const plan = plans.find(p => p.id === id);
            if(!plan) return;
            
            const el = (elId) => document.getElementById(elId);
            if(el('plan-id')) el('plan-id').value = plan.id;
            if(el('plan-name')) el('plan-name').value = plan.name;
            if(el('plan-price')) el('plan-price').value = plan.price_monthly;
            if(el('plan-limit')) el('plan-limit').value = plan.email_limit_daily;
            if(el('plan-features')) el('plan-features').value = plan.features_json;
            if(el('plan-modal-title')) el('plan-modal-title').textContent = 'Edit Plan';
            document.getElementById('plan-modal')?.classList.add('active');
        } catch(e){}
    };

    document.getElementById('form-plan')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('plan-id').value;
        const payload = {
            name: document.getElementById('plan-name').value,
            description: '',
            price_monthly: parseFloat(document.getElementById('plan-price').value),
            price_yearly: parseFloat(document.getElementById('plan-price').value) * 10,
            email_limit_daily: parseInt(document.getElementById('plan-limit').value),
            features_json: document.getElementById('plan-features').value
        };
        try {
            if(id) await api.put(`/admin/plans/${id}`, payload);
            else await api.post(`/admin/plans`, payload);
            document.getElementById('plan-modal')?.classList.remove('active');
            if(window.showToast) showToast("Plan saved", "success");
            loadPlans();
        } catch(err) { if(window.showToast) showToast(err.message, "error"); }
    });

    window.deletePlan = async (id) => {
        if(!confirm("Delete this plan?")) return;
        try { await api.delete(`/admin/plans/${id}`); loadPlans(); } catch(e){}
    };

    // --- Global Settings ---
    async function loadSettings() {
        try {
            // Backend endpoint: GET /api/admin/settings
            // Returns: array of { id, key, value, category, description }
            const settings = await api.get('/admin/settings');
            const map = {};
            if(Array.isArray(settings)) {
                settings.forEach(s => map[s.key] = s.value);
            }
            
            const el = (id) => document.getElementById(id);
            if(el('admin-groq')) el('admin-groq').value = map['default_groq_api_key'] || '';
            if(el('admin-gcp-email')) el('admin-gcp-email').value = map['gcp_service_account_email'] || '';
            if(el('admin-gcp-json')) el('admin-gcp-json').value = map['gcp_service_account_json'] || '';
            if(el('admin-rzp-key')) el('admin-rzp-key').value = map['razorpay_key_id'] || '';
            if(el('admin-rzp-secret')) el('admin-rzp-secret').value = map['razorpay_key_secret'] || '';
        } catch(e) {
            console.error("Load settings error:", e);
        }
    }

    document.getElementById('form-admin-settings')?.addEventListener('submit', async(e) => {
        e.preventDefault();
        // Backend endpoint: PUT /api/admin/settings expects array of {key, value}
        const payload = [
            { key: 'default_groq_api_key', value: document.getElementById('admin-groq').value },
            { key: 'gcp_service_account_email', value: document.getElementById('admin-gcp-email').value },
            { key: 'gcp_service_account_json', value: document.getElementById('admin-gcp-json').value },
            { key: 'razorpay_key_id', value: document.getElementById('admin-rzp-key').value },
            { key: 'razorpay_key_secret', value: document.getElementById('admin-rzp-secret').value },
        ];
        try {
            await api.put('/admin/settings', payload);
            if(window.showToast) showToast("Settings saved", "success");
        } catch(err) { if(window.showToast) showToast(err.message, "error"); }
    });

    // --- Policies ---
    async function loadPolicies() {
        try {
            // Backend endpoint: GET /api/admin/policies
            const policies = await api.get('/admin/policies');
            const list = document.getElementById('policy-list');
            if(!list) return;
            list.innerHTML = '';
            
            if(!policies || policies.length === 0) {
                list.innerHTML = '<div class="p-4 text-center text-gray-500">No policies created yet.</div>';
                return;
            }
            
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
        } catch(e) {
            console.error("Load policies error:", e);
        }
    }

    window.openPolicyModal = () => {
        document.getElementById('form-policy')?.reset();
        const slug = document.getElementById('pol-slug');
        if(slug) slug.readOnly = false;
        document.getElementById('policy-modal')?.classList.add('active');
    };

    window.editPolicy = async (slug) => {
        try {
            const p = await api.get(`/public/policies/${slug}`);
            const el = (id) => document.getElementById(id);
            if(el('pol-slug')) { el('pol-slug').value = p.slug; el('pol-slug').readOnly = true; }
            if(el('pol-title')) el('pol-title').value = p.title;
            if(el('pol-content')) el('pol-content').value = p.content_html || '';
            document.getElementById('policy-modal')?.classList.add('active');
        } catch(e){}
    };

    document.getElementById('form-policy')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        // Backend endpoint: POST /api/admin/policies expects { title, slug, content_html, is_active }
        const payload = {
            slug: document.getElementById('pol-slug').value,
            title: document.getElementById('pol-title').value,
            content_html: document.getElementById('pol-content').value,
            is_active: true
        };
        try {
            await api.post('/admin/policies', payload);
            document.getElementById('policy-modal')?.classList.remove('active');
            if(window.showToast) showToast("Policy saved", "success");
            loadPolicies();
        } catch(err) { if(window.showToast) showToast(err.message, "error"); }
    });

    window.deletePolicy = async (slug) => {
        if(!confirm("Delete this policy?")) return;
        try { await api.delete(`/admin/policies/${slug}`); loadPolicies(); } catch(e){}
    };

    // --- Notifications ---
    document.getElementById('form-notif')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = document.getElementById('notif-msg')?.value;
        if(!msg) return;
        try {
            await api.post('/admin/notifications', { message: msg });
            if(window.showToast) showToast("Broadcast sent!", "success");
            document.getElementById('notif-modal')?.classList.remove('active');
            document.getElementById('form-notif')?.reset();
        } catch(err) { if(window.showToast) showToast(err.message, "error"); }
    });

});
