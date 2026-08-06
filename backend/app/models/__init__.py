"""
Import every model here so `Base.metadata.create_all()` in main.py discovers
all tables, and so relationship() string references resolve correctly.
"""
from app.models.user import User  # noqa: F401
from app.models.db_connection import DBConnection  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.saved_query import SavedQuery  # noqa: F401
