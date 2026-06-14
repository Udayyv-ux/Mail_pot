document.addEventListener('DOMContentLoaded', async () => {
    auth.checkUrlTokens();
    const user = await auth.getCurrentUser();
    if (!user) {
        window.location.href = '/';
        return;
    }

    // Router
    const router = {
        routes: {},
        on(path, callback) { this.routes[path] = callback; },
        async navigate(path) {
            document.querySelectorAll('.page-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            
            const pageId = `page-${path}`;
            const pageEl = document.getElementById(pageId);
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

    // --- Dashboard ---
    let emailChart = null;

    async function loadDashboard() {
        try {
            const data = await api.get('/client/dashboard');
            document.getElementById('dash-templates').textContent = data.active_templates;
            
            const limits = await api.get('/client/limits');
            document.getElementById('dash-emails-sent').textContent = limits.emails_sent_today;
            document.getElementById('dash-emails-limit').textContent = limits.daily_limit;
            
            let percentage = (limits.emails_sent_today / limits.daily_limit) * 100;
            if(percentage > 100) percentage = 100;
            document.getElementById('dash-meter').style.width = percentage + '%';
            
            // Total sent (We will calculate this from logs or just leave 0 for now if backend doesn't provide it)
            // Assuming backend adds total_sent_all_time later
            document.getElementById('dash-total').textContent = limits.total_sent || 0;

            // Load Chart Data
            loadAnalyticsChart();
        } catch(e) {
            components.showToast("Failed to load dashboard stats", "error");
        }
    }

    async function loadAnalyticsChart() {
        try {
            const stats = await api.get('/client/analytics/chart');
            const ctx = document.getElementById('email-chart').getContext('2d');
            
            if(emailChart) emailChart.destroy();
            
            emailChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: stats.labels || ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Emails Sent',
                        data: stats.data || [0,0,0,0,0,0,0],
                        borderColor: '#4f46e5',
                        backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#ec4899',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8', stepSize: 1 } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        } catch(e) {
            console.log("Analytics error:", e);
        }
    }

    // --- Templates ---
    async function loadTemplates() {
        try {
            const templates = await api.get('/client/templates');
            const tbody = document.getElementById('template-list');
            tbody.innerHTML = '';
            
            if(templates.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-500">No templates found.</td></tr>';
                return;
            }
            
            templates.forEach(t => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="p-4 font-bold text-white">${t.project_name}</td>
                    <td class="p-4 text-gray-300 truncate max-w-xs">${t.subject}</td>
                    <td class="p-4">
                        <span class="px-3 py-1 rounded-full text-xs font-bold ${t.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}">
                            ${t.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td class="p-4 text-right space-x-2">
                        <button class="text-primary hover:text-indigo-400 font-semibold text-sm" onclick="editTemplate('${t.id}')">Edit</button>
                        <button class="text-red-400 hover:text-red-300 font-semibold text-sm" onclick="deleteTemplate('${t.id}')">Delete</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch(e) {
            components.showToast("Failed to load templates", "error");
        }
    }

    document.getElementById('btn-new-template').addEventListener('click', () => {
        document.getElementById('tmpl-id').value = '';
        document.getElementById('tmpl-project').value = '';
        document.getElementById('tmpl-subject').value = '';
        document.getElementById('tmpl-body').value = '<p>Hi {first_name},</p>\n\n<p>Your message here</p>';
        document.getElementById('tmpl-banner-url').value = '';
        document.getElementById('tmpl-banner-preview').classList.add('hidden');
        document.getElementById('template-editor-modal').classList.add('active');
        updatePreview();
    });

    document.getElementById('tmpl-body').addEventListener('input', updatePreview);
    function updatePreview() {
        const html = document.getElementById('tmpl-body').value;
        const bannerUrl = document.getElementById('tmpl-banner-url').value;
        const doc = document.getElementById('tmpl-preview').contentWindow.document;
        doc.open();
        
        let finalHtml = html;
        if(bannerUrl) {
            finalHtml = `<img src="${bannerUrl}" style="max-width:100%; border-radius:8px; margin-bottom:20px;"/><br/>` + finalHtml;
        }
        doc.write(finalHtml);
        doc.close();
    }

    // Banner Upload Handler
    document.getElementById('tmpl-banner').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if(!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            // Need to use raw fetch because our api.js assumes JSON
            const token = auth.getToken();
            const res = await fetch('/api/client/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });
            const data = await res.json();
            if(!res.ok) throw new Error(data.detail || "Upload failed");
            
            document.getElementById('tmpl-banner-url').value = data.url;
            const preview = document.getElementById('tmpl-banner-preview');
            preview.querySelector('img').src = data.url;
            preview.classList.remove('hidden');
            updatePreview();
            components.showToast("Banner uploaded!", "success");
        } catch(err) {
            components.showToast(err.message, "error");
        }
    });

    document.getElementById('btn-save-template').addEventListener('click', async () => {
        const id = document.getElementById('tmpl-id').value;
        const project = document.getElementById('tmpl-project').value;
        const subject = document.getElementById('tmpl-subject').value;
        const body = document.getElementById('tmpl-body').value;
        const banner_url = document.getElementById('tmpl-banner-url').value;
        
        const payload = { project_name: project, subject, body_html: body, banner_url };
        
        try {
            if(id) {
                await api.put(`/client/templates/${id}`, payload);
            } else {
                await api.post(`/client/templates`, payload);
            }
            document.getElementById('template-editor-modal').classList.remove('active');
            components.showToast("Template saved!", "success");
            loadTemplates();
        } catch(e) {
            components.showToast(e.message, "error");
        }
    });

    window.editTemplate = async (id) => {
        try {
            const templates = await api.get('/client/templates');
            const t = templates.find(x => x.id === id);
            if(!t) return;
            
            document.getElementById('tmpl-id').value = t.id;
            document.getElementById('tmpl-project').value = t.project_name;
            document.getElementById('tmpl-subject').value = t.subject;
            document.getElementById('tmpl-body').value = t.body_html;
            document.getElementById('tmpl-banner-url').value = t.banner_url || "";
            
            if(t.banner_url) {
                const preview = document.getElementById('tmpl-banner-preview');
                preview.querySelector('img').src = t.banner_url;
                preview.classList.remove('hidden');
            } else {
                document.getElementById('tmpl-banner-preview').classList.add('hidden');
            }
            
            document.getElementById('template-editor-modal').classList.add('active');
            updatePreview();
        } catch(e) {}
    };

    window.deleteTemplate = async (id) => {
        if(!confirm("Delete this template?")) return;
        try { await api.delete(`/client/templates/${id}`); loadTemplates(); } catch(e){}
    };

    // --- Billing ---
    async function loadBilling() {
        try {
            const currentPlan = await api.get('/client/billing/current-plan');
            document.getElementById('billing-current-plan').textContent = currentPlan.name;
            document.getElementById('billing-current-limit').textContent = `${currentPlan.daily_limit} / day`;
            
            const plans = await api.get('/public/plans');
            const container = document.getElementById('billing-plan-list');
            container.innerHTML = '';
            
            plans.forEach(plan => {
                if(plan.id === currentPlan.id) return;
                let features = [];
                try { features = JSON.parse(plan.features_json); } catch(e){}
                
                const card = document.createElement('div');
                card.className = 'glass p-6 rounded-2xl border border-white/10 hover:border-primary/50 transition-colors flex flex-col';
                let featuresHtml = features.map(f => `<li class="text-sm text-gray-300 flex items-center gap-2"><svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>${f}</li>`).join('');
                
                card.innerHTML = `
                    <h4 class="text-lg font-bold mb-2">${plan.name}</h4>
                    <div class="mb-4"><span class="text-3xl font-extrabold">$${plan.price_monthly}</span><span class="text-gray-400 text-sm">/mo</span></div>
                    <ul class="space-y-2 mb-6 flex-1">${featuresHtml}</ul>
                    <button class="w-full bg-white text-dark hover:bg-gray-200 font-bold py-2 rounded-lg transition-colors" onclick="upgradePlan('${plan.id}', '${plan.name}', ${plan.price_monthly})">Upgrade Now</button>
                `;
                container.appendChild(card);
            });
        } catch(e) {
            components.showToast("Failed to load billing", "error");
        }
    }

    window.upgradePlan = async (planId, planName, amount) => {
        try {
            components.showToast(`Initiating upgrade to ${planName}...`, "info");
            const order = await api.post('/payments/create-order', { plan_id: planId });
            
            const options = {
                "key": order.razorpay_key_id,
                "amount": amount * 100,
                "currency": "USD",
                "name": "LeadFlow.ai",
                "description": `Upgrade to ${planName}`,
                "order_id": order.id,
                "handler": async function (response) {
                    try {
                        await api.post('/payments/verify', {
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature,
                            plan_id: planId
                        });
                        components.showToast("Payment successful! Plan upgraded.", "success");
                        loadBilling();
                    } catch(e) {
                        components.showToast("Payment verification failed", "error");
                    }
                },
                "theme": { "color": "#4f46e5" }
            };
            const rzp = new Razorpay(options);
            rzp.open();
        } catch(e) {
            components.showToast(e.message, "error");
        }
    };

    // --- Settings ---
    async function loadSettings() {
        try {
            const data = await api.get('/client/settings');
            document.getElementById('set-company').value = data.company_name || '';
            document.getElementById('set-smtp-email').value = data.smtp_email || '';
            document.getElementById('set-sheet').value = data.google_sheet_url || '';
            
            const adminSettings = await api.get('/public/settings');
            document.getElementById('service-account-email').textContent = adminSettings.service_account_email || 'Not configured by admin';
        } catch(e) {
            components.showToast("Failed to load settings", "error");
        }
    }

    document.getElementById('form-profile').addEventListener('submit', async(e) => {
        e.preventDefault();
        const payload = {
            company_name: document.getElementById('set-company').value,
            smtp_email: document.getElementById('set-smtp-email').value,
            smtp_password: document.getElementById('set-smtp-pass').value || undefined,
            groq_api_key: document.getElementById('set-groq').value || undefined
        };
        try {
            await api.put('/client/profile', payload);
            components.showToast("Profile settings saved", "success");
            document.getElementById('set-smtp-pass').value = '';
            document.getElementById('set-groq').value = '';
        } catch(err) {
            components.showToast(err.message, "error");
        }
    });

    document.getElementById('form-sheet').addEventListener('submit', async(e) => {
        e.preventDefault();
        try {
            await api.put('/client/sheet', { url: document.getElementById('set-sheet').value });
            components.showToast("Google Sheet linked successfully", "success");
        } catch(err) {
            components.showToast(err.message, "error");
        }
    });

    // --- Send Blast Form ---
    document.getElementById('form-send-blast').addEventListener('submit', async(e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        const oldText = btn.textContent;
        btn.textContent = "Processing..."; btn.disabled = true;
        
        const batchSize = document.getElementById('blast-batch').value;
        try {
            await api.post('/client/blast', { batch_size: parseInt(batchSize) });
            components.showToast("Blast triggered successfully! Emails are sending in the background.", "success");
            document.getElementById('blast-modal').classList.remove('active');
            setTimeout(loadDashboard, 2000); // Reload stats shortly after
        } catch(err) {
            components.showToast(err.message, "error");
        } finally {
            btn.textContent = oldText; btn.disabled = false;
        }
    });

    // Logout
    document.getElementById('btn-logout').addEventListener('click', () => {
        auth.logout();
        window.location.href = '/';
    });

    // Notifications Fetching
    async function fetchNotifications() {
        try {
            const notifs = await api.get('/client/notifications');
            const badge = document.getElementById('notification-badge');
            const list = document.getElementById('notification-list');
            list.innerHTML = '';
            
            if(notifs.length > 0) {
                badge.classList.remove('hidden');
                badge.textContent = notifs.length;
                notifs.forEach(n => {
                    const div = document.createElement('div');
                    div.className = 'p-3 border-b border-white/10 text-sm text-gray-300';
                    div.innerHTML = `<span class="block text-white font-bold mb-1">${components.formatDate(n.created_at)}</span>${n.message}`;
                    list.appendChild(div);
                });
            } else {
                badge.classList.add('hidden');
                list.innerHTML = '<div class="p-4 text-center text-gray-500">No new announcements.</div>';
            }
        } catch(e) {}
    }

    document.getElementById('notification-bell').addEventListener('click', () => {
        document.getElementById('notification-dropdown').classList.toggle('hidden');
    });

    // Initialize Routes
    router.on('dashboard', loadDashboard);
    router.on('templates', loadTemplates);
    router.on('billing', loadBilling);
    // router.on('campaigns') removed completely
    router.on('settings', loadSettings);
    
    // Set display email
    let payload = null;
    try {
        const token = api.getToken();
        if(token) payload = JSON.parse(atob(token.split('.')[1]));
    } catch(e) {}
    
    if(payload) document.getElementById('client-email-display').textContent = payload.sub;

    router.init();
    fetchNotifications();
});
