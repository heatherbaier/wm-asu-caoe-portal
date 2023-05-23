########################################################################
#################        Importing packages      #######################
########################################################################
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import pymysql



# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()
def create_app():
    app = Flask(__name__) # creates the Flask instance, __name__ is the name of the current Python module

    pymysql.install_as_MySQLdb()

    secret_key = os.getenv("SECRET_KEY")
    if os.path.isfile(secret_key):
        with open(secret_key, 'r') as f:
            secret_key = f.read().rstrip()

    app.config['SECRET_KEY'] = secret_key

    db_uri = os.getenv("DATABASE_URI")
    if os.path.isfile(db_uri):
        with open(db_uri, 'r') as f:
            db_uri = f.read().rstrip()

    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # deactivate Flask-SQLAlchemy track modifications
    db.init_app(app) # Initialiaze sqlite database
    # The login manager contains the code that lets your application and Flask-Login work together
    login_manager = LoginManager() # Create a Login Manager instance
    login_manager.login_view = 'auth.login' # define the redirection path when login required and we attempt to access without being logged in
    login_manager.init_app(app) # configure it for login
    from models import User
    @login_manager.user_loader
    def load_user(user_id): #reload user object from the user ID stored in the session
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))
    # blueprint for auth routes in our app
    # blueprint allow you to orgnize your flask app
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    # blueprint for non-auth parts of app
    from app import main as main_blueprint
    app.register_blueprint(main_blueprint)
    return app
