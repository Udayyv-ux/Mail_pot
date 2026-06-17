document.addEventListener('DOMContentLoaded', async () => {
    // Parse OAuth tokens from URL first, then check auth
    auth.checkUrlTokens();
    const user = await auth.getCurrentUser();
    if (!user) {
        window.location.href = '/';
        return;
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  ROUTER — handles sidebar tab navigation
    // ─────────────────────────────────────────────────────────────────────────
    const router = {
        routes: {},
        currentRoute: null,

        on(path, callback) {
            this.routes[path] = callback;
        },

        async navigate(path) {
            if (!path) return;
            // Allow re-navigating to the same route (force refresh)
            this.currentRoute = path;
            window.location.hash = path;

            // Hide all pages, deactivate all nav items
            document.querySelectorAll('.page-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

            // Show target page
            const pageEl = document.getElementById('page-' + path);
            if (pageEl) pageEl.classList.add('active');

            // Highlight nav item
            const navEl = document.querySelector('.nav-item[data-route="' + path + '"]');
            if (navEl) navEl.classList.add('active');

            // Update topbar title
            const titleEl = document.getElementById('topbar-title');
            if (titleEl) titleEl.textContent = path.charAt(0).toUpperCase() + path.slice(1);

            // Fire route callback
            if (this.routes[path]) {
                try {
                    await this.routes[path]();
                } catch (err) {
                    console.error('Route callback error (' + path + '):', err);
                }
            }
        },

        init() {
            // Bind all sidebar nav clicks
            document.querySelectorAll('.nav-item').forEach(el => {
                el.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.navigate(el.dataset.route);
                });
            });

            // Handle browser back/forward
            window.addEventListener('hashchange', () => {
                const path = window.location.hash.replace('#', '') || 'dashboard';
                this.navigate(path);
            });

            // Navigate to the initial page
            const initialPath = window.location.hash.replace('#', '') || 'dashboard';
            this.currentRoute = null; // reset so navigate fires
            this.navigate(initialPath);
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  DASHBOARD
    // ─────────────────────────────────────────────────────────────────────────
    let emailChart = null;

    async function loadDashboard() {
        try {
            const data = await api.get('/client/dashboard');
            const el = (id) => document.getElementById(id);

            if (el('dash-emails-sent')) el('dash-emails-sent').textContent = data.emails_sent_today || 0;
            if (el('dash-emails-limit')) el('dash-emails-limit').textContent = data.daily_limit || 0;
            if (el('dash-total')) el('dash-total').textContent = data.emails_sent_today || 0;

            // Repurpose the "templates" stat card as "Active Campaigns"
            if (el('dash-templates')) {
                el('dash-templates').textContent = data.active_campaigns || 0;
                var statTitle = el('dash-templates').parentElement.querySelector('.stat-title');
                if (statTitle) statTitle.textContent = 'Active Campaigns';
                var statDesc = el('dash-templates').parentElement.querySelector('.stat-desc');
                if (statDesc) statDesc.textContent = (data.total_campaigns || 0) + ' Total Campaigns';
            }

            var percentage = data.daily_limit > 0 ? (data.emails_sent_today / data.daily_limit) * 100 : 0;
            if (percentage > 100) percentage = 100;
            if (el('dash-meter')) el('dash-meter').value = percentage;

            loadAnalyticsChart();
        } catch (e) {
            console.error('Dashboard load error:', e);
            if (window.showToast) showToast('Failed to load dashboard stats', 'error');
        }
    }

    async function loadAnalyticsChart() {
        try {
            const stats = await api.get('/client/analytics/chart');
            const canvas = document.getElementById('email-chart');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');

            if (emailChart) emailChart.destroy();

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
        } catch (e) {
            console.log('Analytics chart error:', e);
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  TEMPLATES
    // ─────────────────────────────────────────────────────────────────────────
    async function loadTemplates() {
        try {
            const templates = await api.get('/client/templates');
            const tbody = document.getElementById('template-list');
            if (!tbody) return;
            tbody.innerHTML = '';

            if (templates.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-500">No templates found. Create your first one!</td></tr>';
                return;
            }

            templates.forEach(t => {
                const tr = document.createElement('tr');
                tr.innerHTML =
                    '<td class="p-4 font-bold text-white">' + t.project_name + '</td>' +
                    '<td class="p-4 text-gray-300 truncate max-w-xs">' + t.subject + '</td>' +
                    '<td class="p-4">' +
                        '<span class="px-3 py-1 rounded-full text-xs font-bold ' + (t.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400') + '">' +
                            (t.is_active ? 'Active' : 'Inactive') +
                        '</span>' +
                    '</td>' +
                    '<td class="p-4 text-right space-x-2">' +
                        '<button class="text-primary hover:text-indigo-400 font-semibold text-sm" onclick="editTemplate(\'' + t.id + '\')">Edit</button>' +
                        '<button class="text-red-400 hover:text-red-300 font-semibold text-sm" onclick="deleteTemplate(\'' + t.id + '\')">Delete</button>' +
                    '</td>';
                tbody.appendChild(tr);
            });
        } catch (e) {
            if (window.showToast) showToast('Failed to load templates', 'error');
        }
    }

    document.getElementById('btn-new-template')?.addEventListener('click', () => {
        document.getElementById('tmpl-id').value = '';
        document.getElementById('tmpl-project').value = '';
        document.getElementById('tmpl-subject').value = '';
        document.getElementById('tmpl-body').value = '<p>Hi {first_name},</p>\n\n<p>Your message here</p>';
        document.getElementById('tmpl-banner-url').value = '';
        document.getElementById('tmpl-banner-preview').classList.add('hidden');
        document.getElementById('template-editor-modal').showModal();
        updatePreview();
    });

    document.getElementById('tmpl-body')?.addEventListener('input', updatePreview);
    function updatePreview() {
        var bodyEl = document.getElementById('tmpl-body');
        var bannerUrlEl = document.getElementById('tmpl-banner-url');
        var previewEl = document.getElementById('tmpl-preview');
        if (!bodyEl || !previewEl) return;

        var html = bodyEl.value;
        var bannerUrl = bannerUrlEl ? bannerUrlEl.value : '';
        var doc = previewEl.contentWindow.document;
        doc.open();

        var finalHtml = html;
        if (bannerUrl) {
            finalHtml = '<img src="' + bannerUrl + '" style="max-width:100%; border-radius:8px; margin-bottom:20px;"/><br/>' + finalHtml;
        }
        doc.write(finalHtml);
        doc.close();
    }

    // Banner Upload Handler
    document.getElementById('tmpl-banner')?.addEventListener('change', async (e) => {
        var file = e.target.files[0];
        if (!file) return;

        var formData = new FormData();
        formData.append('file', file);

        try {
            var token = api.getToken();
            var res = await fetch('/api/client/upload', {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token },
                body: formData
            });
            var data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Upload failed');

            document.getElementById('tmpl-banner-url').value = data.url;
            var preview = document.getElementById('tmpl-banner-preview');
            preview.querySelector('img').src = data.url;
            preview.classList.remove('hidden');
            updatePreview();
            if (window.showToast) showToast('Banner uploaded!', 'success');
        } catch (err) {
            if (window.showToast) showToast(err.message, 'error');
        }
    });

    document.getElementById('btn-save-template')?.addEventListener('click', async () => {
        var id = document.getElementById('tmpl-id').value;
        var project = document.getElementById('tmpl-project').value;
        var subject = document.getElementById('tmpl-subject').value;
        var body = document.getElementById('tmpl-body').value;
        var banner_url = document.getElementById('tmpl-banner-url').value;

        var payload = { project_name: project, subject: subject, body_html: body, banner_url: banner_url };

        try {
            if (id) {
                await api.put('/client/templates/' + id, payload);
            } else {
                await api.post('/client/templates', payload);
            }
            document.getElementById('template-editor-modal').close();
            if (window.showToast) showToast('Template saved!', 'success');
            loadTemplates();
        } catch (e) {
            if (window.showToast) showToast(e.message, 'error');
        }
    });

    window.editTemplate = async (id) => {
        try {
            var templates = await api.get('/client/templates');
            var t = templates.find(x => x.id === id);
            if (!t) return;

            document.getElementById('tmpl-id').value = t.id;
            document.getElementById('tmpl-project').value = t.project_name;
            document.getElementById('tmpl-subject').value = t.subject;
            document.getElementById('tmpl-body').value = t.body_html;
            document.getElementById('tmpl-banner-url').value = t.banner_url || '';

            if (t.banner_url) {
                var preview = document.getElementById('tmpl-banner-preview');
                preview.querySelector('img').src = t.banner_url;
                preview.classList.remove('hidden');
            } else {
                document.getElementById('tmpl-banner-preview').classList.add('hidden');
            }

            document.getElementById('template-editor-modal').showModal();
            updatePreview();
        } catch (e) {}
    };

    window.deleteTemplate = async (id) => {
        if (!confirm('Delete this template?')) return;
        try { await api.delete('/client/templates/' + id); loadTemplates(); } catch (e) {}
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  CAMPAIGNS
    // ─────────────────────────────────────────────────────────────────────────
    async function loadCampaigns() {
        try {
            var campaigns = await api.get('/client/campaigns');
            var tbody = document.getElementById('campaign-list');
            if (!tbody) return;
            tbody.innerHTML = '';

            if (campaigns.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-500">No campaigns yet. Click "+ New Campaign" to get started!</td></tr>';
                return;
            }

            campaigns.forEach(function (c) {
                var tr = document.createElement('tr');
                var followUpText = (c.follow_up_days && c.follow_up_days > 0) ? ('Wait ' + c.follow_up_days + ' days') : 'Disabled';
                tr.innerHTML =
                    '<td class="p-4 font-bold text-white">' + c.name + '</td>' +
                    '<td class="p-4 text-gray-300 truncate max-w-xs font-mono text-xs">' + c.google_sheet_id + '</td>' +
                    '<td class="p-4 text-gray-400 text-sm">' + followUpText + '</td>' +
                    '<td class="p-4 text-right space-x-2">' +
                        '<button class="text-red-400 hover:text-red-300 font-semibold text-sm" onclick="deleteCampaign(\'' + c.id + '\')">Delete</button>' +
                    '</td>';
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('Campaigns load error:', e);
            if (window.showToast) showToast('Failed to load campaigns', 'error');
        }
    }

    document.getElementById('btn-new-campaign')?.addEventListener('click', async () => {
        document.getElementById('camp-name').value = '';
        document.getElementById('camp-sheet').value = '';
        document.getElementById('camp-followup-days').value = '0';

        // Populate follow-up template dropdown from existing templates
        try {
            var templates = await api.get('/client/templates');
            var sel = document.getElementById('camp-followup-template');
            sel.innerHTML = '<option value="">-- None --</option>';
            templates.forEach(function (t) {
                var opt = document.createElement('option');
                opt.value = t.id;
                opt.textContent = t.project_name;
                sel.appendChild(opt);
            });
        } catch (e) {}

        document.getElementById('modal-campaign').showModal();
    });

    document.getElementById('form-campaign')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        var payload = {
            name: document.getElementById('camp-name').value,
            sheet_url_or_id: document.getElementById('camp-sheet').value,
            follow_up_days: parseInt(document.getElementById('camp-followup-days').value) || 0,
            follow_up_template_id: document.getElementById('camp-followup-template').value || null
        };

        try {
            await api.post('/client/campaigns', payload);
            document.getElementById('modal-campaign').close();
            if (window.showToast) showToast('Campaign created!', 'success');
            loadCampaigns();
            loadDashboard();
        } catch (e) {
            if (window.showToast) showToast(e.message || 'Failed to create campaign', 'error');
        }
    });

    window.deleteCampaign = async (id) => {
        if (!confirm('Delete this campaign and all its email logs?')) return;
        try {
            await api.delete('/client/campaigns/' + id);
            loadCampaigns();
            loadDashboard();
            if (window.showToast) showToast('Campaign deleted', 'success');
        } catch (e) {
            if (window.showToast) showToast(e.message, 'error');
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  BILLING
    // ─────────────────────────────────────────────────────────────────────────
    let currentBillingCycle = 'monthly';
    let cachedPlans = [];

    async function loadBilling() {
        try {
            var profile = await api.get('/client/profile');
            var el = (id) => document.getElementById(id);

            if (el('billing-current-plan')) el('billing-current-plan').textContent = profile.plan_name || 'Free Plan';
            if (el('billing-current-limit')) el('billing-current-limit').textContent = (profile.daily_limit || 50) + ' / day';

            cachedPlans = await api.get('/public/plans');
            renderPlans();
            setupBillingToggle();
        } catch (e) {
            console.error('Billing load error:', e);
        }
    }

    function renderPlans() {
        var container = document.getElementById('billing-plan-list');
        if (!container) return;
        container.innerHTML = '';

        cachedPlans.forEach(function (plan) {
            var features = [];
            try { features = JSON.parse(plan.features_json); } catch (e) {}

            var card = document.createElement('div');
            card.className = 'glass p-6 rounded-2xl border border-white/10 hover:border-primary/50 transition-colors flex flex-col';
            var featuresHtml = features.map(function (f) {
                return '<li class="text-sm text-gray-300 flex items-center gap-2"><svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>' + f + '</li>';
            }).join('');

            let displayPrice = plan.price_monthly;
            let totalBilled = '<div class="text-xs text-gray-500 font-medium mb-4">Billed monthly</div>';
            
            if (currentBillingCycle === 'half_yearly') {
                displayPrice = Math.round((plan.price_half_yearly || plan.price_monthly * 6) / 6);
                totalBilled = '<div class="text-xs text-green-400 font-medium mb-4">Billed $' + (plan.price_half_yearly || plan.price_monthly * 6) + ' every 6 months</div>';
            } else if (currentBillingCycle === 'yearly') {
                displayPrice = Math.round((plan.price_yearly || plan.price_monthly * 12) / 12);
                totalBilled = '<div class="text-xs text-green-400 font-medium mb-4">Billed $' + (plan.price_yearly || plan.price_monthly * 12) + ' yearly</div>';
            }

            card.innerHTML =
                '<h4 class="text-lg font-bold mb-2">' + plan.name + '</h4>' +
                '<div><span class="text-4xl font-extrabold">$' + displayPrice + '</span><span class="text-gray-400 text-sm">/mo</span></div>' +
                totalBilled +
                '<ul class="space-y-2 mb-6 flex-1">' + featuresHtml + '</ul>' +
                '<button class="w-full bg-white text-dark hover:bg-gray-200 font-bold py-3 rounded-xl transition-colors" onclick="upgradePlan(\'' + plan.id + '\', \'' + plan.name + '\')">Upgrade Now</button>';
            container.appendChild(card);
        });
    }

    function setupBillingToggle() {
        const toggleContainer = document.getElementById('billing-toggle');
        if (!toggleContainer || toggleContainer.dataset.setup) return;
        toggleContainer.dataset.setup = 'true';
        
        const buttons = toggleContainer.querySelectorAll('button');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                buttons.forEach(b => {
                    b.classList.remove('bg-primary', 'text-white');
                    b.classList.add('text-gray-400');
                });
                btn.classList.add('bg-primary', 'text-white');
                btn.classList.remove('text-gray-400');
                
                currentBillingCycle = btn.dataset.cycle;
                renderPlans();
            });
        });
    }

    window.upgradePlan = async (planId, planName) => {
        try {
            if (window.showToast) showToast('Initiating upgrade to ' + planName + '...', 'info');
            var order = await api.post('/payments/create-order', { plan_id: planId, billing_cycle: currentBillingCycle });

            var options = {
                key: order.razorpay_key_id,
                amount: order.amount,
                currency: 'INR',
                name: 'Sheetx.io',
                description: 'Upgrade to ' + planName,
                order_id: order.order_id,
                handler: async function (response) {
                    try {
                        await api.post('/payments/verify', {
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature
                        });
                        if (window.showToast) showToast('Payment successful! Plan upgraded.', 'success');
                        loadBilling();
                    } catch (e) {
                        if (window.showToast) showToast('Payment verification failed', 'error');
                    }
                },
                theme: { color: '#4f46e5' }
            };
            var rzp = new Razorpay(options);
            rzp.open();
        } catch (e) {
            if (window.showToast) showToast(e.message, 'error');
        }
    };

    // ─────────────────────────────────────────────────────────────────────────
    //  SETTINGS
    // ─────────────────────────────────────────────────────────────────────────
    async function loadSettings() {
        try {
            var data = await api.get('/client/profile');
            var el = (id) => document.getElementById(id);
            if (el('set-company')) el('set-company').value = data.company_name || '';
            if (el('service-account-email')) el('service-account-email').textContent = data.service_account_email || 'Not configured by admin';
        } catch (e) {
            console.error('Settings load error:', e);
        }
    }

    document.getElementById('form-profile')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        var payload = {
            company_name: document.getElementById('set-company').value
        };
        try {
            await api.put('/client/profile', payload);
            if (window.showToast) showToast('Profile updated', 'success');
        } catch (err) {
            if (window.showToast) showToast(err.message, 'error');
        }
    });

    // ─────────────────────────────────────────────────────────────────────────
    //  NOTIFICATIONS
    // ─────────────────────────────────────────────────────────────────────────
    async function fetchNotifications() {
        try {
            var notifs = await api.get('/client/notifications');
            var badge = document.getElementById('notification-badge');
            var list = document.getElementById('notification-list');
            if (!badge || !list) return;
            list.innerHTML = '';

            if (notifs.length > 0) {
                badge.classList.remove('hidden');
                badge.textContent = notifs.length;
                notifs.forEach(function (n) {
                    var div = document.createElement('div');
                    div.className = 'p-3 border-b border-white/10 text-sm text-gray-300';
                    div.innerHTML = '<span class="block text-white font-bold mb-1">' + new Date(n.created_at).toLocaleString() + '</span>' + n.message;
                    list.appendChild(div);
                });
            } else {
                badge.classList.add('hidden');
                list.innerHTML = '<div class="p-4 text-center text-gray-500">No new announcements.</div>';
            }
        } catch (e) {}
    }

    // ─────────────────────────────────────────────────────────────────────────
    //  LOGOUT
    // ─────────────────────────────────────────────────────────────────────────
    document.getElementById('btn-logout')?.addEventListener('click', () => {
        auth.logout();
    });

    // ─────────────────────────────────────────────────────────────────────────
    //  REGISTER ROUTES & BOOT
    // ─────────────────────────────────────────────────────────────────────────
    router.on('dashboard', loadDashboard);
    router.on('templates', loadTemplates);
    router.on('campaigns', loadCampaigns);
    router.on('billing', loadBilling);
    router.on('settings', loadSettings);

    // Display user email
    var emailDisplay = document.getElementById('client-email-display');
    if (emailDisplay) emailDisplay.textContent = user.email || '';

    // Start the app
    router.init();
    fetchNotifications();
});
