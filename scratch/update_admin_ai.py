import os

# 1. Update backend/routers/admin.py
admin_py_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\backend\routers\admin.py"
with open(admin_py_path, 'r', encoding='utf-8') as f:
    admin_py = f.read()

if "has_ai_templates: bool = False" not in admin_py:
    admin_py = admin_py.replace(
        "    features_json: str",
        "    features_json: str\n    has_ai_templates: bool = False"
    )
    with open(admin_py_path, 'w', encoding='utf-8') as f:
        f.write(admin_py)
    print("Updated admin.py")

# 2. Update frontend/admin/index.html
admin_html_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\admin\index.html"
with open(admin_html_path, 'r', encoding='utf-8') as f:
    admin_html = f.read()

if 'id="plan-has-ai"' not in admin_html:
    checkbox_html = """
                <div class="form-control mb-4 bg-base-300/50 p-4 rounded-xl border border-white/5">
                    <label class="label cursor-pointer justify-start gap-4">
                        <input type="checkbox" id="plan-has-ai" class="toggle toggle-secondary">
                        <div>
                            <span class="label-text font-medium text-white block">Enable AI Templates</span>
                            <span class="label-text-alt text-gray-400">Allows users on this plan to auto-generate templates using Groq AI.</span>
                        </div>
                    </label>
                </div>
"""
    admin_html = admin_html.replace(
        '<button type="submit" class="btn btn-secondary text-white w-full mt-4">Save Plan</button>',
        checkbox_html + '                <button type="submit" class="btn btn-secondary text-white w-full mt-4">Save Plan</button>'
    )
    with open(admin_html_path, 'w', encoding='utf-8') as f:
        f.write(admin_html)
    print("Updated admin/index.html")

# 3. Update frontend/js/admin-app.js
admin_js_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\js\admin-app.js"
with open(admin_js_path, 'r', encoding='utf-8') as f:
    admin_js = f.read()

if "has_ai_templates" not in admin_js:
    # Adding payload field
    admin_js = admin_js.replace(
        "features_json: document.getElementById('plan-features').value",
        "features_json: document.getElementById('plan-features').value,\n                has_ai_templates: document.getElementById('plan-has-ai').checked"
    )
    # Updating Edit modal population
    admin_js = admin_js.replace(
        "document.getElementById('plan-features').value = plan.features_json || '';",
        "document.getElementById('plan-features').value = plan.features_json || '';\n    document.getElementById('plan-has-ai').checked = plan.has_ai_templates || false;"
    )
    # Resetting form
    admin_js = admin_js.replace(
        "document.getElementById('plan-features').value = '';",
        "document.getElementById('plan-features').value = '';\n    document.getElementById('plan-has-ai').checked = false;"
    )
    with open(admin_js_path, 'w', encoding='utf-8') as f:
        f.write(admin_js)
    print("Updated admin-app.js")
