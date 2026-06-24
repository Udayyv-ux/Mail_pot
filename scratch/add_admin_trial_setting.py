import re
import os

file_path_html = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\admin\index.html"
with open(file_path_html, "r", encoding="utf-8") as f:
    content_html = f.read()

# Add to index.html under "Global Settings"
trial_input_html = """
                            <div class="form-control">
                                <label class="label"><span class="label-text text-gray-400 font-medium">Default Trial Duration (Days)</span></label>
                                <input type="number" id="admin-trial-days" class="input input-bordered bg-base-300 border-white/10" placeholder="5" value="5">
                                <label class="label"><span class="label-text-alt text-gray-500">Number of days before trial users are locked out.</span></label>
                            </div>
"""
if 'id="admin-trial-days"' not in content_html:
    content_html = content_html.replace(
        '<div class="divider border-white/5">Landing Page Settings</div>',
        trial_input_html + '                            <div class="divider border-white/5">Landing Page Settings</div>'
    )
    with open(file_path_html, "w", encoding="utf-8") as f:
        f.write(content_html)
    print("Admin HTML updated.")

file_path_js = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\js\admin-app.js"
with open(file_path_js, "r", encoding="utf-8") as f:
    content_js = f.read()

# Load trial_days
if "document.getElementById('admin-trial-days').value = data.settings.trial_days" not in content_js:
    content_js = content_js.replace(
        "document.getElementById('admin-maintenance').checked = data.settings.maintenance_mode === 'true';",
        "document.getElementById('admin-maintenance').checked = data.settings.maintenance_mode === 'true';\n                if (data.settings.trial_days) document.getElementById('admin-trial-days').value = data.settings.trial_days;"
    )

# Save trial_days
if "trial_days: document.getElementById('admin-trial-days').value" not in content_js:
    content_js = content_js.replace(
        "maintenance_mode: document.getElementById('admin-maintenance').checked ? 'true' : 'false',",
        "maintenance_mode: document.getElementById('admin-maintenance').checked ? 'true' : 'false',\n                    trial_days: document.getElementById('admin-trial-days').value || '5',"
    )

with open(file_path_js, "w", encoding="utf-8") as f:
    f.write(content_js)
print("Admin JS updated.")
