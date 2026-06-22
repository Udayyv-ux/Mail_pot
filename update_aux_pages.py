import os
import re

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root, "frontend")
    
    # Files to process
    files_to_fix_footer = ["help.html", "docs.html", "legal.html", "policy.html", "status.html", "feedback.html"]
    
    for fname in files_to_fix_footer:
        path = os.path.join(frontend_dir, fname)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()
            
            # Fix footer copyright mojibake
            html = re.sub(r'([A-Za-z\x80-\xFF]+)\s+2026\s+Sheetx\.io', r'&copy; 2026 Sheetx.io', html)
            
            # Specific page updates
            if fname == "help.html":
                # Replace the generic grid with an FAQ
                grid_pattern = r'<div class="max-w-4xl mx-auto px-6 grid grid-cols-1 md:grid-cols-2 gap-6 mb-16">.*?</div>\s*<div class="max-w-2xl'
                faq_content = """<div class="max-w-4xl mx-auto px-6 mb-16">
            <h2 class="text-2xl font-bold mb-8 text-center">Frequently Asked Questions</h2>
            <div class="space-y-4">
                <div class="collapse collapse-plus bg-base-200/50 border border-white/5">
                  <input type="radio" name="my-accordion-3" checked="checked" /> 
                  <div class="collapse-title text-xl font-medium">How does the native Gmail integration work?</div>
                  <div class="collapse-content text-gray-400">
                    <p>Instead of relying on clunky third-party SMTP servers, Sheetx.io connects directly to your Google Workspace via OAuth. This ensures your automated emails are sent directly from your actual Gmail outbox, maximizing deliverability and bypassing generic spam filters.</p>
                  </div>
                </div>
                <div class="collapse collapse-plus bg-base-200/50 border border-white/5">
                  <input type="radio" name="my-accordion-3" /> 
                  <div class="collapse-title text-xl font-medium">How should I format my Google Sheet?</div>
                  <div class="collapse-content text-gray-400">
                    <p>Your Google Sheet must contain a column named exactly <b>"Email"</b> (case-insensitive). Optional columns like "Name", "Company", or "Notes" can be used as variables in your email templates (e.g., Hi {Name}).</p>
                  </div>
                </div>
                <div class="collapse collapse-plus bg-base-200/50 border border-white/5">
                  <input type="radio" name="my-accordion-3" /> 
                  <div class="collapse-title text-xl font-medium">What happens if I hit my daily email limit?</div>
                  <div class="collapse-content text-gray-400">
                    <p>Google Workspace limits accounts to 2,000 outgoing emails per day. To protect your domain reputation, Sheetx.io will automatically pause sending when you reach your plan limit or the Google API limit, and resume the next day.</p>
                  </div>
                </div>
            </div>
        </div>
        <div class="max-w-2xl"""
                html = re.sub(grid_pattern, faq_content, html, flags=re.DOTALL)
                
            elif fname == "docs.html":
                # Add real documentation
                placeholder_pattern = r'<p class="text-gray-400 mb-12 text-lg">Integrate Sheetx\.io seamlessly into your workflows\.</p>\s*<div class="bg-base-200/50.*?</div>'
                docs_content = """<p class="text-gray-400 mb-12 text-lg">Integrate Sheetx.io seamlessly into your workflows.</p>
            <div class="bg-base-200/50 border border-white/5 rounded-xl p-8 mb-8">
                <h3 class="text-2xl font-bold mb-4">1. Setting up your Google Sheet</h3>
                <p class="text-gray-400 mb-4">Sheetx reads directly from your Google Sheets. To get started, create a new sheet and ensure the first row contains your headers. <b>"Email"</b> is the only strictly required header. Make sure your sharing settings are set to "Anyone with the link can view".</p>
                <div class="mockup-code bg-dark/80 mb-6">
                    <pre data-prefix="1"><code>Email, Name, Company, Notes</code></pre>
                    <pre data-prefix="2"><code>john@example.com, John Doe, Acme Corp, Mentioned they need automation</code></pre>
                </div>
            </div>
            <div class="bg-base-200/50 border border-white/5 rounded-xl p-8">
                <h3 class="text-2xl font-bold mb-4">2. Spintax & AI Variables</h3>
                <p class="text-gray-400 mb-4">Our engine supports deep personalization. Enclose variables in curly braces to map them directly from your sheet headers. You can also use Spintax to randomize greetings.</p>
                <div class="mockup-code bg-dark/80 text-sm">
                    <pre data-prefix=">"><code>{Hi|Hello|Hey} {Name},</code></pre>
                    <pre data-prefix=">"><code>I saw that {Company} is scaling rapidly.</code></pre>
                </div>
            </div>"""
                html = re.sub(placeholder_pattern, docs_content, html, flags=re.DOTALL)
                
            elif fname == "status.html":
                # Update system status services
                services_pattern = r'<div class="space-y-4">.*?</div>\s*</div>\s*</main>'
                status_content = """<div class="space-y-4">
                <div class="flex justify-between items-center bg-base-200/50 border border-white/5 p-4 rounded-xl">
                    <div class="flex items-center gap-3">
                        <div class="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
                        <span class="font-bold">Google Workspace OAuth Gateway</span>
                    </div>
                    <span class="text-green-500 text-sm">Operational</span>
                </div>
                <div class="flex justify-between items-center bg-base-200/50 border border-white/5 p-4 rounded-xl">
                    <div class="flex items-center gap-3">
                        <div class="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
                        <span class="font-bold">Autonomous Scheduling Engine</span>
                    </div>
                    <span class="text-green-500 text-sm">Operational</span>
                </div>
                <div class="flex justify-between items-center bg-base-200/50 border border-white/5 p-4 rounded-xl">
                    <div class="flex items-center gap-3">
                        <div class="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
                        <span class="font-bold">Client Dashboard UI</span>
                    </div>
                    <span class="text-green-500 text-sm">Operational</span>
                </div>
                <div class="flex justify-between items-center bg-base-200/50 border border-white/5 p-4 rounded-xl">
                    <div class="flex items-center gap-3">
                        <div class="w-3 h-3 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></div>
                        <span class="font-bold">AI Template Matching</span>
                    </div>
                    <span class="text-green-500 text-sm">Operational</span>
                </div>
            </div>
        </div>
    </main>"""
                html = re.sub(services_pattern, status_content, html, flags=re.DOTALL)
                
            elif fname == "feedback.html":
                # Link feedback form to demo API endpoint conceptually
                html = html.replace('id="feedback-form"', 'id="feedback-form" action="/api/public/demo-request" method="POST"')

            with open(path, "w", encoding="utf-8") as f:
                f.write(html)

if __name__ == "__main__":
    main()
