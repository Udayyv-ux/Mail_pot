import aiohttp
import re

async def send_whatsapp_message(phone: str, template_name: str, access_token: str, phone_number_id: str) -> tuple[bool, str]:
    """
    Send a WhatsApp template message using the Meta Cloud API.
    """
    if not phone or not template_name or not access_token or not phone_number_id:
        return False, "Missing required WhatsApp credentials or parameters."
        
    # Clean the phone number to digits only (Meta API requires country code without '+')
    # Example: '+1 (555) 662-9367' -> '15556629367'
    clean_phone = re.sub(r'\D', '', str(phone))
    if not clean_phone:
        return False, "Invalid phone number."
        
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "en_US"
            }
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status in (200, 201):
                    return True, "Success"
                else:
                    error_data = await response.text()
                    return False, f"Meta API Error ({response.status}): {error_data}"
    except Exception as e:
        return False, f"Request failed: {str(e)}"
