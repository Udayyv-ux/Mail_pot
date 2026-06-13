/**
 * Client Portal App
 */
document.addEventListener('DOMContentLoaded', async () => {
    const user = await auth.requireAuth('client');
    if (!user) return;

    // --- Logout ---
    document.getElementById('btn-logout').addEventListener('click', () => auth.logout());

    // --- Routing ---
    router.on('dashboard', loadDashboard);
    router.on('campaigns', loadCampaigns);
    router.on('templates', loadTemplates);
    router.on('settings', loadSettings);
    router.init();

    // --- Dashboard ---
    async function loadDashboard() {
        try {
            const data = await api.get('/client/dashboard');
            document.getElementById('dash-emails-sent').textContent = data.emails_sent_today;
            document.getElementById('dash-emails-limit').textContent = `/ ${data.daily_limit}`;
            document.getElementById('dash-campaigns').textContent = data.active_campaigns;
            document.getElementById('dash-total').textContent = data.total_campaigns;
            
            const pct = Math.min(100, (data.emails_sent_today / data.daily_limit) * 100);
            document.getElementById('dash-meter').style.width = `${pct}%`;
            
            if (pct > 90) document.getElementById('dash-meter').style.backgroundColor = 'var(--danger)';
            else if (pct > 70) document.getElementById('dash-meter').style.backgroundColor = 'var(--warning)';
        } catch(e) {
            components.showToast("Failed to load dashboard", "error");
        }
    }

    // --- Settings ---
    async function loadSettings() {
        try {
            const profile = await api.get('/client/profile');
            document.getElementById('set-company').value = profile.company_name || '';
            document.getElementById('set-smtp-email').value = profile.smtp_email || '';
            document.getElementById('set-sheet').value = profile.google_sheet_id || '';
            
            document.getElementById('service-account-email').innerText = profile.service_account_email || 'Not configured by admin';
            
            if (profile.has_groq_key) {
                document.getElementById('groq-status').innerHTML = components.createBadge('Configured', 'success');
            } else {
                document.getElementById('groq-status').innerHTML = components.createBadge('Using System Default', 'warning');
            }
        } catch(e) {
            components.showToast("Failed to load settings", "error");
        }
    }

    document.getElementById('form-profile').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            await api.put('/client/profile', {
                company_name: document.getElementById('set-company').value,
                smtp_email: document.getElementById('set-smtp-email').value,
                smtp_password: document.getElementById('set-smtp-pass').value || undefined,
                groq_api_key: document.getElementById('set-groq').value || undefined
            });
            components.showToast("Profile saved", "success");
            document.getElementById('set-smtp-pass').value = '';
            document.getElementById('set-groq').value = '';
            loadSettings();
        } catch(e) { components.showToast(e.message, "error"); }
    });

    document.getElementById('form-sheet').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            await api.put('/client/sheet', {
                sheet_url_or_id: document.getElementById('set-sheet').value
            });
            components.showToast("Sheet linked successfully", "success");
        } catch(e) { components.showToast(e.message, "error"); }
    });



    // --- Templates ---
    async function loadTemplates() {
        try {
            const tmpls = await api.get('/client/templates');
            const tbody = document.getElementById('template-list');
            tbody.innerHTML = '';
            if (tmpls.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No templates created yet</td></tr>`;
                return;
            }
            tmpls.forEach(t => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${t.project_name}</strong></td>
                        <td>${t.subject}</td>
                        <td>${components.createBadge(t.is_active ? 'Active' : 'Draft', t.is_active ? 'success' : 'secondary')}</td>
                        <td>
                            <button class="btn btn-secondary btn-sm" onclick="editTemplate('${t.id}')">Edit</button>
                            <button class="btn btn-danger btn-sm" onclick="deleteTemplate('${t.id}')">Delete</button>
                        </td>
                    </tr>
                `;
            });
        } catch(e) { components.showToast("Failed to load templates", "error"); }
    }

    document.getElementById('btn-new-template').addEventListener('click', () => {
        document.getElementById('tmpl-id').value = '';
        document.getElementById('tmpl-project').value = '';
        document.getElementById('tmpl-subject').value = '';
        document.getElementById('tmpl-body').value = '';
        document.getElementById('template-editor-modal').classList.add('active');
        updatePreview();
    });

    document.querySelector('.modal-close-tmpl').addEventListener('click', () => {
        document.getElementById('template-editor-modal').classList.remove('active');
    });

    document.getElementById('tmpl-body').addEventListener('input', updatePreview);

    function updatePreview() {
        const html = document.getElementById('tmpl-body').value;
        const iframe = document.getElementById('tmpl-preview');
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        doc.open();
        doc.write(html || '<p style="color:#888; font-family:sans-serif; text-align:center; margin-top:2rem;">Preview will appear here</p>');
        doc.close();
    }

    document.getElementById('btn-save-template').addEventListener('click', async () => {
        const id = document.getElementById('tmpl-id').value;
        const data = {
            project_name: document.getElementById('tmpl-project').value,
            subject: document.getElementById('tmpl-subject').value,
            body_html: document.getElementById('tmpl-body').value
        };
        try {
            if (id) await api.put(`/client/templates/${id}`, data);
            else await api.post(`/client/templates/`, data);
            
            components.showToast("Template saved", "success");
            document.getElementById('template-editor-modal').classList.remove('active');
            loadTemplates();
        } catch(e) { components.showToast(e.message, "error"); }
    });

    // Make template functions global for inline onclick
    window.deleteTemplate = async (id) => {
        if(!confirm("Are you sure?")) return;
        try {
            await api.delete(`/client/templates/${id}`);
            components.showToast("Deleted", "success");
            loadTemplates();
        } catch(e) { components.showToast(e.message, "error"); }
    };

    window.editTemplate = async (id) => {
        try {
            const tmpls = await api.get('/client/templates');
            const tmpl = tmpls.find(t => t.id === id);
            if(tmpl) {
                document.getElementById('tmpl-id').value = tmpl.id;
                document.getElementById('tmpl-project').value = tmpl.project_name;
                document.getElementById('tmpl-subject').value = tmpl.subject;
                document.getElementById('tmpl-body').value = tmpl.body_html;
                document.getElementById('template-editor-modal').classList.add('active');
                updatePreview();
            }
        } catch(e) {}
    };

    // --- Campaigns ---
    async function loadCampaigns() {
        try {
            const camps = await api.get('/client/campaigns');
            const tbody = document.getElementById('campaign-list');
            tbody.innerHTML = '';
            if (camps.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No campaigns started yet</td></tr>`;
                return;
            }
            camps.forEach(c => {
                let statusBadge = '';
                if(c.status==='running') statusBadge = components.createBadge('Running', 'success');
                else if(c.status==='paused') statusBadge = components.createBadge('Paused', 'warning');
                else statusBadge = components.createBadge('Completed', 'secondary');
                
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${c.name}</strong><br><small class="text-muted">${components.formatDate(c.started_at)}</small></td>
                        <td>${statusBadge}</td>
                        <td>${c.emails_sent} / ${c.total_leads}</td>
                        <td>${c.emails_failed}</td>
                        <td>
                            ${c.status === 'running' ? `<button class="btn btn-warning btn-sm" onclick="pauseCampaign('${c.id}')">Pause</button>` : ''}
                            ${c.status === 'paused' ? `<button class="btn btn-success btn-sm" onclick="resumeCampaign('${c.id}')">Resume</button>` : ''}
                            <button class="btn btn-secondary btn-sm" onclick="viewLogs('${c.id}')">Logs</button>
                        </td>
                    </tr>
                `;
            });
        } catch(e) { components.showToast("Failed to load campaigns", "error"); }
    }

    document.getElementById('form-start-campaign').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        btn.textContent = "Starting..."; btn.disabled = true;
        try {
            const res = await api.post('/client/campaigns/start', {
                name: document.getElementById('camp-name').value,
                batch_size: parseInt(document.getElementById('camp-batch').value)
            });
            components.showToast(`Started! Queued ${res.emails_queued} emails.`, "success");
            document.getElementById('camp-name').value = '';
            loadCampaigns();
            router.navigate('campaigns');
        } catch(e) { 
            components.showToast(e.message, "error"); 
        } finally {
            btn.textContent = "Start Campaign"; btn.disabled = false;
        }
    });

    window.pauseCampaign = async (id) => {
        try { await api.post(`/client/campaigns/${id}/pause`); loadCampaigns(); components.showToast("Paused", "info"); } catch(e){}
    };
    window.resumeCampaign = async (id) => {
        try { await api.post(`/client/campaigns/${id}/resume`); loadCampaigns(); components.showToast("Resumed", "success"); } catch(e){}
    };
    window.viewLogs = async (id) => {
        try {
            const logs = await api.get(`/client/campaigns/${id}/logs`);
            let html = '<table class="table" style="width:100%;text-align:left;"><tr><th>Email</th><th>Status</th><th>Template</th><th>Time</th></tr>';
            logs.forEach(l => {
                html += `<tr>
                    <td>${l.recipient_email}</td>
                    <td>${l.status==='sent' ? '✅ Sent' : '❌ Failed'}</td>
                    <td>${l.template_used || '-'}</td>
                    <td>${components.formatDate(l.sent_at)}</td>
                </tr>`;
            });
            html += '</table>';
            components.showModal("Campaign Logs", html);
        } catch(e){}
    };
});
