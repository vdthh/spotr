########################################################################################
#################################### autosearch.py #####################################
############## Handles all functions related to the autosearch section #################
########################## automate google custom search jobs ##########################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from flask import Blueprint, render_template, redirect, request, flash
from .db import get_db
from .common import logAction
import traceback
from datetime import datetime
import json
import re
########################################################################################


########################################################################################
######################################## FLASK INIT ####################################
########################################################################################
bp_autosearch = Blueprint('autosearch', __name__, url_prefix="/autosearch")
########################################################################################


########################################################################################
######################################## VARIABLES #####################################
########################################################################################


########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
# HTML ROUTING #
@bp_autosearch.route("/", methods=["GET","POST"])
def autosearch_main():
    '''--> main routine'''
    '''--> initialize gloval variables'''
    global gv_suggestedPlaylistName


    '''--> read query parameters'''
    args=request.args      


    #--> PAGE LOAD #
    if request.method == "GET":
        '''--> db'''
        cursor = get_db().cursor()

        '''--> return html'''
        logAction("msg - autosearch.py - autosearch_main load page --> autosearch.html page loaded.")

        return render_template('autosearch.html', likedTracksList = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall())


########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
def syncToAnalyzeTracks():
    '''--> synchronize tracks in db with playlist'''
    '''--> source is spotify playlist 'spotr_toAnalyze' '''
    '''--> target is 'ToAnalyzeTracks' db table'''
    
    '''--> initialize variables'''
    db_tracks       = []
    act_tracks      = []

    
########################################################################################