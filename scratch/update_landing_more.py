import os

html_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\frontend\index.html"
with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

# 1. Update Hero Subtitle
old_hero = "Connect your Google Sheets, define your templates, and let our AI match the perfect message to every lead automatically."
new_hero = "Connect your Google Sheets, define your templates, and let our AI dispatch the perfect, personalized Email & WhatsApp message to every lead automatically."
html_content = html_content.replace(old_hero, new_hero)

# 2. Add WhatsApp Card to Features
# Current features grid is <div class="grid md:grid-cols-3 gap-8">
old_grid = '<div class="grid md:grid-cols-3 gap-8">'
new_grid = '<div class="grid md:grid-cols-2 lg:grid-cols-4 gap-8">'
html_content = html_content.replace(old_grid, new_grid)

# Find the end of the 3rd card
# The 3rd card ends with </div>\n                    </div>\n                </div>\n            </div>\n        </section>
old_end_features = '''                        </div>
                    </div>
                </div>
            </div>
        </section>'''

whatsapp_card = '''                        </div>
                    </div>
                    <div class="card bg-base-100 border border-white/5 hover:border-green-400/50 transition-colors">
                        <div class="card-body">
                            <h2 class="card-title text-green-400">Native WhatsApp API</h2>
                            <p class="text-gray-400 text-sm mt-2">Go beyond email. Trigger official Meta WhatsApp templates directly from your Sheet to guarantee 98% open rates.</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>'''
html_content = html_content.replace(old_end_features, whatsapp_card)

# 3. Update the fake terminal "Vs Bulk Senders" to mention WA
old_vs_bulk = '''<div class="flex items-center gap-2 text-green-400 font-bold text-sm mb-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> 99% Primary Inbox Placement</div>'''
new_vs_bulk = '''<div class="flex items-center gap-2 text-green-400 font-bold text-sm mb-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> Email + WhatsApp Combined</div>
                                        <p class="text-xs text-gray-400 pl-6 mb-3">Bulk mailers only do email. We hit your leads on multiple channels to triple your response rate.</p>
                                        <div class="flex items-center gap-2 text-green-400 font-bold text-sm mb-1"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg> 99% Primary Inbox Placement</div>'''
html_content = html_content.replace(old_vs_bulk, new_vs_bulk)

# 4. Update the visual sheet UI
old_sheet_tr = '''<td class="py-3 px-4 relative overflow-hidden text-green-300 flex items-center gap-2">
                                    <span class="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-[10px] uppercase font-bold tracking-wider whitespace-nowrap">Real Estate Template</span>
                                    <div><span id="typewriter-1"></span><span class="animate-pulse font-bold text-primary ml-1" id="cursor-1">|</span></div>
                                </td>'''
new_sheet_tr = '''<td class="py-3 px-4 relative overflow-hidden flex items-center gap-2">
                                    <span class="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-[10px] uppercase font-bold tracking-wider whitespace-nowrap">Real Estate Template</span>
                                    <span class="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-[10px] uppercase font-bold tracking-wider whitespace-nowrap hidden sm:inline">WhatsApp Queued</span>
                                    <div class="text-green-300"><span id="typewriter-1"></span><span class="animate-pulse font-bold text-primary ml-1" id="cursor-1">|</span></div>
                                </td>'''
html_content = html_content.replace(old_sheet_tr, new_sheet_tr)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print("Done updating index.html")
