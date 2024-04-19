from flask import Blueprint, render_template
from recap import  db

bp = Blueprint('errors', __name__)

@bp.app_errorhandler(404) #app_errorhandler allows the blueprint to overide app methods vs scoped methods to the blueprint
def not_found_error(error):
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500



