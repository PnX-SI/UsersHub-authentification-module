from authlib.integrations.flask_client import OAuth

from .auth_manager import *
from .authentication import *
from .user_manager import user_manager

oauth = OAuth()
