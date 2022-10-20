########################################################################################
#################################### autosearch.py #####################################
############## Handles all functions related to the autosearch section #################
########################## automate google custom search jobs ##########################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from unittest import result
from flask import Blueprint, render_template, redirect, request, flash
# from numpy import int256
from .db import get_db
from .common import logAction, getTracksFromPlaylist, getTrackInfo, googleSearchApiRequest, extractItemsFromGoogleResponse, checkIfTracksInPlaylist
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
    
    try:

        '''--> initialize variables'''
        dbTrackIDs              = []        #used only for comparison
        playlistTrackIDs        = []        #used only for comparison
        global gv_actdbTracks


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

                cursor.execute('INSERT INTO ToAnalyzeTracks (id, album, artists, title, href, times_searched) VALUES (?,?,?,?,?,?)',(playlistTrack["id"], track_info["album"], ', '.join(track_info["artists"]), track_info["title"], track_info["href"], 0))
                get_db().commit()
                logAction("msg - autosearch.py - syncToAnalyzeTracks() 40 --> Added track " + playlistTrack["id"] + " to ToAnalyzeTracks db.")

        for dbTrack in gv_actdbTracks:
            #deleted tracks?
            if not dbTrack["id"] in playlistTrackIDs:
                #db track not in playlist --> remove from db
                cursor.execute('DELETE FROM ToAnalyzeTracks WHERE id = ?', (dbTrack["id"],))
                get_db().commit()
                logAction("msg - autosearch.py - syncToAnalyzeTracks() 50 --> Removed track " + dbTrack["id"] + " from ToAnalyzeTracks db.")
        
        '''--> update act list one more time'''
        gv_actdbTracks          = []
        for item in cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall():
            gv_actdbTracks.append({"id": item["id"], "title": item["title"], "artists": item["artists"], "times_searched": item["times_searched"]})

        '''--> perform search job'''
        i1                      = 0
        i2                      = 0
        item1                   = {}
        item1_timessearched     = 0
        item2                   = ""
        times_counter           = 0
        search_string           = ""
        gcs_response            = ""
        gcs_result              = []

        for i1 in range(0, len(gv_actdbTracks)):
            item1       = gv_actdbTracks[i1]    

            if (item1["times_searched"] == None):
                #value not initialized yet
                item1_timessearched     = i1 + 1
            else:
                if int(item1["times_searched"]) <= i1:
                    #this should be prevented at all time
                    item1_timessearched     = i1 + 1
                else:
                    #normal situation, get value from db
                    item1_timessearched     = int(item1["times_searched"])

            times_counter   = item1_timessearched

            if item1_timessearched < len(gv_actdbTracks):
                #for this track, not all searches have been performed yet
                for i2 in range(item1_timessearched, len(gv_actdbTracks)):
                    item2       = gv_actdbTracks[i2]

                    '''--> create searchstring'''
                    search_string = item1["artists"] + " " + item1["title"] + " " + item2["artists"] + " " + item2["title"]
                    logAction("msg - autosearch.py - syncToAnalyzeTracks() 70 --> start google search job for searchterm: " + str(search_string) + ", i1=" + str(i1) + ", i2=" +str(i2) + ", item1_timessearched=" + str(item1_timessearched) + ".")
            

                    '''--> actual search job'''
                    gcs_response      = googleSearchApiRequest(search_string, startIndex = 0)

                    gcs_result        = extractItemsFromGoogleResponse(gcs_response, maxResults = 15)  #response: {"result": True/False, "response": list of playlistlinks, "message": ...}"


                    '''--> check response'''
                    if gcs_result["result"] == False:  
                        flash(gcs_result["message"], category="error")
                        raise Exception("Faulty response from extractItemsFromGoogleResponse: " + gcs_result["message"])

                    
                    '''--> check if found playlists contains 2 searched tracks'''
                    for playlist_link in gcs_result["response"]:

                        '''--> grab playlist ID from each link'''       
                        regexResult     = re.search("https:\/\/open.spotify.com\/playlist\/([a-zA-Z0-9]+)", playlist_link) 
                        playlistID      = regexResult.group(1)

                        playlist_tracks     = getTracksFromPlaylist(playlistID, False)
                        print("ITEM1: " + item1["id"] + ", ITEM: " + item2["id"])
                        response_check      = checkIfTracksInPlaylist([item1["id"], item2["id"]], playlist_tracks, False)

                        if response_check == True:
                            print("Playlist " + playlistID + " contains all tracks in list: " + str([item1["id"], item2["id"]]) + ".")
                        else:
                            print("Playlist " + playlistID + " does NOT contain all tracks in list: " + str([item1["id"], item2["id"]]) + ".")


                        #TODO 20221020 --> checkIfTracksInPlaylist uitvoeren met listInDetail op  True!
                        # syncToAnalyzeTracks() opsplitsen, is te lang
                        # eventueel getTrackInfo() updaten, zodat extra key in response dict wordt teruggegeven: lijst met per artiestnaam van dat nummer een dict {"artistName": , "artistID": }
                        # kan gebruikt worden om artiesten met eenzelfde naam te onderscheiden adhv artiest ID! Eventueel met terugwerkende kracht in discover.py,...


                    
    except Exception as ex:
        logAction("err - autosearch.py - syncToAnalyzeTracks() 100 --> error while performing autosearch --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        flash("Error performing autosearch job. See log for details.", category="error")

########################################################################################