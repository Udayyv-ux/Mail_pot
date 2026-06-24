import os

def replace_in_file(path, old, new):
    if not os.path.exists(path): return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if old in content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.replace(old, new))
        print(f"Updated {path}")

# Update marketing texts
replace_in_file(r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\index.html", "14-day", "5-day")
replace_in_file(r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\js\landing.js", "14-day", "5-day")
replace_in_file(r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\js\admin-app.js", "14-day", "5-day")

# Add lockout banner to client/index.html
client_html_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\client\index.html"
with open(client_html_path, "r", encoding="utf-8") as f:
    content = f.read()

banner_html = """
            <!-- Mobile Topbar -->
            <header class="h-16 border-b border-white/5 flex justify-between items-center px-4 md:px-8 bg-base-200 shadow-sm shrink-0 lg:hidden">
                <div class="flex items-center gap-3">
                    <label for="portal-drawer" class="btn btn-square btn-ghost text-white">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-5 h-5 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                    </label>
                    <img src="/api/logo?v=3" alt="Sheetx Logo" class="h-6 object-contain">
                </div>
            </header>
            
            <div id="trial-lockout-banner" class="hidden bg-error/90 text-error-content p-4 text-center z-50 shrink-0 text-sm md:text-base font-medium">
                Your 5-day free trial has expired. You cannot perform tasks. Please <a href="#billing" onclick="document.querySelector('[data-route=billing]').click(); return false;" class="font-bold underline hover:text-white">upgrade your plan</a> to continue.
            </div>
"""
if 'id="trial-lockout-banner"' not in content:
    content = content.replace(
        """
            <!-- Mobile Topbar -->
            <header class="h-16 border-b border-white/5 flex justify-between items-center px-4 md:px-8 bg-base-200 shadow-sm shrink-0 lg:hidden">
                <div class="flex items-center gap-3">
                    <label for="portal-drawer" class="btn btn-square btn-ghost text-white">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="inline-block w-5 h-5 stroke-current"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path></svg>
                    </label>
                    <img src="/api/logo?v=3" alt="Sheetx Logo" class="h-6 object-contain">
                </div>
            </header>""",
        banner_html
    )
    with open(client_html_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added banner to client/index.html")

# Update client-app.js to check trial_ends_at
client_js_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\js\client-app.js"
with open(client_js_path, "r", encoding="utf-8") as f:
    content = f.read()

# I need to add logic where API requests fail, OR where profile is loaded.
# Let's add it to the init() function or the fetch dashboard function.
# Wait, fetch profile is done in `loadProfile` but `loadDashboard` runs first on init?
# Let's check `API` interceptor or just do it when `data` is loaded in dashboard.
# In `client-app.js`, we can just fetch profile globally on init to determine lock state.
pass
