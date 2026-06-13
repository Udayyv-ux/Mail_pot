import smtplib
import json
import os
import re
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from groq import Groq
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SHEET_ID = "1ebb66FSCxH6_p26MtwQgY4puX4pSOyMWSO7mjx2xQMU" 
SENDER_EMAIL = "contact@homestoday.in"
SENDER_PASSWORD = "ssdjdjmpquaatfdx" 
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY)

# --- GOOGLE SHEETS SETUP ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("backend/credentials.json", scope)

# --- DYNAMIC CONFIG & TEMPLATE SYSTEM ---
TEMPLATE_FILE = "backend/templates.json"
CONFIG_FILE = "backend/config.json"

def get_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"sheet_id": ""}, f)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_sheet_id(url_or_id):
    # Automatically extract the ID if the user pastes a full URL
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_or_id)
    sheet_id = match.group(1) if match else url_or_id.strip()
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"sheet_id": sheet_id}, f)
    return sheet_id

def get_templates():
    if not os.path.exists(TEMPLATE_FILE):
        default_templates = {"General": {"subject": "Thanks for connecting!", "body": "<h2>Hi {first_name},</h2><p>We received your inquiry.</p>"}}
        with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
            json.dump(default_templates, f)
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_template(project_id, subject, body):
    templates = get_templates()
    templates[project_id] = {"subject": subject, "body": body}
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f)

def delete_template(project_id):
    templates = get_templates()
    if project_id in templates:
        del templates[project_id]
        with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
            json.dump(templates, f)
        return True
    return False

# --- SMART AGENT LOCATION VERIFICATION ---
def categorize_with_ai(lead_info):
    if not lead_info:
        return "General"
    templates = get_templates()
    categories = list(templates.keys())
    categories_str = ", ".join([f"'{c}'" for c in categories])
        
    prompt = f"""
    You are an advanced real-estate routing agent. 
    Customer Inquiry: "{lead_info}"
    Available Project IDs: {categories_str}
    
    Instructions: Match the location or intent to the closest Project ID. If unsure, reply 'General'.
    Reply ONLY with the exact matching Project ID string.
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        decision = response.choices[0].message.content.strip()
        if decision in templates:
            return decision
        return "General"
    except Exception as e:
        print(f"AI Agent Error: {e}")
        return "General"

def send_template_email(to_email, first_name, category):
    if not first_name.strip():
        first_name = "There"
    templates = get_templates()
    if category not in templates:
        category = "General"
        
    template_data = templates[category]
    subject = template_data["subject"]
    html_body = template_data["body"].replace("{first_name}", first_name)
    
    msg = MIMEMultipart('alternative')
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def process_sheet():
    config = get_config()
    sheet_id = config.get("sheet_id")
    
    if not sheet_id:
        print("Waiting for Google Sheet link to be added in dashboard...")
        return 0

    try:
        # Connect dynamically on every run using the saved ID
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(sheet_id).sheet1
        records = sheet.get_all_values()
        emails_sent_this_run = 0
        
        BATCH_LIMIT = 10 
        ANTI_SPAM_DELAY = 2 
        
        for i, row in reversed(list(enumerate(records[1:], start=2))):
            if emails_sent_this_run >= BATCH_LIMIT:
                break 

            name = row[0] if len(row) > 0 else ""
            email = row[1] if len(row) > 1 else ""
            inquiry = row[2] if len(row) > 2 else ""
            status = row[4] if len(row) > 4 else "" 
            
            if email.strip() and inquiry.strip() and status != "Sent":
                print(f"Agent analyzing lead: {name} | Inquiry: {inquiry}")
                category = categorize_with_ai(inquiry)
                sheet.update_cell(i, 4, category)
                success = send_template_email(email, name, category)
                
                if success:
                    sheet.update_cell(i, 5, "Sent")
                    emails_sent_this_run += 1
                    time.sleep(ANTI_SPAM_DELAY)
            
            elif status == "Sent":
                continue 
                
        return emails_sent_this_run
    except Exception as e:
        print(f"Google Sheets Error (Check if link is correct & shared with service email): {e}")
        return 0