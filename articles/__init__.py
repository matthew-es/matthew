from flask import Blueprint
articles = Blueprint('articles', __name__, template_folder='templates', static_folder='static')
from .articles_routes import *