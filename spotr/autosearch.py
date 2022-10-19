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
from .common import logAction, getTracksFromPlaylist, getTrackInfo
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
gv_actdbTracks                  = []                        #list of {"id": , "title": , "artists": , "times_searched": }
gv_actPlaylistTracks            = []                        #list of {"id": , "title": , "artists": , "times_searched": }
gv_playlistToAnalyseID          = "4wC748pDf0gHnJRFyzb4l9"

########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
# HTML ROUTING #
@bp_autosearch.route("/", methods=["GET","POST"])
def autosearch_main():
    '''--> main routine'''
    '''--> initialize gloval variables'''
    global gv_actdbTracks
    global gv_actPlaylistTracks
    global gv_playlistToAnalyseID


    '''--> read query parameters'''
    args=request.args      


    #--> PAGE LOAD #
    if request.method == "GET":
        '''--> db'''
        cursor = get_db().cursor()

        syncToAnalyzeTracks()

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

    '''--> log'''
    logAction("msg - autosearch.py - syncToAnalyzeTracks()  --> Started")
    
    '''--> initialize variables'''
    dbTrackIDs              = []        #used only for comparison
    playlistTrackIDs        = []        #used only for comparison


    '''--> db'''
    cursor = get_db().cursor()


    '''--> db tracks'''
    for item in cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall():
        gv_actdbTracks.append({"id": item["id"], "title": item["title"], "artists": item["artists"], "times_searched": item["times_searched"]})
        dbTrackIDs.append(item["id"])


    '''--> actual spotr_toAnalyze-playlist tracks'''
    gv_actPlaylistTracks        = getTracksFromPlaylist(gv_playlistToAnalyseID, True)   # returns list of {id: trackid, artists: list with artists, title: title}
    for track in gv_actPlaylistTracks:
        playlistTrackIDs.append(track["id"])


    '''--> synchronize playlist/db'''
    for playlistTrack in gv_actPlaylistTracks:
        #added tracks?
        if not playlistTrack["id"] in dbTrackIDs:
            #playlist track not in db --> save to db

            '''--> track info'''
            track_info = getTrackInfo(playlistTrack["id"], True)        #{"trackid": string, "title": string, "artists": list of string, "album": string, "href": string, "popularity": string}

            cursor.execute('INSERT INTO ToAnalyzeTracks (id, album, artists, title, href, times_searched) VALUES (?,?,?,?,?,?)',(playlistTrack["id"], track_info["album"], track_info["artists"], track_info["title"], track_info["href"], 0))
            get_db().commit()
            logAction("msg - autosearch.py - syncToAnalyzeTracks() 40 --> Added track " + track_info["title"] + " to ToAnalyzeTracks db.")

    for dbTrack in gv_actdbTracks:
        #deleted tracks?
        if not dbTrack["id"] in playlistTrackIDs:
            #db track not in playlist --> remove from db
            cursor.execute('DELETE FROM ToAnalyzeTracks WHERE id = ?', (dbTrack["id"],))
            get_db().commit()
            logAction("msg - autosearch.py - syncToAnalyzeTracks() 50 --> Removed track " + track_info["title"] + " from ToAnalyzeTracks db.")
    
########################################################################################