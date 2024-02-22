'''Server startup script, creates the flask app'''
from flask import Flask, g, redirect, url_for
from flask_login import LoginManager
# from flask_sqlalchemy import SQLAlchemy

from flask_mysqldb import MySQL

from . import auth, manage, scheduling
from .user import User

# db = SQLAlchemy()


def create_app(test_config=None):
    '''Creates the flask app, connection to the database and initilizes
    the default settings'''
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # SQLALCHEMY_DATABASE_URI=(
        #     'mysql://root:password@localhost/avis_bookings'),
        # SQLALCHEMY_TRACK_MODIFICATIONS=False,
        
        MYSQL_USER='rehman',
        MYSQL_PASSWORD='R4rehman__',
        MYSQL_DB='avis_bookings',
        MYSQL_HOST='localhost',
        MYSQL_PORT=3306,
        MYSQL_CURSORCLASS='DictCursor'
    )
    app.secret_key = 'oooooooooo'
    app.config['SESSION_TYPE']= 'filesystem'
    # db.init_app(app)
    mysql = MySQL(app)

    # flask-login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # callback to reload the user object
    @login_manager.user_loader
    def load_user(user_id):
        '''This function is called by flask-login in order to create the user
        object'''
        user = User(user_id)
        g.user = user

        cur = mysql.connect.cursor()

        cur.execute(
            '''UPDATE users SET confirmed_at=NOW() WHERE user_id = %s''',
            (user_id,)
        )

        mysql.connect.commit()

        return user

    # Set index page
    @app.route('/')
    def index():
        return redirect(url_for('scheduling.index'))
    app.add_url_rule('/', endpoint='index')

    # Add all blueprints
    app.register_blueprint(auth.bp)
    app.register_blueprint(scheduling.bp)
    app.register_blueprint(manage.bp)

    return app
