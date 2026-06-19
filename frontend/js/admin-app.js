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
            
            // Check if there's an error we can display
            const token = localStorage.getItem('access_token');
            if (token) {
                // If we have a token but user is null, it means the API call failed
                const errDiv = document.createElement('div');
                errDiv.className = 'text-red-400 mt-4 text-sm font-mono bg-black/50 p-2 rounded';
                errDiv.textContent = 'Auth failed. Please check the backend server logs. Are you sure you are running the backend on port 8000?';
                loginScreen.querySelector('.card').appendChild(errDiv);
            }
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
        currentRoute: null,
        on(path, callback) { this.routes[path] = callback; },
        async navigate(path) {
            if (!path) return;
            // Allow re-navigating to the same route (force refresh)
            this.currentRoute = path;
            window.location.hash = path;
            
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
            
            window.addEventListener('hashchange', () => {
                const path = window.location.hash.replace('#', '') || 'dashboard';
                this.navigate(path);
            });
            
            const initialPath = window.location.hash.replace('#', '') || 'dashboard';
            this.navigate(initialPath);
        }
    };

    let adminChart = null;

    function initAdmin() {
        router.on('dashboard', loadDashboard);
        router.on('users', loadUsers);
        router.on('plans', loadPlans);
        router.on('monitor', loadGlobalLogs);
        router.on('settings', loadSettings);
        router.on('landing', loadLandingContent);
        router.on('policies', loadPolicies);
        router.on('promo', loadPromoCodes);
        router.init();
    }

    // --- Dashboard ---
    async function loadDashboard() {
        try {
            const stats = await api.get('/admin/dashboard');
            const revenue = await api.get('/admin/revenue').catch(() => ({}));
            
            const el = (id) => document.getElementById(id);
            
            if(el('stat-users')) el('stat-users').textContent = stats.total_clients || 0;
            if(el('stat-plans')) el('stat-plans').textContent = revenue.active_subscriptions || 0;
            if(el('stat-emails')) el('stat-emails').textContent = stats.total_emails_sent || 0;
            if(el('stat-demos')) el('stat-demos').textContent = '-'; // We can populate this later


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
            
            const labels = stats?.labels || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
            const data = stats?.data || [0,0,0,0,0,0,0];
            
            adminChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Total Platform Emails Sent',
                        data: data,
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
                    <td class="p-4 text-white font-medium">${c.email}</td>
                    <td class="p-4 text-gray-300">${c.company_name || 'N/A'}</td>
                    <td class="p-4 text-gray-300"><span class="bg-primary/20 text-primary px-2 py-1 rounded-full text-xs">${c.plan || 'Free'}</span></td>
                    <td class="p-4 text-right">
                        <button onclick="resetUsage('${c.id}')" class="text-xs bg-dark/50 hover:bg-white/10 text-gray-300 py-1 px-3 rounded transition-colors mr-2">Reset Usage</button>
                        <button class="text-secondary hover:text-pink-400 font-semibold text-sm" onclick="viewClientDetails('${c.id}')">Details</button>
                        <button class="text-secondary hover:text-pink-400 font-semibold text-sm mr-2" onclick="openClientFeatures('${c.id}', '${c.company_name || "Client"}')">Features</button>
                        <button class="text-accent hover:text-white font-semibold text-sm" onclick="impersonateClient('${c.user_id}')">Impersonate</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch(e) {
            console.error("Load users error:", e);
        }
    }

    window.impersonateClient = async (userId) => {
        if(!confirm("Are you sure you want to impersonate this user? You will be redirected to the Client Portal.")) return;
        try {
            const res = await api.post(`/admin/impersonate/${userId}`);
            // Save admin token so we can restore it later
            const currentToken = localStorage.getItem('token');
            localStorage.setItem('admin_token', currentToken);
            
            // Set client token
            localStorage.setItem('token', res.access_token);
            window.location.href = '/client';
        } catch (e) {
            alert("Failed to impersonate: " + e.message);
        }
    };

    window.resetUsage = async (id) => {
        if(!confirm("Are you sure you want to reset this user's daily usage?")) return;
        try {
            await api.post(`/admin/clients/${id}/reset`);
            if(window.showToast) showToast("Usage reset successfully", "success");
            loadUsers();
        } catch (e) {
            alert("Failed to reset: " + e.message);
        }
    };

    window.viewClientDetails = async (id) => {
        try {
            const client = await api.get(`/admin/clients/${id}`);
            const modal = document.getElementById('client-details-modal');
            const content = document.getElementById('cd-content');
            
            content.innerHTML = `
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div><span class="text-gray-400">Company:</span> <span class="text-white">${client.company_name || 'N/A'}</span></div>
                    <div><span class="text-gray-400">Email:</span> <span class="text-white">${client.user?.email || 'N/A'}</span></div>
                    <div><span class="text-gray-400">Plan:</span> <span class="text-white">${client.plan?.name || 'Free'}</span></div>
                    <div><span class="text-gray-400">Status:</span> <span class="text-green-400">${client.status}</span></div>
                    <div><span class="text-gray-400">Daily Limit:</span> <span class="text-white">${client.daily_email_limit}</span></div>
                    <div><span class="text-gray-400">Sent Today:</span> <span class="text-white">${client.emails_sent_today}</span></div>
                    
                    <div class="col-span-2 mt-4"><strong class="text-white">Sheet Integration</strong></div>
                    <div class="col-span-2"><span class="text-gray-400">Sheet ID:</span> <span class="text-white break-all">${client.google_sheet_id || 'Not Connected'}</span></div>
                    <div><span class="text-gray-400">Target Cols:</span> <span class="text-white">${client.target_columns || 'Name, Email, Inquiry'}</span></div>
                    <div><span class="text-gray-400">Status Col:</span> <span class="text-white">${client.status_column || 'Status'}</span></div>
                    
                    <div class="col-span-2 mt-4"><strong class="text-white">Custom Overrides</strong></div>

                    <div><span class="text-gray-400">Groq Key:</span> <span class="text-white">${client.groq_api_key_enc ? 'Configured' : 'Using Global'}</span></div>
                </div>
            `;
            
            modal.showModal();
        } catch(e) {
            console.error("View details error:", e);
        }
    };

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

        document.getElementById('client-features-modal')?.showModal();
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
            document.getElementById('client-features-modal')?.close();
        } catch(err) {
            if(window.showToast) showToast(err.message, "error");
        }
    });

    window.savePlan = savePlan;
    window.editPlan = editPlan;
    window.deletePlan = deletePlan;

    // --- Global Monitor ---
    async function loadGlobalLogs() {
        try {
            const logs = await api.get('/admin/email-logs');
            const tbody = document.getElementById('global-log-list');
            if(!tbody) return;
            tbody.innerHTML = '';

            if(!logs || logs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-gray-500">No emails sent yet.</td></tr>';
                return;
            }

            logs.forEach(log => {
                const tr = document.createElement('tr');
                let statusBadge = '';
                if(log.status === 'sent') statusBadge = '<span class="badge badge-success badge-sm text-xs">Sent</span>';
                else if(log.status === 'failed') statusBadge = '<span class="badge badge-error badge-sm text-xs">Failed</span>';
                else if(log.status === 'bounced') statusBadge = '<span class="badge badge-warning badge-sm text-xs">Bounced</span>';
                else statusBadge = `<span class="badge badge-ghost badge-sm text-xs">${log.status}</span>`;

                tr.innerHTML = `
                    <td class="p-4 text-gray-300 font-mono text-xs">${log.client_id || 'Unknown'}</td>
                    <td class="p-4 text-white">${log.recipient_email}</td>
                    <td class="p-4">${statusBadge}</td>
                    <td class="p-4 text-gray-400 text-sm">${log.sent_at ? new Date(log.sent_at).toLocaleString() : '-'}</td>
                    <td class="p-4 text-error text-xs max-w-xs truncate" title="${log.error_message || ''}">${log.error_message || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch(e) {
            console.error("Load global logs error:", e);
        }
    };

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
                    <div class="text-sm text-gray-400 mb-4">Limit: ${plan.email_limit_daily}/day · ${plan.campaign_limit || 3} Campaigns</div>
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
        document.getElementById('plan-modal')?.showModal();
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
            if(el('plan-price-half-yearly')) el('plan-price-half-yearly').value = plan.price_half_yearly || (plan.price_monthly * 6);
            if(el('plan-price-yearly')) el('plan-price-yearly').value = plan.price_yearly || (plan.price_monthly * 12);
            if(el('plan-limit')) el('plan-limit').value = plan.email_limit_daily;
            if(el('plan-campaign-limit')) el('plan-campaign-limit').value = plan.campaign_limit || 3;
            if(el('plan-features')) {
                let feats = [];
                try { feats = JSON.parse(plan.features_json); } catch(e){}
                el('plan-features').value = feats.join('\n');
            }
            if(el('plan-modal-title')) el('plan-modal-title').textContent = 'Edit Plan';
            document.getElementById('plan-modal')?.showModal();
        } catch(e){}
    };

    document.getElementById('form-plan')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('plan-id').value;
        const featuresText = document.getElementById('plan-features').value;
        const featuresArray = featuresText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
        
        const payload = {
            name: document.getElementById('plan-name').value,
            description: '',
            price_monthly: parseFloat(document.getElementById('plan-price').value),
            price_half_yearly: parseFloat(document.getElementById('plan-price-half-yearly').value) || 0,
            price_yearly: parseFloat(document.getElementById('plan-price-yearly').value) || 0,
            email_limit_daily: parseInt(document.getElementById('plan-limit').value),
            campaign_limit: parseInt(document.getElementById('plan-campaign-limit').value) || 3,
            features_json: JSON.stringify(featuresArray)
        };
        try {
            if(id) await api.put(`/admin/plans/${id}`, payload);
            else await api.post(`/admin/plans`, payload);
            document.getElementById('plan-modal')?.close();
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
            settings.forEach(s => {
                if(s.key === 'GROQ_API_KEY') document.getElementById('admin-groq').value = s.value;

                if(s.key === 'GCP_SERVICE_EMAIL') document.getElementById('admin-gcp-email').value = s.value;
                if(s.key === 'GCP_CREDENTIALS_JSON') document.getElementById('admin-gcp-json').value = s.value;
                if(s.key === 'RAZORPAY_KEY_ID') document.getElementById('admin-rzp-key').value = s.value;
                if(s.key === 'RAZORPAY_SECRET') document.getElementById('admin-rzp-secret').value = s.value;
                if(s.key === 'MAINTENANCE_MODE') document.getElementById('admin-maintenance').checked = (s.value === 'true');
                if(s.key === 'LANDING_HOW_IT_WORKS_TITLE') document.getElementById('admin-how-it-works-title').value = s.value;
                if(s.key === 'LANDING_HOW_IT_WORKS_SUBTITLE') document.getElementById('admin-how-it-works-subtitle').value = s.value;
            });
            
            // Re-fetch the current logo to ensure it's not cached from an old upload if they just saved
            const img = document.getElementById('admin-current-logo');
            if (img) {
                img.src = '/api/logo?v=' + new Date().getTime();
                img.classList.remove('hidden');
            }
        } catch(e) {}
    }

    document.getElementById('form-admin-settings')?.addEventListener('submit', async(e) => {
        e.preventDefault();
        const payload = [
            {key: 'GROQ_API_KEY', value: document.getElementById('admin-groq').value},

            {key: 'GCP_SERVICE_EMAIL', value: document.getElementById('admin-gcp-email').value},
            {key: 'GCP_CREDENTIALS_JSON', value: document.getElementById('admin-gcp-json').value},
            {key: 'MAINTENANCE_MODE', value: document.getElementById('admin-maintenance').checked ? 'true' : 'false'},
            {key: 'RAZORPAY_KEY_ID', value: document.getElementById('admin-rzp-key').value},
            {key: 'RAZORPAY_SECRET', value: document.getElementById('admin-rzp-secret').value},
            {key: 'LANDING_HOW_IT_WORKS_TITLE', value: document.getElementById('admin-how-it-works-title').value},
            {key: 'LANDING_HOW_IT_WORKS_SUBTITLE', value: document.getElementById('admin-how-it-works-subtitle').value}
        ];
        try {
            await api.put('/admin/settings', payload);
            if(window.showToast) showToast("Settings saved", "success");
        } catch(err) { if(window.showToast) showToast(err.message, "error"); }
    });

    // --- Landing Page Content ---
    async function loadLandingContent() {
        try {
            const settings = await api.get('/admin/settings');
            settings.forEach(s => {
                if(s.key === 'LANDING_STEPS') document.getElementById('landing-steps').value = s.value;
                if(s.key === 'LANDING_FAQ') document.getElementById('landing-faq').value = s.value;
                if(s.key === 'LANDING_FOOTER') document.getElementById('landing-footer').value = s.value;
                if(s.key === 'LANDING_REVIEWS') document.getElementById('landing-reviews').value = s.value;
            });
            
            // Populate defaults if empty to help the admin
            if(!document.getElementById('landing-steps').value) {
                document.getElementById('landing-steps').value = JSON.stringify([
                    {step_num: "01", title: "Connect your Google Sheet", description: "Paste your Google Sheet URL. We automatically read your leads instantly without complex setup."},
                    {step_num: "02", title: "Define your templates", description: "Create various email templates for different types of clients or outreach scenarios."},
                    {step_num: "03", title: "AI matches the message", description: "Our AI engine analyzes each lead's notes and automatically selects the most relevant email template."},
                    {step_num: "04", title: "Review & Send", description: "Approve the AI-selected templates and send them. We throttle sending speeds to protect your domain."},
                    {step_num: "05", title: "Track in your Sheet", description: "We log the email status and replies right back into your original Google Sheet."}
                ], null, 2);
            }
            if(!document.getElementById('landing-faq').value) {
                document.getElementById('landing-faq').value = JSON.stringify([
                    {question: "What is Sheetx.io?", answer: "Sheetx.io is an intelligent outreach platform that syncs with Google Sheets and uses AI to match the perfect email template to your leads."},
                    {question: "Is there a free trial?", answer: "Yes, we offer a 14-day free trial on all paid plans so you can test our AI matching engine."},
                    {question: "Do I need to import my leads?", answer: "No importing required! Just paste your Google Sheet URL, and we sync directly with your live data."},
                    {question: "Will this affect my domain reputation?", answer: "We use smart sending features like built-in delays and throttling to ensure your domain reputation stays protected while scaling."},
                    {question: "Can I bring my own email account?", answer: "Yes! You can connect your existing Google accounts securely via the Gmail API to send directly from your own domain."}
                ], null, 2);
            }
            if(!document.getElementById('landing-footer').value) {
                document.getElementById('landing-footer').value = JSON.stringify({
                    "Product": [{name: "Features", url: "#features"}, {name: "Pricing", url: "#pricing"}],
                    "Company": [{name: "About Us", url: "#about"}, {name: "Contact", url: "#contact"}],
                    "Legal": [{name: "Regulations", url: "/regulations"}]
                }, null, 2);
            }
            if(!document.getElementById('landing-reviews').value) {
                document.getElementById('landing-reviews').value = JSON.stringify([
                    {quote: "Sheetx.io transformed our agency outreach. What used to take our SDR team 2 full days now takes under 2 hours.", name: "Amanda Clarke", role: "Head of Growth", initials: "A"},
                    {quote: "The Google Sheets integration is seamless. Our team loves the timeline view, and configuration errors dropped to zero from day one.", name: "James Rawlinson", role: "Ops Director", initials: "J"},
                    {quote: "We operate across multiple countries. Sheetx.io is the only platform that handles all dynamic tax rules without custom workarounds.", name: "Sarah Mitchell", role: "Finance Manager", initials: "S"}
                ], null, 2);
            }
            
            // Render FAQ Builder UI
            renderFaqBuilder();
        } catch(e) {}
    }

    // --- FAQ Builder Logic ---
    function renderFaqBuilder() {
        const container = document.getElementById('faq-builder-container');
        if(!container) return;
        let faqs = [];
        try { faqs = JSON.parse(document.getElementById('landing-faq').value); } catch(e){}
        
        container.innerHTML = '';
        faqs.forEach((faq, idx) => {
            container.insertAdjacentHTML('beforeend', `
                <div class="faq-row bg-base-100 p-4 rounded-xl border border-white/5 relative group">
                    <button type="button" onclick="removeFaqRow(this)" class="btn btn-sm btn-circle btn-ghost text-red-400 absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">✕</button>
                    <div class="form-control mb-2 pr-8">
                        <label class="label pt-0"><span class="label-text text-gray-400 text-xs">Question</span></label>
                        <input type="text" class="faq-q input input-sm input-bordered bg-base-200 border-white/10" value="${faq.question.replace(/"/g, '&quot;')}">
                    </div>
                    <div class="form-control">
                        <label class="label pt-0"><span class="label-text text-gray-400 text-xs">Answer</span></label>
                        <textarea class="faq-a textarea textarea-sm textarea-bordered bg-base-200 border-white/10 h-16">${faq.answer}</textarea>
                    </div>
                </div>
            `);
        });
    }

    window.addFaqRow = () => {
        let faqs = [];
        try { faqs = JSON.parse(document.getElementById('landing-faq').value || "[]"); } catch(e){}
        faqs.push({question: "", answer: ""});
        document.getElementById('landing-faq').value = JSON.stringify(faqs);
        renderFaqBuilder();
    };

    window.removeFaqRow = (btn) => {
        btn.closest('.faq-row').remove();
    };

    document.getElementById('form-admin-landing')?.addEventListener('submit', async(e) => {
        e.preventDefault();
        
        // Serialize FAQ Builder back to JSON
        const faqRows = document.querySelectorAll('.faq-row');
        const newFaqs = [];
        faqRows.forEach(row => {
            const q = row.querySelector('.faq-q').value.trim();
            const a = row.querySelector('.faq-a').value.trim();
            if(q || a) newFaqs.push({question: q, answer: a});
        });
        document.getElementById('landing-faq').value = JSON.stringify(newFaqs);

        // Validate JSON before saving
        try {
            JSON.parse(document.getElementById('landing-steps').value);
            JSON.parse(document.getElementById('landing-faq').value);
            JSON.parse(document.getElementById('landing-footer').value);
            JSON.parse(document.getElementById('landing-reviews').value);
        } catch(err) {
            if(window.showToast) showToast("Invalid JSON format. Please check your syntax.", "error");
            return;
        }

        const payload = [
            {key: 'LANDING_STEPS', value: document.getElementById('landing-steps').value},
            {key: 'LANDING_FAQ', value: document.getElementById('landing-faq').value},
            {key: 'LANDING_FOOTER', value: document.getElementById('landing-footer').value},
            {key: 'LANDING_REVIEWS', value: document.getElementById('landing-reviews').value}
        ];
        try {
            await api.put('/admin/settings', payload);
            if(window.showToast) showToast("Landing page content saved", "success");
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
        document.getElementById('policy-modal')?.showModal();
    };

    window.editPolicy = async (slug) => {
        try {
            const p = await api.get(`/public/policies/${slug}`);
            const el = (id) => document.getElementById(id);
            if(el('pol-slug')) { el('pol-slug').value = p.slug; el('pol-slug').readOnly = true; }
            if(el('pol-title')) el('pol-title').value = p.title;
            if(el('pol-icon')) el('pol-icon').value = p.icon || '';
            if(el('pol-desc')) el('pol-desc').value = p.description || '';
            if(el('pol-content')) el('pol-content').value = p.content_html || '';
            document.getElementById('policy-modal')?.showModal();
        } catch(e){}
    };

    document.getElementById('form-policy')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        // Backend endpoint: POST /api/admin/policies expects { title, slug, content_html, is_active }
        const payload = {
            slug: document.getElementById('pol-slug').value,
            title: document.getElementById('pol-title').value,
            icon: document.getElementById('pol-icon') ? document.getElementById('pol-icon').value : '',
            description: document.getElementById('pol-desc') ? document.getElementById('pol-desc').value : '',
            content_html: document.getElementById('pol-content').value,
            is_active: true
        };
        try {
            await api.post('/admin/policies', payload);
            document.getElementById('policy-modal')?.close();
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
            document.getElementById('notif-modal')?.close();
            document.getElementById('form-notif')?.reset();
        } catch(err) { if(window.showToast) showToast(err.message, "error"); }
    });

    // --- Promo Codes ---
    async function loadPromoCodes() {
        try {
            const codes = await api.get('/admin/promo-codes');
            const list = document.getElementById('promo-list');
            if(!list) return;
            list.innerHTML = '';
            
            if(!codes || codes.length === 0) {
                list.innerHTML = '<tr><td colspan="6" class="p-4 text-center text-gray-500">No promo codes found.</td></tr>';
                return;
            }
            
            codes.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="p-4 font-bold font-mono text-white">${c.code}</td>
                    <td class="p-4 text-secondary">${c.discount_pct}%</td>
                    <td class="p-4">${c.uses}</td>
                    <td class="p-4">${c.max_uses}</td>
                    <td class="p-4">
                        ${c.is_active ? '<span class="badge badge-success badge-sm">Active</span>' : '<span class="badge badge-error badge-sm">Inactive</span>'}
                    </td>
                    <td class="p-4 text-right">
                        <button class="btn btn-xs btn-error text-white" onclick="deletePromoCode('${c.id}')">Delete</button>
                    </td>
                `;
                list.appendChild(tr);
            });
        } catch(e) {
            console.error(e);
        }
    }

    document.getElementById('form-promo')?.addEventListener('submit', async(e) => {
        e.preventDefault();
        const payload = {
            code: document.getElementById('promo-code-val').value.toUpperCase(),
            discount_pct: parseInt(document.getElementById('promo-discount').value) || 0,
            max_uses: parseInt(document.getElementById('promo-max-uses').value) || 100,
            is_active: true
        };
        try {
            await api.post('/admin/promo-codes', payload);
            if(window.showToast) showToast('Promo code created', 'success');
            document.getElementById('modal-promo')?.close();
            document.getElementById('form-promo').reset();
            loadPromoCodes();
        } catch(err) {
            if(window.showToast) showToast(err.message, 'error');
        }
    });

    window.deletePromoCode = async (id) => {
        if(!confirm("Delete this promo code?")) return;
        try {
            await api.delete('/admin/promo-codes/' + id);
            if(window.showToast) showToast('Deleted', 'success');
            loadPromoCodes();
        } catch(e) {}
    };

    router.on('promo', loadPromoCodes);

    window.uploadLogo = async function() {
        const fileInput = document.getElementById('admin-logo-upload');
        if(!fileInput) return;
        
        if (!fileInput.files || fileInput.files.length === 0) {
            fileInput.click();
            fileInput.onchange = () => {
                if (fileInput.files.length > 0) window.uploadLogo();
            };
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/admin/settings/logo', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${api.getToken()}`
                },
                body: formData
            });
            const data = await res.json();
            if (data.status === 'success') {
                if(window.showToast) showToast('Site logo updated!', 'success');
                const img = document.getElementById('admin-current-logo');
                if(img) {
                    img.src = '/api/logo?v=' + new Date().getTime();
                    img.classList.remove('hidden');
                }
                fileInput.value = '';
            } else {
                alert('Upload failed: ' + JSON.stringify(data));
            }
        } catch (e) {
            alert('Error uploading logo: ' + e);
        }
    };

});
