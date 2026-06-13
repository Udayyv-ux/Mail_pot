/**
 * Admin Portal App
 */
document.addEventListener('DOMContentLoaded', async () => {
    const user = await auth.requireAuth('admin');
    if (!user) return;

    document.getElementById('btn-logout').addEventListener('click', () => auth.logout());

    // Routing
    router.on('dashboard', loadDashboard);
    router.on('clients', loadClients);
    router.on('leads', loadLeads);
    router.on('plans', loadPlans);
    router.on('settings', loadSettings);
    router.init();

    // Dashboard
    async function loadDashboard() {
        try {
            const data = await api.get('/admin/dashboard');
            document.getElementById('dash-clients').textContent = data.total_clients;
            document.getElementById('dash-campaigns').textContent = data.active_campaigns;
            document.getElementById('dash-emails').textContent = data.total_emails_sent;
            document.getElementById('dash-revenue').textContent = `₹${data.total_revenue}`;
            
            const engine = await api.get('/admin/engine/status');
            const engStatus = document.getElementById('engine-status');
            if (engine.is_running) {
                engStatus.innerHTML = components.createBadge('Running Active', 'success');
                document.getElementById('btn-pause-engine').style.display = 'inline-block';
                document.getElementById('btn-resume-engine').style.display = 'none';
            } else {
                engStatus.innerHTML = components.createBadge('Paused globally', 'warning');
                document.getElementById('btn-pause-engine').style.display = 'none';
                document.getElementById('btn-resume-engine').style.display = 'inline-block';
            }
        } catch(e) { components.showToast("Error loading dashboard", "error"); }
    }

    document.getElementById('btn-pause-engine').onclick = async () => {
        try { await api.post('/admin/engine/pause'); loadDashboard(); components.showToast("Engine stopped", "info"); } catch(e){}
    };
    document.getElementById('btn-resume-engine').onclick = async () => {
        try { await api.post('/admin/engine/resume'); loadDashboard(); components.showToast("Engine started", "success"); } catch(e){}
    };

    // Clients
    async function loadClients() {
        try {
            const clients = await api.get('/admin/clients');
            const tbody = document.getElementById('client-list');
            tbody.innerHTML = '';
            clients.forEach(c => {
                tbody.innerHTML += `
                    <tr>
                        <td>${c.id.substring(0,8)}...</td>
                        <td><strong>${c.company_name}</strong></td>
                        <td>${c.emails_sent_today}</td>
                        <td>${components.createBadge(c.status, c.status==='active'?'success':'secondary')}</td>
                        <td><button class="btn btn-secondary btn-sm" onclick="resetClient('${c.id}')">Reset Usage</button></td>
                    </tr>
                `;
            });
        } catch(e){}
    }
    window.resetClient = async (id) => {
        if(!confirm("Reset today's usage for this client?")) return;
        try { await api.post(`/admin/clients/${id}/reset-usage`); components.showToast("Reset", "success"); loadClients(); } catch(e){}
    }

    // Demo Leads
    async function loadLeads() {
        try {
            const leads = await api.get('/admin/demo-requests');
            const tbody = document.getElementById('demo-list');
            tbody.innerHTML = '';
            leads.forEach(l => {
                let statusBadge = l.status === 'pending' ? 'warning' : 'success';
                let date = new Date(l.created_at).toLocaleDateString();
                tbody.innerHTML += `
                    <tr>
                        <td>${date}</td>
                        <td><strong>${l.name}</strong></td>
                        <td>${l.email}</td>
                        <td>${l.company || '-'}</td>
                        <td title="${l.message}">${l.message.substring(0, 30)}...</td>
                        <td>${components.createBadge(l.status, statusBadge)}</td>
                    </tr>
                `;
            });
        } catch(e){}
    }

    document.getElementById('form-demo-blast').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('btn-demo-send');
        btn.textContent = 'Sending...';
        btn.disabled = true;

        try {
            const res = await api.post('/admin/demo-requests/send-email', {
                subject: document.getElementById('demo-subject').value,
                body_html: document.getElementById('demo-body').value
            });
            components.showToast(`Outreach complete! Sent ${res.sent_count} emails.`, 'success');
            if (res.sent_count > 0) {
                e.target.reset();
                loadLeads();
            }
        } catch(e) {
            components.showToast(e.message, 'error');
        } finally {
            btn.textContent = 'Launch Outreach';
            btn.disabled = false;
        }
    });

    // Plans
    async function loadPlans() {
        try {
            const plans = await api.get('/admin/plans');
            const tbody = document.getElementById('plan-list');
            tbody.innerHTML = '';
            plans.forEach(p => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${p.name}</strong> ${p.is_featured ? '⭐' : ''}</td>
                        <td>₹${p.price_monthly}</td>
                        <td>${p.email_limit_daily} /day</td>
                        <td><button class="btn btn-danger btn-sm" onclick="deletePlan('${p.id}')">Delete</button></td>
                    </tr>
                `;
            });
        } catch(e){}
    }
    
    document.getElementById('form-plan').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const features = document.getElementById('plan-features').value.split('\n').filter(x=>x.trim());
            await api.post('/admin/plans', {
                name: document.getElementById('plan-name').value,
                description: document.getElementById('plan-desc').value,
                price_monthly: parseFloat(document.getElementById('plan-price-mo').value),
                price_yearly: parseFloat(document.getElementById('plan-price-yr').value),
                email_limit_daily: parseInt(document.getElementById('plan-limit').value),
                features_json: JSON.stringify(features)
            });
            components.showToast("Plan created", "success");
            e.target.reset();
            loadPlans();
        } catch(e) { components.showToast(e.message, "error"); }
    });

    window.deletePlan = async (id) => {
        if(!confirm("Delete this plan?")) return;
        try { await api.delete(`/admin/plans/${id}`); loadPlans(); } catch(e){}
    }

    // Settings
    async function loadSettings() {
        try {
            const settings = await api.get('/admin/settings');
            const tbody = document.getElementById('settings-list');
            tbody.innerHTML = '';
            
            // Group by category
            const grouped = {};
            settings.forEach(s => {
                if(!grouped[s.category]) grouped[s.category] = [];
                grouped[s.category].push(s);
            });
            
            Object.keys(grouped).forEach(cat => {
                tbody.innerHTML += `<tr><td colspan="3" style="background:rgba(255,255,255,0.05)"><strong>${cat.toUpperCase()}</strong></td></tr>`;
                grouped[cat].forEach(s => {
                    tbody.innerHTML += `
                        <tr>
                            <td><code>${s.key}</code><br><small class="text-muted">${s.description}</small></td>
                            <td><input type="text" class="form-control set-val-input" data-key="${s.key}" value='${s.value.replace(/'/g, "&#39;")}' /></td>
                            <td></td>
                        </tr>
                    `;
                });
            });
        } catch(e){}
    }

    document.getElementById('btn-save-settings').addEventListener('click', async () => {
        const inputs = document.querySelectorAll('.set-val-input');
        const updates = Array.from(inputs).map(i => ({ key: i.getAttribute('data-key'), value: i.value }));
        try {
            await api.put('/admin/settings', updates);
            components.showToast("Settings saved globally", "success");
        } catch(e) { components.showToast(e.message, "error"); }
    });
});
