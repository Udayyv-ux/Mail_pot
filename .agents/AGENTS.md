
## WhatsApp Cloud API Integration Rules
- **Silent Drops (200 OK):** Meta's WhatsApp Cloud API will return HTTP 200 OK even if a message fails to deliver asynchronously. The most common causes of silent drops are:
  1. Missing required payload components (e.g., if a template has a dynamic button or a media header, the payload MUST include a button/header component, otherwise it is dropped silently).
  2. The WhatsApp Business Account (WABA) lacks a valid payment method (credit card).
  3. The WABA business verification is pending or failed (tier 0 limit).
- **Smart Payload Builder:** MailPilot uses a Smart Payload Builder in \whatsapp_service.py\. It fetches the exact template schema from Meta (\GET /{waba_id}/message_templates?name={template_name}\), parses the required Headers, Bodies, and Buttons, and dynamically injects variables to ensure 100% compliant payloads. Do not revert to the old auto-guesser method.

