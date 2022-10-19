########################################################################################
###################################### __init__.py #####################################
##### 'The __init__.py serves double duty: it will contain the application factory, ####
##### and it tells Python that the flaskr directory should be treated as a package' ####
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from flask import Flask
import os
from . import db, globalvariables
from urllib3 import logging #Removes request warnings from console
from flask_socketio import SocketIO
########################################################################################

gv_socketio = SocketIO(logger=True, engineio_logger=True)

########################################################################################
################################## APPLICATION FACTORY #################################
########################################################################################
'''--> disable insecurewarnings'''
 #disable insecurewarnings in terminal when performing api requests without certificate: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings
logging.captureWarnings(True)

def create_app():
    #instance_relative_config=True --> instance folder is located outside of main (in this case 'spotr') folder.
    app = Flask(__name__, instance_relative_config=True)

    #default configuration settings. 'spotr.sqlite' will be located in instance folder.
    app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'spotr.sqlite'),
    )

    #overrides default configuration with values written in 'config.py'.
    app.config.from_pyfile('config.py', silent=True)

    #initialize plugins
    globalvariables.init()

    #socketio extension
    # gv_socketio = SocketIO()
    gv_socketio.init_app(app)

    #instance folder exists?
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    #register 'close_db' and 'init_db_command' with application instance
    db.init_app(app)

    with app.app_context():
        app.gv_socketio = gv_socketio

        #register blueprint(s)
        from . import watchlist, home, database, search, everynoise, discover, create, _import, autosearch   #blueprints

        app.register_blueprint(watchlist.bp_watchlist)
        app.register_blueprint(home.bp_home)
        app.register_blueprint(database.bp_database)
        app.register_blueprint(search.bp_search)
        app.register_blueprint(everynoise.bp_everynoise)
        app.register_blueprint(discover.bp_discover)
        app.register_blueprint(create.bp_create)
        app.register_blueprint(_import.bp_import)
        app.register_blueprint(autosearch.bp_autosearch)

    return app
########################################################################################