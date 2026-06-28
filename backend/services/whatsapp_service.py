import httpx
import json
from typing import Tuple, Optional

async def send_whatsapp_message(
    phone: str,
    template_name: str,
    phone_number_id: str,
    access_token: str,
    variables: Optional[list] = None
) -> Tuple[bool, Optional[str]]:
    """
    Sends a WhatsApp template message using the Meta Graph API.
    
    Args:
        phone: The recipient's phone number with country code (e.g., '916303488801')
        template_name: The name of the pre-approved WhatsApp template.
        phone_number_id: The Meta WhatsApp Phone Number ID.
        access_token: The Meta WhatsApp System User Access Token.
        variables: Optional list of strings for template placeholders.
        
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
    
    # Payload for a basic template message
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "en_US" # Defaulting to en_US; can be made dynamic later
            }
        }
    }
    
    if variables:
        payload["template"]["components"] = [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": str(v)} for v in variables]
            }
        ]
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code in (200, 201):
                return True, None
            else:
                error_data = response.json()
                err_msg = error_data.get("error", {}).get("message", "Unknown Meta API Error")
                return False, f"Meta API Error ({response.status_code}): {err_msg}"
                
    except Exception as e:
        return False, f"Exception occurred while sending WhatsApp message: {str(e)}"
