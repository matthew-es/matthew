from flask import Blueprint
llms = Blueprint('llms', __name__, template_folder='templates', static_folder='static')
from .llms_routes import *