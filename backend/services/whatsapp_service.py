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
    
    # Fallback languages in case the template was created in 'en' or 'en_GB' instead of 'en_US'
    languages_to_try = ["en_US", "en", "en_GB"]
    
    # Fallback variable combinations in case the template expects 0, 1, or 2 variables
    # (Since we don't have a UI mapper, we intelligently brute-force the parameter count)
    var_combinations = [
        [],                            # 0 params
        [fallback_name],               # 1 param (Name)
        [fallback_name, "Our Team"]    # 2 params (Name, Company/Sender)
    ]
    
    last_err_msg = "Unknown Error"
    last_status = 400
    
    try:
        async with httpx.AsyncClient() as client:
            for lang in languages_to_try:
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
                        return True, None
                    
                    error_data = response.json()
                    err_code = error_data.get("error", {}).get("code")
                    last_err_msg = error_data.get("error", {}).get("message", "Unknown Meta API Error")
                    last_status = response.status_code
                    
                    # 132000 = Number of parameters does not match. (Try next vars_list)
                    # 132001 = Template does not exist in language. (Break inner loop, try next language)
                    
                    if err_code == 132001:
                        break # Break out of var loop, try next language
                        
                    elif err_code != 132000:
                        # Some other fatal error (e.g., number not found, invalid token)
                        return False, f"Meta API Error ({last_status}): {last_err_msg}"
                        
            return False, f"Meta API Error ({last_status}): {last_err_msg} (Tried languages and variable combinations)"
                
    except Exception as e:
        return False, f"Exception occurred while sending WhatsApp message: {str(e)}"
