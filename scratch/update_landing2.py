import os

# Update landing.js
js_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\landing.js"
with open(js_path, "r", encoding="utf-8") as f:
    js_content = f.read()

js_replacements = {
    "Create various email templates": "Create various message templates",
    "the most relevant email template": "the most relevant message template",
    "the email status": "the message status",
    "the perfect email template": "the perfect message template",
    "bring my own email account": "bring my own email or WhatsApp account",
    "send directly from your own domain.": "send directly from your own domain and Meta WhatsApp number."
}
for old, new in js_replacements.items():
    js_content = js_content.replace(old, new)
with open(js_path, "w", encoding="utf-8") as f:
    f.write(js_content)

# Update index.html
html_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\index.html"
with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

old_feature = '''<h2 class="card-title text-green-400">High Deliverability</h2>
                            <p class="text-gray-400 text-sm mt-2">Connect seamlessly via Gmail HTTP API. We throttle sending speeds to protect your domain reputation automatically.</p>'''
new_feature = '''<h2 class="card-title text-green-400">Email & WhatsApp</h2>
                            <p class="text-gray-400 text-sm mt-2">Connect seamlessly via Gmail API & Meta Cloud API. We throttle sending speeds and handle API limits to protect your domain and number reputation automatically.</p>'''

html_content = html_content.replace(old_feature, new_feature)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print("Done updating js and html")
