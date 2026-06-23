import os

js_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\landing.js"
with open(js_path, "r", encoding="utf-8") as f:
    js_content = f.read()

js_content = js_content.replace("Emails per day", "Messages (Email/WA) per day")

with open(js_path, "w", encoding="utf-8") as f:
    f.write(js_content)

print("Done updating pricing in landing.js")
