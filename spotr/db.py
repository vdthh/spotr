########################################################################################
######################################### db.py ########################################
######################### db-related functions and procedures ##########################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
############# https://flask.palletsprojects.com/en/2.1.x/tutorial/factory/ #############
#################### https://www.digitalocean.com/community/tutorials/ #################
################# how-to-use-an-sqlite-database-in-a-flask-application #################
########################################################################################
import sqlite3
import click
from flask import current_app, g
########################################################################################


########################################################################################
###################################### CONNECTION ######################################
########################################################################################
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types = sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()
########################################################################################


########################################################################################
######################################### DATA #########################################
########################################################################################
'''--> Calling this will delete all current data stored in database.db!!!'''
def init_db():
    db = get_db()

    #open and reas 'schema.sql'
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


'''--> make init_db() callable via cli'''
@click.command('init-db')   #command line command
def init_db_command():
    #clears existing data and creates new tables
    init_db()
    click.echo('database is initialized!')
########################################################################################


########################################################################################
############################### APPLICATION REGISTRATION ###############################
########################################################################################
'''--> register with the application interface by calling this in __init__'''
def init_app(app):
    #execute after response returning
    app.teardown_appcontext(close_db)
    #'init_db_command' becomes accessible via cli:
    app.cli.add_command(init_db_command)

########################################################################################