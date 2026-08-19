import os
import smtplib
import markdown
from flask import Blueprint, jsonify, request
from dotenv import load_dotenv
from google import genai
from google.genai import types
from email.message import EmailMessage

load_dotenv()
client = genai.Client()

email_drafter = Blueprint(
    "email_drafter", __name__, url_prefix="/api/email-drafter"
)

config = types.GenerateContentConfig(
    temperature=0.5,
    top_p=0.8,
    top_k=40
)

@email_drafter.get("/health")
def health():
    return jsonify({"status": "ok", "service": "email-drafter"})


@email_drafter.post("/draft")
def draft():
    data = request.get_json(silent=True) or {}
    customer_email = data.get("email", "customer@example.com")
    customer_query = data.get("query", "")
    intent = data.get("intent", "general_inquiry")
    sentiment = data.get("sentiment", "neutral")
    
    if not customer_query:
        return jsonify({"error": "Missing customer query"}), 400

    system_prompt = f"""
    You are the internal customer support AI Copilot for the fintech application Bankly. 
    Draft a professional, concise email to the customer regarding their issue.
    
    Customer Email: {customer_email}
    Customer Query: "{customer_query}"
    Detected Intent: {intent}
    Detected Sentiment: {sentiment}
    
    Rules:
    1. If the sentiment is NEGATIVE, adopt an empathetic and apologetic tone.
    2. If the sentiment is POSITIVE, adopt an upbeat and professional tone without unnecessary apologies.
    3. Provide actionable, recommended steps. Do not invent bank policies.
    4. You MUST follow this exact header structure, keeping the empty blank lines exactly as shown below:
    
    To: {customer_email}

    Subject: [Write a concise, professional, non-emotional subject here]

    5. Structure the rest of the email body professionally with standard paragraph spacing.
    6. Acknowledge the issue clearly.
    7. Provide the Next Best Action using a clearly spaced bulleted list.
    8. Sign off as 'The Bankly Support Team'.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=system_prompt,
            config=config
        )
        return jsonify({"draft": response.text})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@email_drafter.post("/iterate")
def iterate():
    data = request.get_json(silent=True) or {}
    current_draft = data.get("current_draft", "")
    action = data.get("action", "regenerate")
    
    instructions = {
        "shorter": "Rewrite the following email to be 50% shorter and more direct.",
        "empathetic": "Rewrite the following email to be warmer, more apologetic, and highly empathetic.",
        "regenerate": "Ignore the previous draft and write a completely new, alternative email for this issue."
    }
    
    tweak_instruction = instructions.get(action, instructions["regenerate"])
    
    prompt = f"""
    INSTRUCTION:
    {tweak_instruction}

    CURRENT DRAFT:
    {current_draft}
    
    Rules:
        1. You MUST follow this exact header structure, keeping the empty blank lines exactly as shown below:
        
        To: [The customer's email]
    
        Subject: [Write a concise, professional, non-emotional subject here]
    
        2. Structure the rest of the email body professionally with standard paragraph spacing.
        3. Sign off as 'The Bankly Support Team'.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=config
        )
        return jsonify({"new_draft": response.text})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@email_drafter.post("/send")
def send_email():
    data = request.get_json(silent=True) or {}
    recipient = data.get("to")
    subject = data.get("subject", "Bankly Customer Support Update")
    body = data.get("body")

    # Basic validation
    if not recipient or not body:
        return jsonify({"error": "Missing recipient or email body"}), 400

    # Load credentials from .env
    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        return jsonify({"error": "Server email credentials are not configured."}), 500

    try:
        # Convert the Gemini Markdown string into HTML
        html_body = markdown.markdown(body)

        # Construct the email object
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient

        # Set the plain text version first (acts as a fallback)
        msg.set_content(body)
        
        # Attach the formatted HTML version
        msg.add_alternative(html_body, subtype='html')

        # Sending the email via gmail's server
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return jsonify({"status": "success", "message": f"Email successfully sent to {recipient}"})
        
    except Exception as e:
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500