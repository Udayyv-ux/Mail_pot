import httpx
import json
from typing import Tuple, Optional

async def send_whatsapp_message(
    phone: str,
    template_name: str,
    phone_number_id: str,
    access_token: str,
    fallback_name: str = "Customer"
) -> Tuple[bool, Optional[str]]:
    """
    Sends a WhatsApp template message using the Meta Graph API.
    
    Args:
        phone: The recipient's phone number with country code
        template_name: The name of the pre-approved WhatsApp template.
        phone_number_id: The Meta WhatsApp Phone Number ID.
        access_token: The Meta WhatsApp System User Access Token.
        fallback_name: The name to use if the template expects 1 variable.
        
    Returns:
        (Success Boolean, Error Message String)
    """
    if not phone_number_id or not access_token:
        return False, "WhatsApp credentials not configured for this client."

    # Meta Graph API Endpoint (v19.0)
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Fallback languages
    languages_to_try = ["en_US", "en", "en_GB", "en_IN"]
    
    # Fallback variable combinations (0 to 4 parameters)
    var_combinations = [
        [],                            
        [fallback_name],               
        [fallback_name, "Our Team"],
        [fallback_name, "Our Team", "updates"],
        [fallback_name, "Our Team", "updates", "more info"]
    ]
    
    last_err_msg = "Unknown Error"
    last_status = 400
    last_err_code = None
    
    print(f"🔍 Starting WhatsApp Auto-Guesser for phone: {phone}, template: '{template_name}'")
    
    try:
        async with httpx.AsyncClient() as client:
            for lang in languages_to_try:
                lang_found = False
                
                for vars_list in var_combinations:
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "template",
                        "template": {
                            "name": template_name,
                            "language": {
                                "code": lang
                            }
                        }
                    }
                    
                    if vars_list:
                        payload["template"]["components"] = [
                            {
                                "type": "body",
                                "parameters": [{"type": "text", "text": str(v)} for v in vars_list]
                            }
                        ]
                    
                    response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                    
                    if response.status_code in (200, 201):
                        print(f"   ✅ Success with lang='{lang}' and {len(vars_list)} variables.")
                        return True, None
                    
                    error_data = response.json()
                    err_code = error_data.get("error", {}).get("code")
                    last_err_msg = error_data.get("error", {}).get("message", "Unknown Meta API Error")
                    last_status = response.status_code
                    last_err_code = err_code
                    
                    print(f"   ❌ Failed with lang='{lang}', {len(vars_list)} vars. Code: {err_code}, Msg: {last_err_msg}")
                    
                    # 132000 = Number of parameters does not match.
                    if err_code == 132000:
                        lang_found = True
                        continue # Try the next variable combination
                        
                    # 132001 = Template does not exist in this language.
                    elif err_code == 132001:
                        break # Break inner loop, try the next language
                        
                    else:
                        # Some other fatal error
                        return False, f"Meta API Error ({last_status}): {last_err_msg}"
                
                # If we found the language but none of the variable combinations worked...
                if lang_found:
                    return False, f"Meta API Error ({last_status}): (#132000) Template requires complex parameters (Header/Button) or more than 4 variables, which the auto-guesser cannot fulfill."
                        
            return False, f"Meta API Error ({last_status}): {last_err_msg} (Tried languages and variable combinations)"
                
    except Exception as e:
        return False, f"Exception occurred while sending WhatsApp message: {str(e)}"
