########################################################################################
###################################### create.py #######################################
################ Handles all functions related to the create section ###################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from flask import Blueprint, render_template, redirect, request, flash, current_app
from .common import addTracksToPlaylist, apiGetSpotify, changePlaylistDetails, checkIfTrackInDB, getTracksFromArtist, getTracksFromPlaylist, searchSpotify, getTrackInfo, createPlaylist, waitForGivenTimeIns, logAction, createPlaylistDescription, checkSourceAndCreatePlaylist, checkIfTracksInPlaylist, getDBTracks
from .db import get_db
import json
import re
from datetime import datetime
import traceback

from flask_socketio import emit

# from urllib import response

# from pip._vendor import requests

# from pip._vendor import urllib3
# import time

# from . import globalvariables

# from . import gv_socketio
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)      
# #https://www.codegrepper.com/code-examples/python/InsecureRequestWarning%3A+Unverified+HTTPS+request+is+being+made+to+host
########################################################################################


########################################################################################
######################################## FLASK INIT ####################################
########################################################################################
bp_create = Blueprint('create', __name__, url_prefix="/create")
########################################################################################


########################################################################################
######################################## VARIABLES #####################################
########################################################################################
gv_suggestedPlaylistName        = "sport_create_playlist_" + str(datetime.now().year)  + str(datetime.now().month) + str(datetime.now().day) + "_" + str(datetime.now().hour) + str(datetime.now().minute) + "_"
gv_noOfTracksRequested          = 0
gv_givenPlaylistName            = ""
gv_checkboxMoveToListenedDB     = False
gv_ToListenTracks               = []


