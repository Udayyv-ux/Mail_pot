import re

api_js_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\js\api.js"
with open(api_js_path, "r", encoding="utf-8") as f:
    api_js = f.read()

new_loader_logic = """
    loaderTimeout: null,
    activeRequests: 0,

    showLoader() {
        this.activeRequests++;
        if (this.activeRequests === 1) {
            this.loaderTimeout = setTimeout(() => {
                const loader = document.getElementById('global-loader');
                if (loader && this.activeRequests > 0) {
                    loader.classList.remove('hidden');
                    setTimeout(() => loader.classList.remove('opacity-0'), 10);
                }
            }, 300); // 300ms debounce
        }
    },

    hideLoader() {
        this.activeRequests--;
        if (this.activeRequests <= 0) {
            this.activeRequests = 0;
            if (this.loaderTimeout) {
                clearTimeout(this.loaderTimeout);
                this.loaderTimeout = null;
            }
            const loader = document.getElementById('global-loader');
            if (loader) {
                loader.classList.add('opacity-0');
                setTimeout(() => loader.classList.add('hidden'), 300);
            }
        }
    },
"""

# Replace old loader logic
old_loader_regex = re.compile(r"    showLoader\(\) \{.*?    \},.*?    hideLoader\(\) \{.*?    \},", re.DOTALL)
if "loaderTimeout:" not in api_js:
    api_js = old_loader_regex.sub(new_loader_logic.strip(), api_js)
    with open(api_js_path, "w", encoding="utf-8") as f:
        f.write(api_js)
    print("Updated api.js loader debounce.")

client_app_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\js\client-app.js"
with open(client_app_path, "r", encoding="utf-8") as f:
    client_app = f.read()

old_load_dashboard = """    async function loadDashboard(isBackground = false) {
        try {
            const data = await api.get('/client/dashboard', { background: isBackground });
            const el = (id) => document.getElementById(id);

            if (el('dash-emails-sent')) el('dash-emails-sent').textContent = data.emails_sent_today || 0;
            if (el('dash-emails-limit')) el('dash-emails-limit').textContent = data.daily_limit || 0;
            if (el('dash-total')) el('dash-total').textContent = data.total_emails_sent || 0;
            if (el('dash-failed')) el('dash-failed').textContent = data.total_emails_failed || 0;
            
            
            // Gamified Onboarding
            try {
                const templatesReq = await api.get('/client/templates', { background: isBackground });"""

new_load_dashboard = """    async function loadDashboard(isBackground = false) {
        try {
            // Fetch concurrently for 2x faster load times
            const [data, templatesReq] = await Promise.all([
                api.get('/client/dashboard', { background: isBackground }),
                api.get('/client/templates', { background: isBackground }).catch(() => [])
            ]);
            
            const el = (id) => document.getElementById(id);

            if (el('dash-emails-sent')) el('dash-emails-sent').textContent = data.emails_sent_today || 0;
            if (el('dash-emails-limit')) el('dash-emails-limit').textContent = data.daily_limit || 0;
            if (el('dash-total')) el('dash-total').textContent = data.total_emails_sent || 0;
            if (el('dash-failed')) el('dash-failed').textContent = data.total_emails_failed || 0;
            
            // Gamified Onboarding
            try {"""

if "Promise.all" not in client_app:
    client_app = client_app.replace(old_load_dashboard, new_load_dashboard)
    with open(client_app_path, "w", encoding="utf-8") as f:
        f.write(client_app)
    print("Updated client-app.js concurrent fetching.")

