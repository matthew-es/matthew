from flask import Blueprint
chats = Blueprint('chats', __name__, template_folder='templates', static_folder='static')
from .chats_routes import *