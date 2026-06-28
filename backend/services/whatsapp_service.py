import httpx
import json
import re
from typing import Tuple, Optional

TEMPLATE_CACHE = {}

async def _fetch_template_structure(client: httpx.AsyncClient, waba_id: str, template_name: str, access_token: str) -> dict:
    cache_key = f"{waba_id}_{template_name}"
    if cache_key in TEMPLATE_CACHE:
        return TEMPLATE_CACHE[cache_key]

    url = f"https://graph.facebook.com/v25.0/{waba_id}/message_templates?name={template_name}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = await client.get(url, headers=headers, timeout=10.0)
    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            # Prefer 'en' or 'en_US' if available, otherwise just take the first approved one
            templates = [t for t in data["data"] if t.get("status") == "APPROVED"]
            if not templates:
                templates = data["data"]
                
            selected = templates[0]
            for t in templates:
                lang = t.get("language", "")
                if lang in ("en", "en_US"):
                    selected = t
                    break
                    
            TEMPLATE_CACHE[cache_key] = selected
            return selected
            
    return {}

async def send_whatsapp_message(
    phone: str,
    template_name: str,
    phone_number_id: str,
    waba_id: str,
    access_token: str,
    fallback_name: str = "Customer"
) -> Tuple[bool, Optional[str]]:
    """
    Sends a WhatsApp template message using the Meta Graph API.
    Dynamically builds the payload by fetching the template structure.
    """
    if not phone_number_id or not access_token or not waba_id:
        return False, "WhatsApp credentials not configured for this client."

    url = f"https://graph.facebook.com/v25.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    fallback_vars = [fallback_name, "Our Team", "updates", "more info", "here", "today", "details", "contact us", "support"]

    try:
        async with httpx.AsyncClient() as client:
            template_def = await _fetch_template_structure(client, waba_id, template_name, access_token)
            
            if not template_def:
                return False, f"Meta API Error: Template '{template_name}' not found or not approved in your Meta Dashboard."
                
            lang = template_def.get("language", "en_US")
            
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template_name.strip(),
                    "language": {
                        "code": lang
                    }
                }
            }
            
            components_payload = []
            
            # Parse template components to build the exact payload
            for comp in template_def.get("components", []):
                comp_type = comp.get("type", "").upper()
                
                if comp_type == "HEADER":
                    format_type = comp.get("format", "").upper()
                    if format_type == "TEXT":
                        # Does it have variables? {{1}}
                        text_val = comp.get("text", "")
                        var_count = len(re.findall(r"\{\{\d+\}\}", text_val))
                        if var_count > 0:
                            components_payload.append({
                                "type": "header",
                                "parameters": [{"type": "text", "text": fallback_name} for _ in range(var_count)]
                            })
                    elif format_type == "IMAGE":
                        components_payload.append({
                            "type": "header",
                            "parameters": [{
                                "type": "image",
                                "image": {"link": "https://images.unsplash.com/photo-1596524430615-b46475ddff6e?auto=format&fit=crop&q=80&w=1000"}
                            }]
                        })
                    elif format_type == "DOCUMENT":
                        components_payload.append({
                            "type": "header",
                            "parameters": [{
                                "type": "document",
                                "document": {"link": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"}
                            }]
                        })
                    elif format_type == "VIDEO":
                        components_payload.append({
                            "type": "header",
                            "parameters": [{
                                "type": "video",
                                "video": {"link": "https://www.w3schools.com/html/mov_bbb.mp4"}
                            }]
                        })
                        
                elif comp_type == "BODY":
                    text_val = comp.get("text", "")
                    var_count = len(re.findall(r"\{\{\d+\}\}", text_val))
                    if var_count > 0:
                        params = []
                        for i in range(var_count):
                            val = fallback_vars[i] if i < len(fallback_vars) else "..."
                            params.append({"type": "text", "text": val})
                        components_payload.append({
                            "type": "body",
                            "parameters": params
                        })
                        
                elif comp_type == "BUTTONS":
                    buttons = comp.get("buttons", [])
                    for idx, btn in enumerate(buttons):
                        if btn.get("type", "").upper() == "URL":
                            url_val = btn.get("url", "")
                            # If url contains {{1}}, it's dynamic
                            if "{{" in url_val:
                                components_payload.append({
                                    "type": "button",
                                    "sub_type": "url",
                                    "index": str(idx),
                                    "parameters": [{"type": "text", "text": "action"}]
                                })
            
            if components_payload:
                payload["template"]["components"] = components_payload
                
            print(f"📦 Built Smart Payload for '{template_name}': {json.dumps(payload['template'].get('components', []), indent=2)}")
                
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code in (200, 201):
                response_json = response.json()
                print(f"✅ Smart Template '{template_name}' payload accepted by Meta!")
                print("Meta Response:", json.dumps(response_json, indent=2))
                
                messages = response_json.get("messages", [])
                if messages and len(messages) > 0:
                    message_id = messages[0].get("id")
                    print(f"Message ID: {message_id}")
                    
                return True, None
                
            error_data = response.json()
            err_code = error_data.get("error", {}).get("code")
            last_err_msg = error_data.get("error", {}).get("message", "Unknown Meta API Error")
            
            return False, f"Meta API Error ({response.status_code}): {last_err_msg}"
            
    except Exception as e:
        return False, f"Exception occurred while sending WhatsApp message: {str(e)}"
