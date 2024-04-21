from flask import Blueprint
rss = Blueprint('rss', __name__, template_folder='templates', static_folder='static')
from .rss_routes import *