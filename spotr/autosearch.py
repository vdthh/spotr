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
from .common import checkIfTrackInDB, logAction, getTracksFromPlaylist, getTrackInfo, googleSearchApiRequest, extractItemsFromGoogleResponse, checkIfTracksInPlaylist
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
                # logAction("msg - autosearch.py - syncToAnalyzeTracks() 40 --> Added track " + playlistTrack["id"] + " to ToAnalyzeTracks db.")

        for dbTrack in gv_actdbTracks:
            #deleted tracks?
            if not dbTrack["id"] in playlistTrackIDs:
                #db track not in playlist --> remove from db
                cursor.execute('DELETE FROM ToAnalyzeTracks WHERE id = ?', (dbTrack["id"],))
                get_db().commit()
                # logAction("msg - autosearch.py - syncToAnalyzeTracks() 50 --> Removed track " + dbTrack["id"] + " from ToAnalyzeTracks db.")
        
        '''--> finally, update act list'''
        gv_actdbTracks          = []
        for item in cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall():
            gv_actdbTracks.append({"id": item["id"], "title": item["title"], "artists": item["artists"], "times_searched": item["times_searched"]})


        '''--> search job'''
        searchJobResult         = searchForPlaylistsContainingTracks()

        if searchJobResult["result"] == True:
            print("FINISHED WITH SUCCESS!! FOUND " + str(len(searchJobResult["response"])) + " playlists.")
            '''--> add tracks from found playlists to ScrapedTracks db'''
            for playlist in searchJobResult["response"]:
                print("Playlist " + playlist["playlistid"])
                for track in getTracksFromPlaylist(playlist["playlistid"], False):
                    # print("TRACK FROM PLAYLIST: " + track)
                    track_info      = getTrackInfo(track, True)

                    '''--> check before add'''
                    if not checkIfTrackInDB(track, "ListenedTrack") and not checkIfTrackInDB(track, "ToListenTrack") and not checkIfTrackInDB(track, "ScrapedTracks"):
                        # print("TSJAKKE")
                        cursor.execute(
                                'INSERT INTO ScrapedTracks (id, album, artists, title, href, popularity, from_playlist, found_by_tracks) VALUES (?,?,?,?,?,?,?,?)', 
                                (track, track_info["album"], ', '.join(track_info["artists"]), track_info["title"], track_info["href"], track_info["popularity"], "False", 0)
                            )
                        get_db().commit()
                    else:
                        pass
                        # print("NOT TSJAKKA")

        else:
            print("FINISHED WITHOUT SUCCES")

                    
    except Exception as ex:
        logAction("err - autosearch.py - syncToAnalyzeTracks() 100 --> error while performing autosearch --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        flash("Error performing autosearch job. See log for details.", category="error")

                        #TODO 20221020 --> 
                        # syncToAnalyzeTracks() opsplitsen, is te lang
                        # eventueel getTrackInfo() updaten, zodat extra key in response dict wordt teruggegeven: lijst met per artiestnaam van dat nummer een dict {"artistName": , "artistID": }
                        # kan gebruikt worden om artiesten met eenzelfde naam te onderscheiden adhv artiest ID! Eventueel met terugwerkende kracht in discover.py,...

########################################################################################


########################################################################################
########################################################################################
def searchForPlaylistsContainingTracks():
    '''--> search for playlists that contain tracks from toAnalyzeTracks db'''
    '''--> 2 tracks are being searched for each time'''
    '''--> so a valid playlist contains at least 2 tracks of toAnalyzeTracks db'''
    '''--> returns the following dict: {"result": True/False, "message": e.g. "Found 10 playlists.", "response": list of {"playlistid": ,"trackid1": ,"trackid2":}}'''
    '''--> '''

    '''--> initialize variables'''
    resultSuccess           = False
    resultMessage           = ""
    resultResponse          = []
    i1                      = 0
    i2                      = 0
    item1                   = {}
    item1_timessearched     = 0
    item2                   = ""
    times_counter           = 0
    search_string           = ""
    gcs_response            = ""
    gcs_result              = []
    playlist_tracks         = []

    logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 0 --> Started.")

    try:
        '''--> check source'''
        if len(gv_actdbTracks) == 0:
            #leave
            logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 10 --> Source tracklist contains 0 tracks.")
            resultSuccess       = False
            resultMessage       = "Source tracklist has no tracks."
            toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
            return toReturn


        '''--> perform search job'''
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
                    logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 20 --> start google search job for searchterm: " + str(search_string) + ", i1=" + str(i1) + ", i2=" +str(i2) + ", item1_timessearched=" + str(item1_timessearched) + ".")
                    print("start google search job for searchterm: " + str(search_string) + ", i1=" + str(i1) + ", i2=" +str(i2) + ", item1_timessearched=" + str(item1_timessearched) + ".")

                    '''--> actual search job'''
                    gcs_response      = googleSearchApiRequest(search_string, startIndex = 0)
                    gcs_result        = extractItemsFromGoogleResponse(gcs_response, maxResults = 15)  #response: {"result": True/False, "response": list of playlistlinks, "message": ...}"


                    '''--> check response'''
                    if gcs_result["result"] == False:  
                        #leave
                        logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 10 --> Bad response from gcs: " + gcs_result["message"])
                        resultSuccess       = False
                        resultMessage       = "Bad response from gcs. See log for details."
                        toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
                        return toReturn

                    
                    '''--> check if found playlists contains the 2 searched tracks'''
                    for playlist_link in gcs_result["response"]:

                        '''--> grab playlist ID from each link'''       
                        regexResult     = re.search("https:\/\/open.spotify.com\/playlist\/([a-zA-Z0-9]+)", playlist_link) 
                        playlistID      = regexResult.group(1)

                        '''--> get playlist tracks + check'''
                        playlist_tracks     = getTracksFromPlaylist(playlistID, True)
                        response_check      = checkIfTracksInPlaylist([item1["id"], item2["id"]], playlist_tracks, True)

                        if response_check == True:
                            #playlists contains the 2 tracks
                            print("Playlist " + playlistID + " contains all tracks in list: " + str([item1["id"], item2["id"]]) + ".")
                            resultResponse.append({"playlistid": playlistID, "trackid1": item1["id"], "trackid2": item2["id"]})

                        else:
                            #playlists does not contain both tracks
                            print("Playlist " + playlistID + " does NOT contain all tracks in list: " + str([item1["id"], item2["id"]]) + ".")


                    '''--> increase times_searched value for item1 and save'''
                    times_counter       +=1
                    get_db().execute('UPDATE ToAnalyzeTracks SET times_searched=? WHERE id=?',(times_counter, item1["id"]))
                    get_db().commit()


        '''--> finished, return response'''
        resultSuccess       = True
        resultMessage       = "Finished searchForPlaylistsContainingTracks()."
        toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}  
        return toReturn   


    except Exception as ex:
        logAction("err - common.py - searchForPlaylistsContainingTracks() --> error while performing: " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())

        resultSuccess       = False
        resultMessage       = "Error while performing searchForPlaylistsContainingTracks(). See log for details"
        toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
        return toReturn
