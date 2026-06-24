import os
import re

FRONTEND_DIR = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replacements for dark themes to improve contrast
    # gray-500 -> gray-400
    # gray-600 -> gray-400 
    # gray-700 -> gray-300
    # gray-800 -> text-white
    # gray-900 -> text-white
    
    new_content = re.sub(r'\btext-gray-500\b', 'text-gray-400', content)
    new_content = re.sub(r'\btext-gray-600\b', 'text-gray-400', new_content)
    new_content = re.sub(r'\btext-gray-700\b', 'text-gray-300', new_content)
    new_content = re.sub(r'\btext-gray-800\b', 'text-white', new_content)
    new_content = re.sub(r'\btext-gray-900\b', 'text-white', new_content)
    
    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk(FRONTEND_DIR):
    for file in files:
        if file.endswith('.html') or file.endswith('.js'):
            process_file(os.path.join(root, file))

print("Done replacing dark text classes.")
