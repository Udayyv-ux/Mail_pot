import os
import re

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root, "frontend")
    
    # 1. Update index.html
    index_path = os.path.join(frontend_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    # Currency replacements
    html = html.replace("$15", "₹1,200")
    html = html.replace("$35", "₹2,800")
    html = html.replace("$30/hour", "₹2,500/hour")
    html = html.replace("Cost: $", "Cost: ₹")
    html = html.replace("savings.textContent = '$' +", "savings.textContent = '₹' +")
    html = html.replace("manualCost.textContent = '$' +", "manualCost.textContent = '₹' +")
    
    # Google Meet scheduling HTML injection
    demo_type_original = """<div class="form-control">
                        <label class="label pt-0 pb-1"><span class="label-text text-gray-300">Inquiry Type</span></label>
                        <select id="demo-type" class="select select-bordered w-full bg-dark/50 focus:bg-dark text-white border-white/10 focus:border-primary">
                            <option value="Book a Demo">Book a Demo</option>
                            <option value="Sales Inquiry">Sales Inquiry</option>
                            <option value="Partnership">Partnership</option>
                            <option value="Technical Support">Technical Support</option>
                            <option value="Feedback">Feedback</option>
                        </select>
                    </div>"""
    demo_type_new = """<div class="grid grid-cols-2 gap-4">
                      <div class="form-control">
                          <label class="label pt-0 pb-1"><span class="label-text text-gray-300">Inquiry Type</span></label>
                          <select id="demo-type" class="select select-bordered w-full bg-dark/50 focus:bg-dark text-white border-white/10 focus:border-primary">
                              <option value="Demo">Platform Demo</option>
                              <option value="Pricing">Pricing Question</option>
                              <option value="Partnership">Partnership</option>
                              <option value="Other">Other</option>
                          </select>
                      </div>
                      <div class="form-control">
                          <label class="label pt-0 pb-1"><span class="label-text text-gray-300">Preferred Time <span class="text-error">*</span></span></label>
                          <input type="datetime-local" id="demo-time" class="input input-bordered w-full bg-dark/50 focus:bg-dark text-white border-white/10 focus:border-primary" required />
                      </div>
                  </div>"""
    if demo_type_original in html:
        html = html.replace(demo_type_original, demo_type_new)
    
    # Fix Book a Demo Button Color
    btn_orig = '<button type="submit" id="btn-demo-submit" class="btn btn-primary w-full mt-2">Submit Request</button>'
    btn_new = '<button type="submit" id="btn-demo-submit" class="btn bg-primary hover:bg-violet-600 text-white border-none w-full mt-2">Submit Request</button>'
    html = html.replace(btn_orig, btn_new)
    
    # Fix Comparison Table Emojis -> SVGs
    icon_bulk = '<div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">ðŸ“¨</div>'
    svg_bulk = '<div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">\n                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>\n                                    </div>'
    if "ðŸ“¨" not in html: # check other mojibake string
        icon_bulk = '<div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">dY""</div>'
    html = html.replace(icon_bulk, svg_bulk)

    icon_zap = '<div class="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center text-secondary">âš¡</div>'
    svg_zap = '<div class="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center text-secondary">\n                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>\n                                    </div>'
    if "âš¡" not in html:
        icon_zap = '<div class="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center text-secondary">a!</div>'
    html = html.replace(icon_zap, svg_zap)

    # Fix modal close buttons
    html = html.replace('<button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2 text-gray-400 hover:text-white">?</button>', '<button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2 text-gray-400 hover:text-white">&#10005;</button>')
    html = html.replace('<button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">âœ•</button>', '<button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">&#10005;</button>')

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    # 2. Update landing.js
    landing_path = os.path.join(frontend_dir, "js", "landing.js")
    if os.path.exists(landing_path):
        with open(landing_path, "r", encoding="utf-8") as f:
            ljs = f.read()
        ljs = ljs.replace("Billed $", "Billed ₹")
        ljs = ljs.replace("'$' +", "'₹' +")
        ljs = ljs.replace("$${", "₹${")
        payload_orig = "inquiry_type: document.getElementById('demo-type').value,\n            message: document.getElementById('demo-message').value"
        payload_new = "inquiry_type: document.getElementById('demo-type').value,\n            scheduled_time: document.getElementById('demo-time').value,\n            message: document.getElementById('demo-message').value"
        ljs = ljs.replace(payload_orig, payload_new)
        with open(landing_path, "w", encoding="utf-8") as f:
            f.write(ljs)
            
    # 3. Update client-app.js
    client_path = os.path.join(frontend_dir, "js", "client-app.js")
    if os.path.exists(client_path):
        with open(client_path, "r", encoding="utf-8") as f:
            cjs = f.read()
        cjs = cjs.replace("Billed $", "Billed ₹")
        cjs = cjs.replace(">$15<", ">₹1,200<")
        cjs = cjs.replace(">$35<", ">₹2,800<")
        cjs = cjs.replace(">$", ">₹")
        cjs = cjs.replace("'$' +", "'₹' +")
        cjs = cjs.replace("$${", "₹${")
        with open(client_path, "w", encoding="utf-8") as f:
            f.write(cjs)

if __name__ == "__main__":
    main()
