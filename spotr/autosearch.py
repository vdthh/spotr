########################################################################################
#################################### autosearch.py #####################################
############## Handles all functions related to the autosearch section #################
########################## automate google custom search jobs ##########################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from unittest import result
from urllib import response
from flask import Blueprint, render_template, redirect, request, flash
# from numpy import int256
from .db import get_db
from .common import checkIfTrackInDB, logAction, getTracksFromPlaylist, getTrackInfo, googleSearchApiRequest, extractItemsFromGoogleResponse, checkIfTracksInPlaylist, checkIfTrackInDB_test, apiGetSpotify, createPlaylist, addTracksToPlaylist
from .watchlist import checkWatchlistItems
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
gv_searchResults                = []                        #list of {"playlistid":, "foundbytrack1":, "foundbytrack2":...}

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
    global gv_searchResults


    '''--> read query parameters'''
    args=request.args      


    #--> PAGE LOAD #
    if request.method == "GET" and not ("addTracksToDb" in args) and not ("createCopyOfPlaylist" in args):
        '''--> page load'''

        '''--> db'''
        cursor = get_db().cursor()


        '''--> refresh ToAnalyzeTracks db'''
        syncToAnalyzeTracks()

        '''--> return html'''
        logAction("msg - autosearch.py - autosearch_main load page --> autosearch.html page loaded.")
        return render_template('autosearch.html', 
                                likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                searchResult            = gv_searchResults)

    elif request.method == "GET" and ("addTracksToDb" in args) and not ("createCopyOfPlaylist" in args):
        '''--> add playlist tracks to ScrapedTracks db - button press'''
        try:
            '''--> initialize variables'''
            getPlaylistTracksResponse       = []        #list of track IDs
            track_count                     = 0 


            '''--> Get user input'''
            playlistID = args["addTracksToDb"]


            '''--> playlist tracks'''
            getPlaylistTracksResponse       = getTracksFromPlaylist(playlistID, False)      #returns list with track IDs


            '''--> check response'''
            if getPlaylistTracksResponse == "":
                logAction("err - autosearch.py - addTracksToDb 10 --> Faulty response from getTracksFromPlaylist().")
                flash("Faulty response from getTracksFromPlaylist().", category="error")
                raise Exception("Faulty response from getTracksFromPlaylist().")


            '''--> add tracks to db'''
            for track in getPlaylistTracksResponse:
                track_count     +=1
                track_info      = getTrackInfo(track, True)

                '''--> check before add'''
                if not checkIfTrackInDB_test(track, ["ListenedTrack", "ToListenTrack", "ScrapedTracks"]):
                    #not in db yet, add
                    get_db().execute(
                            'INSERT INTO ScrapedTracks (id, album, artists, title, href, popularity, from_playlist, found_by_tracks) VALUES (?,?,?,?,?,?,?,?)', 
                            (track, track_info["album"], ', '.join(track_info["artists"]), track_info["title"], track_info["href"], track_info["popularity"], "False", 0)
                        )
                    get_db().commit()

                else: 
                    #in db, don't add
                    pass


            '''--> return html'''
            logAction("msg - autosearch.py - addTracksToDb 20 --> Finished, added " + str(track_count) + " tracks to ScrapedTracks db.")
            return render_template('autosearch.html', 
                                    likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                    searchResult            = gv_searchResults)


        except Exception as ex:
            logAction("err - autosearch.py - addTracksToDb 100 --> error while adding playlist tracks to ScrapedTracks db --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error while adding playlist tracks to ScrapedTracks db. See log for details.", category="error")

            return render_template('autosearch.html', 
                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                        searchResult            = gv_searchResults)

    elif request.method == "GET" and ("createCopyOfPlaylist" in args) and not ("addTracksToDb" in args):
        '''--> create playlist of found playlist (copy) - button press'''
        try:
            '''--> initialize variables'''
            noAddedTracks               = 0
            tracksToCopy                = []        #track IDs
            createPlaylistResponse      = {}
            addTracksResponse           = {}
            getPlaylistTracksResponse   = []
            playlistName                = ""
            track_count                 = 0
            playlist_description        = ""
            found_by_track1             = ""
            found_by_track2             = ""


            '''--> Get user input'''
            playlistID          = args["createCopyOfPlaylist"]
            found_by_track1     = args["foundbytrack1"]
            found_by_track2     = args["foundbytrack2"]


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> playlist tracks'''
            getPlaylistTracksResponse       = getTracksFromPlaylist(playlistID, False)      #returns list with track IDs


            '''--> check response'''
            if getPlaylistTracksResponse == "":
                logAction("err - autosearch.py - createCopyOfPlaylist 10 --> Faulty response from getTracksFromPlaylist().")
                flash("Faulty response from getTracksFromPlaylist().", category="error")
                raise Exception("Faulty response from getTracksFromPlaylist().")


            '''--> create list with checked tracks'''
            for track in getPlaylistTracksResponse:
                track_count     +=1
                track_info      = getTrackInfo(track, True)

                '''--> check before add'''
                if not checkIfTrackInDB_test(track, ["ListenedTrack", "ToListenTrack", "ScrapedTracks"]):
                    #not in db yet
                    tracksToCopy.append(track)

                    '''--> add tracks to ListenedTrack db'''
                    cursor.execute(
                        'INSERT INTO ListenedTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?)', 
                        (track, track, track_info["album"], ', '.join(track_info["artists"]), track_info["title"], track_info["href"], track_info["popularity"], playlistID, 0)
                    )
                    get_db().commit()
                    noAddedTracks       = noAddedTracks + 1

                else: 
                    #in db, don't add
                    pass


            '''--> get source playlist name'''
            playlistName         = apiGetSpotify("playlists/" + playlistID)["response"]["name"]     #returns {"result": True/False, "response": json response, "message": ...}


            '''--> check if any tracks in tocopylist'''
            print("LENGTH: " + str(len(tracksToCopy)))
            if len(tracksToCopy) == 0:
                print("LENGTH2: " + str(len(tracksToCopy)))
                logAction("err - autosearch.py - createCopyOfPlaylist 30 --> No (unlistened) tracks found in playlist " + playlistName + ".")
                raise TypeError ("No (unlistened) tracks found in playlist " + playlistName + ".")


            '''--> create new empty playlist + check response'''
            playlist_description        = "created by spotr. Copy of playlist \"" + playlistName + "\", found by tracks " + found_by_track1 + " and " + found_by_track2 + "."
            createPlaylistResponse      = createPlaylist("spotr_copyOfPlaylist_" + playlistName, playlist_description)        #returns dict {result: True/false, response: {playlistid: }, message:...}

            if createPlaylistResponse["result"] == False:
                logAction("err - autosearch.py - createCopyOfPlaylist 90 --> Negative feedback from createPlaylist: " + createPlaylistResponse["message"])
                raise Exception(createPlaylistResponse["message"])


            '''--> add tracks to newly created playlist + check response'''
            addTracksResponse       = addTracksToPlaylist(createPlaylistResponse["response"]["playlistid"], tracksToCopy)

            if addTracksResponse["result"] == False:
                logAction("err - autosearch.py - createCopyOfPlaylist 100 --> Negative feedback from addTracksToPlaylist: " + addTracksResponse["message"])
                raise Exception(addTracksResponse["message"])


            '''--> log'''
            logAction("msg - autosearch.py - createCopyOfPlaylist 50 --> Succesfully added " + str(noAddedTracks) + " tracks from playlist " + playlistName + " to new playlist.")
            flash("Succesfully added " + str(noAddedTracks) + " tracks from playlist " + playlistName + " to new playlist.", category="message")


            '''--> return html'''
            logAction("msg - autosearch.py - createCopyOfPlaylist 20 --> Succesfully added " + str(noAddedTracks) + " tracks from playlist " + playlistName + " to new playlist.")
            return render_template('autosearch.html', 
                                    likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                    searchResult            = gv_searchResults)


        except TypeError:
            print("LENGTH3: " + str(len(tracksToCopy)))
            logAction("msg - autosearch.py - createCopyOfPlaylist 99 --> No (unlistened) tracks found in playlist " + playlistName + ".")
            flash("No (unlistened) tracks found in playlist " + playlistName + ".", category="message")

            return render_template('autosearch.html', 
            likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
            searchResult            = gv_searchResults)


        except Exception as ex:
            logAction("err - autosearch.py - createCopyOfPlaylist 100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error copying playlist tracks to new playlist. See log for details.", category="error")

            return render_template('autosearch.html', 
                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                        searchResult            = gv_searchResults)


########################################################################################
@bp_autosearch.route('/startSearchJob', methods=['GET', 'POST'])
def autosearch_startSearchJob():
        '''--> search for playlists with tracks from ToAnalyzeTracks'''
        logAction("msg - autosearch.py - autosearch_main start searchjob --> manually initiated, starting searchForPlaylistsContainingTracks().")

        '''--> initialize variables'''
        response        = {}
        global gv_searchResults


        '''--> db'''
        cursor = get_db().cursor()


        '''--> call'''
        response        = searchForPlaylistsContainingTracks(15)  # {"result": True/False, "message": e.g. "Found 10 playlists.", "response": list of {"playlistid":, "foundbytrack1":, "foundbytrack2":, "nooftracks":...}


        '''--> check response'''
        if response["result"] == False:
            logAction("err - autosearch.py - autosearch_main start searchjob 100 --> error while performing searchForPlaylistsContainingTracks().")
            flash("error while performing searchForPlaylistsContainingTracks(). See log for details.", category="error")
            return render_template('autosearch.html', 
                                    likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                    searchResult            = gv_searchResults)


        '''--> update gv'''
        gv_searchResults        = response["response"]


        '''--> return html'''
        logAction("msg - autosearch.py - autosearch_main start searchjob 150 --> finished searchForPlaylistsContainingTracks()! Found " + str(len(response["response"])) + " playlists.")
        flash("Finished searchForPlaylistsContainingTracks()! Found " + str(len(response["response"])) + " playlists.", category="message")
        return render_template('autosearch.html', 
                                likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                searchResult            = gv_searchResults)

########################################################################################
########################################################################################
@bp_autosearch.route('/startAutosearchJob', methods=['GET', 'POST'])
def autosearch_startAutosearchJob():
        '''--> start autosearch for playlists with tracks from ToAnalyzeTracks'''
        logAction("msg - autosearch.py - autosearch_main start autosearchjob --> automatically initiated, starting searchForPlaylistsContainingTracks().")

        try:
            '''--> initialize variables'''
            response                = {}
            playlistName            = ""
            count_new_playlists     = 0


            '''--> db'''
            cursor = get_db().cursor()


            '''--> call'''
            response        = searchForPlaylistsContainingTracks(15)  # {"result": True/False, "message": e.g. "Found 10 playlists.", "response": list of {"playlistid":, "foundbytrack1":, "foundbytrack2":, "nooftracks":...}


            '''--> check response'''
            if response["result"] == False:
                logAction("err - autosearch.py - autosearch_main start autosearchjob 100 --> error while performing searchForPlaylistsContainingTracks().")
                flash("error while performing auto triggered searchForPlaylistsContainingTracks(). See log for details.", category="error")
                return render_template('autosearch.html', 
                                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                        searchResult            = gv_searchResults)


            '''--> save results'''
            
            for entry in response["response"]:

                '''--> playlistName'''
                playlistName         = apiGetSpotify("playlists/" + entry["playlistid"])["response"]["name"]     #returns {"result": True/False, "response": json response, "message": ...}
                
                cursor.execute('SELECT * FROM ToAnalyzeResults WHERE playlistid=?', (entry["playlistid"],))
                if cursor.fetchone() == None:
                    cursor.execute(
                        'INSERT INTO ToAnalyzeResults (playlistid, foundbytrack1, foundbytrack2, name_) VALUES (?,?,?,?)', 
                        (entry["playlistid"], entry["foundbytrack1"], entry["foundbytrack2"], playlistName)
                    )
                    get_db().commit()

                    count_new_playlists     +=1

        except Exception as ex:
            logAction("err - autosearch.py - autosearch_main start autosearchjob 40 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error performing searchForPlaylistsContainingTracks(). See log for details.", category="error")
            return render_template('autosearch.html', 
                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                        searchResult            = gv_searchResults)


        '''--> check watchlist items'''
        try:
            if not checkWatchlistItems():
                #error
                logAction("err - autosearch.py - autosearch_main start autosearchjob 40 --> Faulty response from checkwatchlistItems.")
                flash("Faulty response from checkWatchlistItems(). See log for details.", category="error")
            else:
                #success
                logAction("msg - autosearch.py - autosearch_main start autosearchjob 45 --> Finished checkwatchlistItems() with success!.")
                
        except Exception as ex:
            logAction("err - autosearch.py - autosearch_main start autosearchjob 50 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error performing checkWatchlistItems(). See log for details.", category="error")
            return render_template('autosearch.html', 
                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                        searchResult            = gv_searchResults)


        '''--> return html'''
        logAction("msg - autosearch.py - autosearch_main start autosearchjob 150 --> finished searchForPlaylistsContainingTracks() and checkWatchlistItems! Found " + str(len(response["response"])) + " playlists, " + str(count_new_playlists) + " new playlists were saved.")
        flash("Finished searchForPlaylistsContainingTracks() and checkWatchlistItems! Found " + str(len(response["response"])) + " playlists, " + str(count_new_playlists) + " new playlists were saved.", category="message")
        return render_template('autosearch.html', 
                                likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                searchResult            = gv_searchResults)

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

                    
    except Exception as ex:
        logAction("err - autosearch.py - syncToAnalyzeTracks() 100 --> error while performing autosearch --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        flash("Error performing autosearch job. See log for details.", category="error")

########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
def searchForPlaylistsContainingTracks(maxResultsPerSearch):
    '''--> search for playlists that contain tracks from toAnalyzeTracks db'''
    '''--> 2 tracks are being searched for each time'''
    '''--> so a valid playlist contains at least 2 tracks of toAnalyzeTracks db'''
    '''--> returns the following dict: {"result": True/False, "message": e.g. "Found 10 playlists.", "response": list of {"playlistid":, "foundbytrack1":, "foundbytrack2": ,"nooftracks": }'''


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
    playlists_valid         = []
    playlist_tracks         = []
    track_count             = 0

    logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 0 --> Started.")

    try:
        '''--> check source'''
        if len(gv_actdbTracks) == 0:
            #leave
            logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 10 --> Source tracklist contains 0 tracks.")
            resultSuccess       = False
            resultMessage       = "Source tracklist has no tracks."
            toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
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
                    # print("start gcs for searchterm: " + str(search_string) + ", i1=" + str(i1) + ", i2=" +str(i2) + ", item1_timessearched=" + str(item1_timessearched) + ".")

                    '''--> actual search job'''
                    gcs_response      = googleSearchApiRequest(search_string, startIndex = 0)
                    gcs_result        = extractItemsFromGoogleResponse(gcs_response, maxResults = maxResultsPerSearch)  #response: {"result": True/False, "response": list of playlistlinks, "message": ...}"
                    

                    '''--> check response'''
                    if gcs_result["result"] == False:  
                        #leave
                        logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 10 --> Bad response from gcs: " + gcs_result["message"])
                        resultSuccess       = False
                        resultMessage       = "Bad response from gcs. See log for details."
                        toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
                        return toReturn

                    # print('Found results for ' + str(search_string) + ': ' + str(len(gcs_result['response'])))
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
                            # print("Playlist " + playlistID + " contains all tracks in list: " + str([item1["id"], item2["id"]]) + ".")
                            playlists_valid.append({"playlistid": playlistID, "track1": item1["artists"] + " - " + item1["title"], "track2": item2["artists"] + " - " + item2["title"]})
                        else:
                            #playlists does not contain both tracks
                            # print("Playlist " + playlistID + " does NOT contain all tracks in list: " + str([item1["id"], item2["id"]]) + ".")
                            pass


                    '''--> increase times_searched value for item1 and save'''
                    times_counter       +=1
                    get_db().execute('UPDATE ToAnalyzeTracks SET times_searched=? WHERE id=?',(times_counter, item1["id"]))
                    get_db().commit()


        '''--> add tracks from found playlists to ScrapedTracks db'''
        for playlist in playlists_valid:
            # print("Getting tracks from valid playlist: " + playlist["playlistid"])
            track_count         = 0

            for track in getTracksFromPlaylist(playlist["playlistid"], False):
                track_count     +=1

            '''--> update response'''   #{"playlistid":, "foundbytrack1":, "foundbytrack2":...}
            playlistName        = playlist
            resultResponse.append({"playlistid": playlist["playlistid"], "foundbytrack1": playlist["track1"], "foundbytrack2": playlist["track2"], "nooftracks": track_count}) 


        '''--> finished, return response'''
        resultSuccess       = True
        resultMessage       = "Finished searchForPlaylistsContainingTracks()."
        toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}  
        return toReturn   


    except Exception as ex:
        logAction("err - common.py - searchForPlaylistsContainingTracks() --> error while performing: " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())

        resultSuccess       = False
        resultMessage       = "Error while performing searchForPlaylistsContainingTracks(). See log for details"
        toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
        return toReturn
