import httpx
import re

async def send_whatsapp_message(phone: str, template_name: str, access_token: str, phone_number_id: str, variables: list[str] = None) -> tuple[bool, str]:
    """
    Send a WhatsApp template message using the Meta Cloud API.
    """
    if not phone or not template_name or not access_token or not phone_number_id:
        return False, "Missing required WhatsApp credentials or parameters."
        
    # Clean the phone number to digits only (Meta API requires country code without '+')
    clean_phone = str(phone).replace("+", "").replace(" ", "").replace("-", "").strip()
    clean_phone = re.sub(r'\D', '', clean_phone)
        
    if not clean_phone:
        return False, "Invalid phone number."
        
    url = f"https://graph.facebook.com/v23.0/{phone_number_id}/messages" # Updated to v23.0 per user spec
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    template_data = {
        "name": template_name,
        "language": {
            "code": "en" # Updated to 'en' per user spec
        }
    }
    
    if variables:
        template_data["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": str(v)} for v in variables]
            }
        ]
    
    payload = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "template",
        "template": template_data
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in (200, 201):
                return True, "Success"
            else:
                return False, f"Meta API Error ({response.status_code}): {response.text}"
    except Exception as e:
        return False, f"Request failed: {str(e)}"
