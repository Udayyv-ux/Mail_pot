document.addEventListener('DOMContentLoaded', async () => {
    // Parse OAuth tokens from URL first, then check auth
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
            if (!path) return;
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

    // --- Dashboard ---
    let emailChart = null;

    async function loadDashboard() {
        try {
            const data = await api.get('/client/dashboard');
            // data has: emails_sent_today, daily_limit, active_campaigns, total_campaigns, company_name
            const el = (id) => document.getElementById(id);
            
            if(el('dash-emails-sent')) el('dash-emails-sent').textContent = data.emails_sent_today || 0;
            if(el('dash-emails-limit')) el('dash-emails-limit').textContent = data.daily_limit || 0;
            if(el('dash-total')) el('dash-total').textContent = data.emails_sent_today || 0;
            if(el('dash-templates')) el('dash-templates').textContent = '-';
            
            let percentage = data.daily_limit > 0 ? (data.emails_sent_today / data.daily_limit) * 100 : 0;
            if(percentage > 100) percentage = 100;
            if(el('dash-meter')) el('dash-meter').style.width = percentage + '%';

            // Load Chart Data
            loadAnalyticsChart();
        } catch(e) {
            console.error("Dashboard load error:", e);
            if(window.showToast) showToast("Failed to load dashboard stats", "error");
        }
    }

    async function loadAnalyticsChart() {
        try {
            const stats = await api.get('/client/analytics/chart');
            const canvas = document.getElementById('email-chart');
            if(!canvas) return;
            const ctx = canvas.getContext('2d');
            
            if(emailChart) emailChart.destroy();
            
            emailChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: stats.labels || [],
                    datasets: [{
                        label: 'Emails Sent',
                        data: stats.data || [],
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
            console.log("Analytics chart error:", e);
        }
    }

    // --- Templates ---
    async function loadTemplates() {
        try {
            const templates = await api.get('/client/templates');
            const tbody = document.getElementById('template-list');
            if(!tbody) return;
            tbody.innerHTML = '';
            
            if(templates.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-500">No templates found. Create your first one!</td></tr>';
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
            if(window.showToast) showToast("Failed to load templates", "error");
        }
    }

    document.getElementById('btn-new-template')?.addEventListener('click', () => {
        document.getElementById('tmpl-id').value = '';
        document.getElementById('tmpl-project').value = '';
        document.getElementById('tmpl-subject').value = '';
        document.getElementById('tmpl-body').value = '<p>Hi {first_name},</p>\n\n<p>Your message here</p>';
        document.getElementById('tmpl-banner-url').value = '';
        document.getElementById('tmpl-banner-preview').classList.add('hidden');
        document.getElementById('template-editor-modal').classList.add('active');
        updatePreview();
    });

    document.getElementById('tmpl-body')?.addEventListener('input', updatePreview);
    function updatePreview() {
        const bodyEl = document.getElementById('tmpl-body');
        const bannerUrlEl = document.getElementById('tmpl-banner-url');
        const previewEl = document.getElementById('tmpl-preview');
        if(!bodyEl || !previewEl) return;
        
        const html = bodyEl.value;
        const bannerUrl = bannerUrlEl ? bannerUrlEl.value : '';
        const doc = previewEl.contentWindow.document;
        doc.open();
        
        let finalHtml = html;
        if(bannerUrl) {
            finalHtml = `<img src="${bannerUrl}" style="max-width:100%; border-radius:8px; margin-bottom:20px;"/><br/>` + finalHtml;
        }
        doc.write(finalHtml);
        doc.close();
    }

    // Banner Upload Handler
    document.getElementById('tmpl-banner')?.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if(!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const token = api.getToken();
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
            if(window.showToast) showToast("Banner uploaded!", "success");
        } catch(err) {
            if(window.showToast) showToast(err.message, "error");
        }
    });

    document.getElementById('btn-save-template')?.addEventListener('click', async () => {
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
            if(window.showToast) showToast("Template saved!", "success");
            loadTemplates();
        } catch(e) {
            if(window.showToast) showToast(e.message, "error");
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
            // Get profile to find current plan info
            const profile = await api.get('/client/profile');
            const el = (id) => document.getElementById(id);
            
            if(el('billing-current-plan')) el('billing-current-plan').textContent = profile.plan_name || 'Free Plan';
            if(el('billing-current-limit')) el('billing-current-limit').textContent = (profile.daily_limit || 50) + ' / day';
            
            const plans = await api.get('/public/plans');
            const container = document.getElementById('billing-plan-list');
            if(!container) return;
            container.innerHTML = '';
            
            plans.forEach(plan => {
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
            console.error("Billing load error:", e);
        }
    }

    window.upgradePlan = async (planId, planName, amount) => {
        try {
            if(window.showToast) showToast(`Initiating upgrade to ${planName}...`, "info");
            const order = await api.post('/payments/create-order', { plan_id: planId });
            
            const options = {
                "key": order.razorpay_key_id,
                "amount": amount * 100,
                "currency": "INR",
                "name": "LeadFlow.ai",
                "description": `Upgrade to ${planName}`,
                "order_id": order.order_id,
                "handler": async function (response) {
                    try {
                        await api.post('/payments/verify', {
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature
                        });
                        if(window.showToast) showToast("Payment successful! Plan upgraded.", "success");
                        loadBilling();
                    } catch(e) {
                        if(window.showToast) showToast("Payment verification failed", "error");
                    }
                },
                "theme": { "color": "#4f46e5" }
            };
            const rzp = new Razorpay(options);
            rzp.open();
        } catch(e) {
            if(window.showToast) showToast(e.message, "error");
        }
    };

    // --- Settings ---
    async function loadSettings() {
        try {
            // Uses /client/profile endpoint which exists in the backend
            const data = await api.get('/client/profile');
            const el = (id) => document.getElementById(id);
            
            if(el('set-company')) el('set-company').value = data.company_name || '';
            if(el('set-smtp-email')) el('set-smtp-email').value = data.smtp_email || '';
            if(el('set-sheet')) el('set-sheet').value = data.google_sheet_id || '';
            if(el('service-account-email')) el('service-account-email').textContent = data.service_account_email || 'Not configured by admin';
            if(el('groq-status')) el('groq-status').textContent = data.has_groq_key ? 'Custom Key Active ✓' : 'Using System Default';
        } catch(e) {
            console.error("Settings load error:", e);
        }
    }

    // --- Profile & Settings Form ---
    document.getElementById('form-profile')?.addEventListener('submit', async(e) => {
        e.preventDefault();
        const payload = {
            company_name: document.getElementById('set-company').value,
            target_columns: document.getElementById('set-target-cols').value,
            status_column: document.getElementById('set-status-col').value
        };
        try {
            await api.put('/client/profile', payload);
            if(window.showToast) showToast("Profile updated", "success");
        } catch(err) {
            if(window.showToast) showToast(err.message, "error");
        }
    });

    document.getElementById('form-sheet')?.addEventListener('submit', async(e) => {
        e.preventDefault();
        try {
            await api.put('/client/sheet', { sheet_url_or_id: document.getElementById('set-sheet').value });
            if(window.showToast) showToast("Google Sheet linked successfully", "success");
        } catch(err) {
            if(window.showToast) showToast(err.message, "error");
        }
    });



    // Logout
    document.getElementById('btn-logout')?.addEventListener('click', () => {
        auth.logout();
    });

    // Notifications
    async function fetchNotifications() {
        try {
            const notifs = await api.get('/client/notifications');
            const badge = document.getElementById('notification-badge');
            const list = document.getElementById('notification-list');
            if(!badge || !list) return;
            list.innerHTML = '';
            
            if(notifs.length > 0) {
                badge.classList.remove('hidden');
                badge.textContent = notifs.length;
                notifs.forEach(n => {
                    const div = document.createElement('div');
                    div.className = 'p-3 border-b border-white/10 text-sm text-gray-300';
                    div.innerHTML = `<span class="block text-white font-bold mb-1">${new Date(n.created_at).toLocaleString()}</span>${n.message}`;
                    list.appendChild(div);
                });
            } else {
                badge.classList.add('hidden');
                list.innerHTML = '<div class="p-4 text-center text-gray-500">No new announcements.</div>';
            }
        } catch(e) {}
    }

    document.getElementById('notification-bell')?.addEventListener('click', () => {
        document.getElementById('notification-dropdown')?.classList.toggle('hidden');
    });

    // Initialize Routes
    router.on('dashboard', loadDashboard);
    router.on('templates', loadTemplates);
    router.on('billing', loadBilling);
    router.on('settings', loadSettings);
    
    // Set display email from user object
    const emailDisplay = document.getElementById('client-email-display');
    if(emailDisplay) emailDisplay.textContent = user.email || '';
    
    // Set user name
    const nameDisplay = document.getElementById('client-name-display');
    if(nameDisplay) nameDisplay.textContent = user.name || '';

    router.init();
    fetchNotifications();
});
