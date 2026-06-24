document.addEventListener('DOMContentLoaded', async () => {
    // Parse OAuth tokens from URL first, then check auth
    auth.checkUrlTokens();
    const user = await auth.getCurrentUser();
    if (!user) {
        window.location.href = '/';
        return;
    }

    // Impersonation handling
    if (localStorage.getItem('admin_token')) {
        const banner = document.getElementById('impersonation-banner');
        if (banner) {
            banner.classList.remove('hidden');
        }
    }

    window.endImpersonation = () => {
        const adminToken = localStorage.getItem('admin_token');
        if (adminToken) {
            localStorage.setItem('access_token', adminToken);
            localStorage.removeItem('admin_token');
            window.location.href = '/admin';
        }
    };

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  ROUTER â€” handles sidebar tab navigation
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  DASHBOARD
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let emailChart = null;

    async function loadDashboard() {
        try {
            const data = await api.get('/client/dashboard');
            const el = (id) => document.getElementById(id);

            if (el('dash-emails-sent')) el('dash-emails-sent').textContent = data.emails_sent_today || 0;
            if (el('dash-emails-limit')) el('dash-emails-limit').textContent = data.daily_limit || 0;
            if (el('dash-total')) el('dash-total').textContent = data.total_emails_sent || 0;
            if (el('dash-failed')) el('dash-failed').textContent = data.total_emails_failed || 0;
            
            const recentList = el('recent-activity-list');
            if (recentList && data.recent_activity) {
                if (data.recent_activity.length === 0) {
                    recentList.innerHTML = '<div class="text-center text-gray-400 mt-10">No recent activity</div>';
                } else {
                    recentList.innerHTML = data.recent_activity.map(a => {
                        const isSent = a.status === 'sent';
                        const colorClass = isSent ? 'text-success' : (a.status === 'failed' ? 'text-error' : 'text-warning');
                        const icon = isSent ? 'âœ“' : (a.status === 'failed' ? 'âœ—' : 'âŸ³');
                        const dateStr = a.sent_at ? new Date(a.sent_at).toLocaleString() : 'Just now';
                        const errMsg = a.error_message ? `<div class="text-xs text-error/80 mt-1 truncate" title="${a.error_message}">₹{a.error_message}</div>` : '';
                        
                        return `
                        <div class="bg-base-300 rounded-lg p-3 border border-white/5 flex items-start gap-3">
                            <div class="mt-0.5 ${colorClass} font-bold">₹{icon}</div>
                            <div class="flex-1 min-w-0">
                                <div class="font-medium text-sm truncate" title="${a.recipient_email}">₹{a.recipient_email}</div>
                                <div class="text-xs text-gray-400">₹{dateStr}</div>
                                ${errMsg}
                            </div>
                            <div class="text-xs font-semibold capitalize ${colorClass}">₹{a.status}</div>
                        </div>
                        `;
                    }).join('');
                }
            }

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

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  TEMPLATES
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async function loadTemplates() {
        try {
            const templates = await api.get('/client/templates');
            const tbody = document.getElementById('template-list');
            if (!tbody) return;
            tbody.innerHTML = '';

            if (templates.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-400">No templates found. Create your first one!</td></tr>';
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

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  CAMPAIGNS
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async function loadCampaigns() {
        try {
            var campaigns = await api.get('/client/campaigns');
            var tbody = document.getElementById('campaign-list');
            if (!tbody) return;
            tbody.innerHTML = '';

            if (campaigns.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-400">No campaigns yet. Click "+ New Campaign" to get started!</td></tr>';
                return;
            }

            campaigns.forEach(function (c) {
                var tr = document.createElement('tr');
                var followUpText = (c.follow_up_days && c.follow_up_days > 0) ? ('Wait ' + c.follow_up_days + ' days') : 'Disabled';
                
                let statusHtml = '';
                if (!c.is_active) {
                    statusHtml = '<span class="badge badge-warning badge-sm">Paused</span>';
                } else if (c.last_error) {
                    statusHtml = `<div class="tooltip tooltip-error cursor-help" data-tip="${c.last_error.replace(/"/g, '&quot;')}"><span class="badge badge-error badge-sm">Error</span></div>`;
                } else {
                    statusHtml = '<span class="badge badge-success badge-sm">Running</span>';
                }
                
                let runText = c.last_run_at ? `<div class="text-xs text-gray-400 mt-1">Last run: ${new Date(c.last_run_at).toLocaleString()}</div>` : '';

                tr.innerHTML =
                    '<td class="p-4 font-bold text-white">' + c.name + '</td>' +
                    '<td class="p-4 text-gray-300 truncate max-w-xs font-mono text-xs">' + c.google_sheet_id + '</td>' +
                    '<td class="p-4 text-gray-400 text-sm">' + followUpText + '</td>' +
                    '<td class="p-4">' + statusHtml + runText + '</td>' +
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
            follow_up_template_id: document.getElementById('camp-followup-template').value || null,
            max_emails_per_hour: parseInt(document.getElementById('camp-throttle-rate').value) || 50,
            send_hours_start: parseInt(document.getElementById('camp-throttle-start').value) || 9,
            send_hours_end: parseInt(document.getElementById('camp-throttle-end').value) || 17,
            review_mode: document.getElementById('camp-review-mode').checked
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

    window.loadQueue = async () => {
        try {
            var items = await api.get('/client/queue');
            var tbody = document.getElementById('queue-list');
            if (tbody) {
                tbody.innerHTML = items.map(q => `
                    <tr>
                        <td class="p-4">
                            <div class="font-medium">₹{q.recipient_name || 'N/A'}</div>
                            <div class="text-xs text-gray-400">₹{q.recipient_email}</div>
                        </td>
                        <td class="p-4">₹{q.campaign_name}</td>
                        <td class="p-4">₹{q.template_name}</td>
                        <td class="p-4 text-right">
                            <button class="btn btn-xs btn-success text-white mr-2" onclick="approveQueue('${q.id}')">Approve</button>
                            <button class="btn btn-xs btn-error text-white" onclick="rejectQueue('${q.id}')">Reject</button>
                        </td>
                    </tr>
                `).join('');
                if (items.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="p-4 text-center text-gray-400">No emails pending review.</td></tr>';
                }
                
                var badge = document.getElementById('queue-badge');
                if (badge) {
                    badge.textContent = items.length;
                    if (items.length > 0) badge.classList.remove('hidden');
                    else badge.classList.add('hidden');
                }
            }
        } catch (e) {
            console.error(e);
        }
    };

    window.approveQueue = async (id) => {
        try {
            await api.post('/client/queue/' + id + '/approve');
            if (window.showToast) showToast('Approved!', 'success');
            loadQueue();
        } catch(e) { if (window.showToast) showToast(e.message, 'error'); }
    };

    window.rejectQueue = async (id) => {
        try {
            await api.post('/client/queue/' + id + '/reject');
            if (window.showToast) showToast('Rejected!', 'success');
            loadQueue();
        } catch(e) { if (window.showToast) showToast(e.message, 'error'); }
    };

    window.loadInbox = async () => {
        try {
            var items = await api.get('/client/inbox');
            var tbody = document.getElementById('inbox-list');
            if (tbody) {
                tbody.innerHTML = items.map(m => `
                    <tr>
                        <td class="p-4 font-medium text-white">₹{m.from.replace(/<.*>/, '')}</td>
                        <td class="p-4">
                            <div class="font-medium text-white">₹{m.subject}</div>
                            <div class="text-xs text-gray-400 truncate max-w-xs">₹{m.snippet}</div>
                        </td>
                        <td class="p-4 text-xs text-gray-400 whitespace-nowrap">₹{new Date(m.date).toLocaleString()}</td>
                    </tr>
                `).join('');
                if (items.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="3" class="p-4 text-center text-gray-400">No recent messages in Inbox.</td></tr>';
                }
            }
        } catch (e) {
            console.error(e);
        }
    };

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  BILLING
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        cachedPlans.forEach(function (plan, index) {
            var features = [];
            try { features = JSON.parse(plan.features_json); } catch (e) {}

            var isPopular = (index === 1); // Middle plan roughly
            var cardBorder = isPopular ? 'border-primary' : 'border-white/10';
            var btnStyle = isPopular ? 'bg-primary text-white hover:bg-primary/80 border-none shadow-[0_0_15px_rgba(var(--p),0.5)]' : 'bg-white text-dark hover:bg-gray-200 border-none';

            var card = document.createElement('div');
            card.className = `glass p-6 rounded-2xl border ${cardBorder} hover:border-primary/50 transition-colors flex flex-col relative`;
            
            var popularBadge = isPopular ? '<div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg">Most Popular</div>' : '';

            var featuresHtml = features.map(function (f) {
                return '<li class="text-sm text-gray-300 flex items-center gap-2"><svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>' + f + '</li>';
            }).join('');

            let displayPrice = plan.price_monthly;
            let totalBilled = '<div class="text-xs text-gray-400 font-medium mb-4">Billed monthly</div>';
            
            if (currentBillingCycle === 'half_yearly') {
                let totalAmount = Math.round((plan.price_monthly * 6) * 0.85);
                displayPrice = Math.round(totalAmount / 6);
                totalBilled = '<div class="text-xs text-green-400 font-medium mb-4">Billed ₹' + totalAmount + ' every 6 months</div>';
            } else if (currentBillingCycle === 'yearly') {
                let totalAmount = Math.round((plan.price_monthly * 12) * 0.75);
                displayPrice = Math.round(totalAmount / 12);
                totalBilled = '<div class="text-xs text-green-400 font-medium mb-4">Billed ₹' + totalAmount + ' yearly</div>';
            }

            card.innerHTML = popularBadge + 
                '<h4 class="text-lg font-bold mb-2">' + plan.name + '</h4>' +
                '<div><span class="text-4xl font-extrabold">₹' + displayPrice + '</span><span class="text-gray-400 text-sm">/mo</span></div>' +
                totalBilled +
                '<ul class="space-y-2 mb-6 flex-1">' + featuresHtml + '</ul>' +
                '<button class="w-full ' + btnStyle + ' font-bold py-3 rounded-xl transition-colors" onclick="upgradePlan(\'' + plan.id + '\', \'' + plan.name + '\')">Upgrade Now</button>';
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

    let activePromoCode = null;

    window.applyPromoCode = async () => {
        const input = document.getElementById('promo-code-input').value.trim();
        if (!input) return;
        // Just store the code locally for now; we'll validate it on create-order.
        activePromoCode = input;
        if (window.showToast) showToast('Promo code applied. Discount will be applied at checkout.', 'success');
    };

    window.upgradePlan = async (planId, planName) => {
        try {
            if (window.showToast) showToast('Initiating upgrade to ' + planName + '...', 'info');
            
            const reqBody = { plan_id: planId, billing_cycle: currentBillingCycle };
            if (activePromoCode) reqBody.promo_code = activePromoCode;
            
            var order = await api.post('/payments/create-order', reqBody);

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

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  SETTINGS
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  NOTIFICATIONS
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                list.innerHTML = '<div class="p-4 text-center text-gray-400">No new announcements.</div>';
            }
        } catch (e) {}
    }

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  LOGOUT
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    document.getElementById('btn-logout')?.addEventListener('click', () => {
        auth.logout();
    });

    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    //  REGISTER ROUTES & BOOT
    // â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    router.on('dashboard', loadDashboard);
    router.on('templates', loadTemplates);
    router.on('campaigns', loadCampaigns);
    router.on('queue', loadQueue);
    router.on('inbox', loadInbox);
    router.on('billing', loadBilling);
    router.on('settings', loadSettings);
    router.on('instructions', () => {}); // No data loading required

    // Display user email
    var emailDisplay = document.getElementById('client-email-display');
    if (emailDisplay) emailDisplay.textContent = user.email || '';

    // Start the app
    router.init();
    fetchNotifications();
});
