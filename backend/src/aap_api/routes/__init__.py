from .auth import auth
from .email_drafter import email_drafter
from .intent_classifier import intent_classifier
from .pii_redaction import pii_redaction
from .shareholder_assistant import shareholder_assistant
from .stock_assistant import stock_assistant

blueprints = [
    auth,
    stock_assistant,
    intent_classifier,
    email_drafter,
    pii_redaction,
    shareholder_assistant,
]