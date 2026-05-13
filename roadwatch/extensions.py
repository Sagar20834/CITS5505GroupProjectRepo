from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
setattr(login_manager, "login_view", "auth.login")
setattr(login_manager, "login_message", "Please log in to access that page.")
setattr(login_manager, "login_message_category", "warning")
