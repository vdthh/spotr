########################################################################################
######################################## home.py #######################################
####################################### home page ######################################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from flask import Blueprint, render_template
########################################################################################


########################################################################################
######################################## FLASK INIT ####################################
########################################################################################
bp_home = Blueprint('home', __name__, url_prefix="")
########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
@bp_home.route("/")
def home_main():
    return render_template("home.html")
########################################################################################