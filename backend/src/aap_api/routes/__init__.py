from .auth import auth
from .email_drafter import email_drafter
from .intent_classifier import intent_classifier
from .stock_assistant import stock_assistant
from .tickets import tickets_bp

blueprints = [auth, stock_assistant, intent_classifier, email_drafter, tickets_bp]