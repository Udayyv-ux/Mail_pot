import re

client_html_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\client\index.html"
with open(client_html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Inject tabs into template editor modal
ai_tabs_html = """
                <!-- Editor Side -->
                <div class="flex-1 flex flex-col p-6 overflow-y-auto border-r border-white/5 relative">
                    <input type="hidden" id="tmpl-id">
                    
                    <!-- Tabs -->
                    <div class="tabs tabs-boxed bg-base-200 mb-6 border border-white/5 p-1 flex">
                        <a class="tab flex-1 tab-active" id="tab-manual" onclick="toggleTemplateMode('manual')">✍️ Write Manually</a>
                        <a class="tab flex-1" id="tab-ai" onclick="toggleTemplateMode('ai')">✨ Generate with AI <span class="badge badge-sm badge-primary ml-2">PRO</span></a>
                    </div>
                    
                    <!-- AI Generator Panel -->
                    <div id="panel-ai" class="hidden mb-6 p-4 rounded-xl bg-base-300 border border-primary/30 relative overflow-hidden">
                        <div class="absolute -right-4 -top-4 opacity-10 blur-xl w-32 h-32 bg-primary rounded-full"></div>
                        <h4 class="font-bold text-white mb-2 relative z-10">AI Template Generator</h4>
                        <p class="text-xs text-gray-400 mb-4 relative z-10">Describe the goal of this email. Our AI will craft a high-converting subject and body instantly.</p>
                        <textarea id="ai-prompt" class="textarea textarea-bordered bg-base-200 border-white/10 focus:border-primary w-full relative z-10" placeholder="e.g. A cold outreach email for my real estate agency offering a free home valuation..."></textarea>
                        <button id="btn-generate-ai" class="btn btn-primary btn-sm mt-3 w-full text-white relative z-10" onclick="generateTemplateAI()">✨ Generate Template</button>
                    </div>
"""
if "<!-- Tabs -->" not in html:
    html = html.replace(
        """                <!-- Editor Side -->\n                <div class="flex-1 flex flex-col p-6 overflow-y-auto border-r border-white/5">\n                    <input type="hidden" id="tmpl-id">""",
        ai_tabs_html
    )

with open(client_html_path, "w", encoding="utf-8") as f:
    f.write(html)
print("Updated client/index.html")

# Update client-app.js
client_js_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\js\client-app.js"
with open(client_js_path, "r", encoding="utf-8") as f:
    js = f.read()

ai_js_logic = """
// --- AI Templates Logic ---
window.toggleTemplateMode = function(mode) {
    const tabManual = document.getElementById('tab-manual');
    const tabAI = document.getElementById('tab-ai');
    const panelAI = document.getElementById('panel-ai');
    
    // Check access
    if (mode === 'ai' && !window.hasAITemplates) {
        alert("Your current plan does not support AI Generated Templates. Please upgrade to unlock this feature.");
        return;
    }
    
    if (mode === 'manual') {
        tabManual.classList.add('tab-active');
        tabAI.classList.remove('tab-active');
        panelAI.classList.add('hidden');
    } else {
        tabAI.classList.add('tab-active');
        tabManual.classList.remove('tab-active');
        panelAI.classList.remove('hidden');
    }
};

window.generateTemplateAI = async function() {
    const prompt = document.getElementById('ai-prompt').value;
    if (!prompt) return;
    
    const btn = document.getElementById('btn-generate-ai');
    const oldText = btn.innerHTML;
    btn.innerHTML = '<span class="loading loading-spinner loading-sm"></span> Generating...';
    btn.disabled = true;
    
    try {
        const res = await api.post('/client/templates/generate', { prompt });
        document.getElementById('tmpl-subject').value = res.subject || '';
        document.getElementById('tmpl-body').value = res.html_body || '';
        updateLivePreview(); // Force live preview update
        
        // Switch back to manual mode so they can edit the generated text
        toggleTemplateMode('manual');
        document.getElementById('ai-prompt').value = '';
    } catch (e) {
        alert("AI Generation failed: " + e.message);
    } finally {
        btn.innerHTML = oldText;
        btn.disabled = false;
    }
};

window.updateLivePreview = function() {
    const htmlBody = document.getElementById('tmpl-body').value;
    const iframe = document.getElementById('tmpl-preview');
    if (iframe) {
        iframe.srcdoc = htmlBody || '<div style="font-family:sans-serif;color:#888;padding:20px;text-align:center;">Live Preview...</div>';
    }
};

// Bind live preview
document.addEventListener('DOMContentLoaded', () => {
    const tmplBody = document.getElementById('tmpl-body');
    if (tmplBody) {
        tmplBody.addEventListener('input', updateLivePreview);
    }
});
"""

if "window.toggleTemplateMode" not in js:
    js += "\n" + ai_js_logic

# Also fetch plan access during dashboard load or profile load
if "window.hasAITemplates = " not in js:
    js = js.replace(
        "const profileData = await api.get('/client/profile');",
        "const profileData = await api.get('/client/profile');\n        window.hasAITemplates = profileData.plan ? profileData.plan.has_ai_templates : false;"
    )

with open(client_js_path, "w", encoding="utf-8") as f:
    f.write(js)
print("Updated client-app.js")