########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
# HTML ROUTING #
@bp_create.route("/", methods=["GET","POST"])
def create_main():
    '''--> main routine'''
    '''--> initialize gloval variables'''
    global gv_suggestedPlaylistName
    global gv_noOfTracksRequested          
    global gv_givenPlaylistName    
    global gv_checkboxMoveToListenedDB  
    global gv_ToListenTracks      


    '''--> read query parameters'''
    args=request.args      


    #--> PAGE LOAD #
    if request.method == "GET":
        '''--> return html'''
        return render_template("create.html",
                                suggestedPlaylistName = gv_suggestedPlaylistName)

    
    elif (request.method == "POST") and ("frm_create_playlist_from_db" in request.form) and not ("frm_create_playlist_from_id" in request.form):
        '''--> tracks from ToListenDB'''

        try:
            '''--> initialize variables'''
            createPlaylistResponse          = {}
            addTracksResponse               = {}
            gv_ToListenTracks               = []


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> retrieve user input'''
            gv_noOfTracksRequested          = int(request.form["input_total"])
            gv_givenPlaylistName            = request.form["input_name"]    
            gv_checkboxMoveToListenedDB     = request.form.get("moveToListeneddb")      #checkbox value 'Move tracks to Listened DB'


            '''--> log'''
            logAction("msg - create.py - create_main tracks from DB --> create playlist from ToListen DB - button press.")


            '''--> get list with requested number of tracks in ToListen db'''
            resultList       = cursor.execute('SELECT * FROM ToListenTrack').fetchmany(size=gv_noOfTracksRequested)        #https://docs.python.org/3/library/sqlite3.html

            for item in resultList:
                gv_ToListenTracks.append(item["id"])

            if len(gv_ToListenTracks) == 0:
                logAction("err - create.py - create_main tracks from DB 5 --> No tracks in ToListeNDB.")
                raise TypeError("No tracks in ToListenDB.")


            '''--> create playlist, check response'''
            createPlaylistResponse      = createPlaylist(gv_givenPlaylistName , "Generated by spotr. contains " + str(len(gv_ToListenTracks) + " tracks from 'ToListenTrack' database."))        #returns dict {result: True/false, response: {playlistid: }, message:...}

            if createPlaylistResponse["result"] == False:
                logAction("err - create.py - create_main tracks from DB 20 --> Negative feedback from createPlaylist: " + createPlaylistResponse["message"])
                raise Exception(createPlaylistResponse["message"])

                
            '''--> add tracks to newly created playlist, check response'''
            addTracksResponse           = addTracksToPlaylist(createPlaylistResponse["response"]["playlistid"], gv_ToListenTracks)

            if addTracksResponse["result"] == False:
                logAction("err - create.py - create_main tracks from DB 30 --> Negative feedback from addTracksToPlaylist: " + addTracksResponse["message"])
                raise Exception(addTracksResponse["message"])


            '''--> remove tracks from ToListenTrack, add tracks to ListenedTrack'''
            for trackID in gv_ToListenTracks:
                cursor.execute('DELETE FROM ToListenTrack WHERE id = ?', (trackID,))
                get_db().commit()

                '''--> get track info'''
                trackInfo       = getTrackInfo(trackID, True)

                cursor.execute(
                        'INSERT INTO ListenedTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?)', 
                        (trackID, trackID, trackInfo["album"], ', '.join(trackInfo["artists"]), trackInfo["title"], trackInfo["href"], trackInfo["popularity"], "False", 0)
                    )
                get_db().commit()


            '''--> log '''
            logAction("msg - create.py - create_main tracks from DB 50 --> Succesfully created playlist " + gv_givenPlaylistName + " with " + str(len(gv_ToListenTracks)) + " tracks from ToListenTrack db.")
            flash("Succesfully created playlist " + gv_givenPlaylistName + " with " + str(len(gv_ToListenTracks)) + " tracks from ToListenTrack db.", category="message")


            '''--> return html'''
            return render_template("create.html",
                                suggestedPlaylistName = gv_suggestedPlaylistName)

            
        except TypeError:
            flash("No tracks in ToListenDB.", category="message")

            '''--> return html'''
            return render_template("create.html",
                                suggestedPlaylistName = gv_suggestedPlaylistName)

        except Exception as ex:
            logAction("err - create.py - create_main tracks from DB 100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error creating playlist with tracks from ToListenDB. See log for details.", category="error")

            '''--> return html'''
            return render_template("create.html",
                                suggestedPlaylistName = gv_suggestedPlaylistName)
     
      #TODO20221011 -   Playlist descriptions, ook bij discover.py?
      #error afhandeling bij ingave valse playlistID - nu wordt gewoon lege lijst teruggegeven? Ook dict in return steken zoals bij createPLaylist?


    elif (request.method == "POST") and ("frm_create_playlist_from_id" in request.form) and not ("frm_create_playlist_from_db" in request.form):
        '''--> tracks from given playlistID'''

        try:
            '''--> initialize variables'''
            playlistTracks                  = ""
            createPlaylistResponse          = {}
            addTracksResponse               = {}
            playlistID                      = ""
            gv_ToListenTracks               = []


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> retrieve user input'''
            gv_givenPlaylistName            = request.form["input_name"]    
            gv_checkboxMoveToListenedDB     = request.form.get("moveToListeneddb")      #checkbox value 'Move tracks to Listened DB'
            playlistID                      = request.form["input_playlistid"]


            '''--> log'''
            logAction("msg - create.py - create_main tracks from playlist ID --> create playlist from another playlist's tracks - button press.")


            '''--> get playlis's tracks'''
            tracksList                      = []
            tracksList                      = getTracksFromPlaylist(playlistID, True)       #list of {id: trackid, artists: list with artists, title: title}


            '''--> check tracks'''
            response        = getDBTracks("ListenedTrack")
            response2       = getDBTracks("ToListenTrack")
            response3       = getDBTracks("WatchListNewTracks")
            dbTracks        = []

            if (response["result"] == True) and (response2["result"] == True) and (response3["result"] == True):
                dbTracks    = response["response"].copy()
                dbTracks.extend(response2["response"])
                dbTracks.extend(response3["response"])
                logAction("msg - create.py - create_main tracks from playlist ID 5 --> " + response["message"] + ", " + response2["message"] + ", " + response3["message"])
            else:
                logAction("err - create.py - create_main tracks from playlist ID 7 --> " + response["message"] + ", " + response2["message"] + ", " + response3["message"])
                raise Exception("No valid trackID list received from DB.")


            for item in tracksList:
                if not item["id"] in dbTracks:
                    gv_ToListenTracks.append(item["id"])

                    '''--> Add tracks to ListenedTrack'''
                    '''--> get track info'''
                    trackInfo       = getTrackInfo(item["id"], True)

                    cursor.execute(
                            'INSERT INTO ListenedTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?)', 
                            (item["id"], item["id"], trackInfo["album"], ', '.join(trackInfo["artists"]), trackInfo["title"], trackInfo["href"], trackInfo["popularity"], "False", 0)
                        )
                    get_db().commit()


            '''--> remove duplicates (if any) from list'''
            gv_ToListenTracks = list(dict.fromkeys(gv_ToListenTracks))

           
            '''--> check for empty list'''
            if len(gv_ToListenTracks) == 0:
                logAction("err - create.py - create_main tracks from playlist ID 10 --> No tracks in given playlist " + playlistID + ".")
                raise TypeError("No tracks in given playlist " + playlistID + ".")


            '''--> get source playlist name'''
            playlistName         = ""
            playlistName         = apiGetSpotify("playlists/" + playlistID)["name"]


            '''--> create playlist, check response'''
            createPlaylistResponse      = createPlaylist(gv_givenPlaylistName , "Generated by spotr. contains " + str(len(gv_ToListenTracks) + " tracks from playlist '" + playlistName + "'. Original playlist contains " + str(len(tracksList))) + ".")        #returns dict {result: True/false, response: {playlistid: }, message:...}

            if createPlaylistResponse["result"] == False:
                logAction("err - create.py - create_main tracks from playlist ID 20 --> Negative feedback from createPlaylist: " + createPlaylistResponse["message"])
                raise Exception(createPlaylistResponse["message"])

                
            '''--> add tracks to newly created playlist, check response'''
            addTracksResponse           = addTracksToPlaylist(createPlaylistResponse["response"]["playlistid"], gv_ToListenTracks)

            if addTracksResponse["result"] == False:
                logAction("err - create.py - create_main tracks from playlist ID 30 --> Negative feedback from addTracksToPlaylist: " + addTracksResponse["message"])
                raise Exception(addTracksResponse["message"])


            '''--> log'''
            logAction("msg - create.py - create_main tracks from playlist ID 50 --> Succesfully added " + str(len(gv_ToListenTracks)) + " tracks from playlist " + playlistName + " to new playlist.")
            flash("Succesfully added " + str(len(gv_ToListenTracks)) + " tracks from playlist " + playlistName + " to new playlist.", category="message")


            '''--> return html'''
            return render_template("create.html",
                                suggestedPlaylistName = gv_suggestedPlaylistName)


        except TypeError:
            flash("No tracks in given playlist.", category="message")

            '''--> return html'''
            return render_template("create.html",
                                suggestedPlaylistName = gv_suggestedPlaylistName)


        except Exception as ex:
            logAction("err - create.py - create_main tracks from playlistID 100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error creating playlist with tracks from given playlist ID. See log for details.", category="error")

            '''--> return html'''
            return render_template("create.html",
                                suggestedPlaylistName = gv_suggestedPlaylistName)
    
