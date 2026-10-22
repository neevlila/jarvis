import json
import re
from providers.provider_manager import ProviderManager

def extract_json_data(res_text):
    text_stripped = res_text.strip()
    try:
        return json.loads(text_stripped)
    except Exception:
        pass
    json_match = re.search(r'```json\s*(.*?)\s*```', res_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except Exception:
            pass
    brace_match = re.search(r'(\{.*\})', res_text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1).strip())
        except Exception:
            pass
    return None

def generate_email_mistral(prompt_topic: str, role: str, about: str, email_format: str, sender_details: dict) -> dict:
    """
    Calls Groq llama-3.3-70b-versatile via ProviderManager to generate an email.
    Returns a dict with {"subject": "...", "body": "..."}.
    """
    system_prompt = (
        "You are J.A.R.V.I.S., a premium digital assistant. "
        f"Write a professional, well-structured {email_format.lower()} email to a recipient who is a: {role}.\n"
        "Ensure the email body is formatted with proper paragraph breaks and double newlines (\\n\\n) between sections (e.g. greeting, body paragraphs, and sign-off on separate lines) to look professional.\n"
        "Format the response as a JSON object with two keys:\n"
        "'subject' (containing a suitable subject line)\n"
        "'body' (containing the text body of the email, preserving all the newlines in the string value).\n"
        "Do NOT include any markdown asterisks like * or ** anywhere in your response (subject or body).\n"
        "Fill in all details (like sender name, department, start and end dates) directly in the email content. "
        "Do not use placeholders like '[Your Name]', '[Start Date]', etc. If details are provided, output them directly."
    )

    user_prompt = f"The email context is: {about}\n"
    if sender_details:
        if sender_details.get("sender_name"):
            user_prompt += f"Sender name: {sender_details['sender_name']}\n"
        if sender_details.get("sender_dept"):
            user_prompt += f"Sender position/department: {sender_details['sender_dept']}\n"
        if sender_details.get("start_date"):
            user_prompt += f"Start date: {sender_details['start_date']}\n"
        if sender_details.get("end_date"):
            user_prompt += f"End date: {sender_details['end_date']}\n"

    user_prompt += "\nRespond ONLY with a valid JSON object matching the keys 'subject' and 'body'. Do not output any markdown code blocks, preamble, or explanations outside the JSON."

    res_text = ProviderManager.chat(
        system_prompt=system_prompt,
        messages_history=[],
        user_prompt=user_prompt,
        response_format_json=True
    )

    parsed = extract_json_data(res_text)
    if parsed and isinstance(parsed, dict) and "subject" in parsed and "body" in parsed:
        parsed["subject"] = parsed["subject"].replace("**", "").replace("*", "")
        parsed["body"] = parsed["body"].replace("**", "").replace("*", "")
        return parsed
    else:
        # Fallback parsing if JSON is malformed
        res_cleaned = res_text.replace("**", "").replace("*", "")
        subject = f"Regarding {about[:35]}"
        body = res_cleaned
        return {"subject": subject, "body": body}
