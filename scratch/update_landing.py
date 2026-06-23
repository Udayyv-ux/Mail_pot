import os

file_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

replacements = {
    "AI-Powered Email Automation": "AI-Powered Email & WhatsApp Automation",
    "C: AI Generated Email": "C: AI Generated Message",
    "Emails sent per week:": "Messages sent per week:",
    "for bulk email specifically": "for bulk outreach specifically",
    "Most email software forces you": "Most outreach software forces you",
    "Map columns directly to email variables.": "Map columns directly to message variables.",
    "Manage multiple email campaigns": "Manage multiple campaigns",
    "most relevant email template": "most relevant template",
    "send personalized emails.": "send personalized messages.",
    "email automation platform": "outreach automation platform",
    "intelligent email automation": "intelligent outreach automation",
    "top 5 cold email templates": "top 5 outreach templates",
    "Start automating your email outreach today.": "Start automating your outreach today.",
    "6 mins per personalized email": "6 mins per personalized message",
    "0 mins per email": "0 mins per message",
    "Vs. Bulk Mailers": "Vs. Bulk Senders"
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done updating index.html")
