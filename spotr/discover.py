########################################################################################
##################################### discover.py ######################################
############### Handles all functions related to the discover section ##################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from urllib import response
from flask import Blueprint, render_template, redirect, request, flash
from pip._vendor import requests
import json
import re
from pip._vendor import urllib3
import time
import traceback

from .common import addTracksToPlaylist, apiGetSpotify, changePlaylistDetails, checkIfTrackInDB, getTracksFromArtist, getTracksFromPlaylist, searchSpotify, returnSearchResults, getTrackInfo, createPlaylist, waitForGivenTimeIns, logAction, createPlaylistDescription, checkSourceAndCreatePlaylist, googleSearchApiRequest, extractItemsFromGoogleResponse, checkIfTracksInPlaylist, getDBTracks
from .db import get_db
from . import globalvariables
from flask import current_app
from flask_socketio import emit
# from . import gv_socketio
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)      
# #https://www.codegrepper.com/code-examples/python/InsecureRequestWarning%3A+Unverified+HTTPS+request+is+being+made+to+host
########################################################################################


########################################################################################
######################################## FLASK INIT ####################################
########################################################################################
bp_discover = Blueprint('discover', __name__, url_prefix="/discover")
########################################################################################


########################################################################################
######################################## VARIABLES #####################################
########################################################################################
gv_favList              = []
gv_searchTrackList      = []
gv_jobList              = [] #contains dicts: {artist:artist, title:title, id:id }
gv_searchList           = []
gv_foundPlaylistList    = []
gv_searchTerm           = ""
gv_noFoundPlaylists     = 0
gv_noFoundTracks        = 0
gv_maxResults           = 0
gv_playlistDetails      = {} # {playlistName:, trackList:, inDB:,}
########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
# HTML ROUTING #
@bp_discover.route("/", methods=["GET","POST"])
def discover_main():
    '''--> main routine'''
    '''--> initialize gloval variables'''
    global gv_favList
    #global gv_searchTrackList
    global gv_jobList
    global gv_searchList
    global gv_foundPlaylistList  
    global gv_searchTerm  
    global gv_noFoundTracks
    global gv_maxResults    
    global gv_noFoundPlaylists   
    global gv_playlistDetails      


    '''--> read query parameters'''
    args=request.args      


    #--> PAGE LOAD #
    if request.method == "GET" and not ("addFavTrackID" in args) and not ("delTrackFromSearchJob" in args) and not ("addSearchedTrackID" in args) and not ("showPlaylistTracks" in args) and not ("addPlaylistTracksToDB" in args) and not ("copyPlaylist" in args):
        try:
            '''--> page load  - get list with all tracks in favorite db'''
            gv_favList      = get_db().execute('SELECT * FROM FavoriteTrack').fetchall()


            '''--> return html'''
            return render_template("discover.html",         
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


        except Exception as ex:
            logAction("err - discover.py - discover_main page load --> error while loading page --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error loading page \"discovery.html\".",category="error")

            '''--> return html'''
            return render_template("discover.html",         
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


    elif request.method == "POST" and not ("search_bing" in request.form) and not ("search_google" in request.form):
        '''--> track search button pressed'''
        try:
            '''--> retrieve user input'''
            gv_searchTerm = request.form['searchinput']


            '''--> log'''
            logAction("msg - discover.py - discover_main search track --> Button press, search for track " + str(gv_searchTerm))
            

            '''--> api request'''
            searchResult  = searchSpotify(gv_searchTerm, "track", 10, 0)
            gv_searchList = returnSearchResults(searchResult, "track")


            '''--> return html'''
            return render_template("discover.html",
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "", 
                                    showFavButton       = "", 
                                    showSearchTab       = "show active", 
                                    showSearchButton    = "active", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


        except Exception as ex:
            logAction("err - discover.py - discover_main search track --> error while searching for track --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error searching for tracks with search term \"" + gv_searchTerm + "\".", category="error")

            '''--> return html'''
            return render_template("discover.html",
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "", 
                                    showFavButton       = "", 
                                    showSearchTab       = "show active", 
                                    showSearchButton    = "active", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)



    elif request.method == "POST" and ("search_bing" in request.form) and not ("search_google" in request.form):
        '''--> search for playlists with Bing - button pressed'''
        '''--> 20220925 TODO'''
        try:
            '''--> log'''
            logAction("msg - discover.py - discover_main search playlist bing --> Button press, search for playlist - TODO")
            flash("Search for playlists with BING, todo!!", category="message")


            '''--> return html'''
            return render_template("discover.html",         
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "", 
                                    showFavButton       = "", 
                                    showSearchTab       = "show active", 
                                    showSearchButton    = "active", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


        except Exception as ex:
            logAction("err - discover.py - discover_main search playlist bing --> error while searching for playlist --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error searching for playlists with Bing.", category="error")

            return render_template("discover.html",         
                        favList             = gv_favList, 
                        jobList             = gv_jobList, 
                        searchList          = gv_searchList, 
                        showFavTab          = "", 
                        showFavButton       = "", 
                        showSearchTab       = "show active", 
                        showSearchButton    = "active", 
                        foundPlaylists      = gv_noFoundPlaylists, 
                        searchTerm          = gv_searchTerm, 
                        maxResults          = gv_maxResults ,
                        validPlaylists      = len(gv_foundPlaylistList), 
                        noOfFoundTracks     = gv_noFoundTracks, 
                        validPlaylistList   = gv_foundPlaylistList,
                        playlistDetails     = gv_playlistDetails)


    elif request.method == "POST" and not ("search_bing" in request.form) and ("search_google" in request.form) :
        '''--> Search for playlists that contains tracks in joblist, with google - button pressed'''
        try:
            '''--> initialize variables'''
            gv_noFoundPlaylists         = 0
            gv_foundPlaylistList        = []
            gv_noFoundTracks            = 0
            gv_foundPlaylistList        = []


            '''--> retrieve user input'''
            gv_maxResults  = int(request.form["maxitemsinput"])


            '''--> log'''
            logAction("msg - discover.py - discover_main search playlist google --> Button press, search for playlists with Google - max " + str(gv_maxResults ) + " search results")


            '''--> stop when no items in gv_jobList'''
            if len(gv_jobList) == 0:            
                logAction("msg - discover.py - discover_main search playlist google --> No items in joblist.")
                flash("No items in joblist!", category="message")
                return render_template("discover.html",
                                        favList             = gv_favList, 
                                        jobList             = gv_jobList, 
                                        searchList          = gv_searchList, 
                                        showFavTab          = "", 
                                        showFavButton       = "", 
                                        showSearchTab       = "show active", 
                                        showSearchButton    = "active", 
                                        foundPlaylists      = gv_noFoundPlaylists, 
                                        searchTerm          = gv_searchTerm, 
                                        maxResults          = gv_maxResults ,
                                        validPlaylists      = len(gv_foundPlaylistList), 
                                        noOfFoundTracks     = gv_noFoundTracks, 
                                        validPlaylistList   = gv_foundPlaylistList,
                                        playlistDetails     = gv_playlistDetails)


            '''--> construct searchterm'''
            '''--> e.g.: 2 tracks --> 'real estate - crime' and 'snap - tomorrow' must become 'real estate crime snap tomorrow'''            
            gv_searchTerm   = ""
            i               = 0

            for item in gv_jobList:
                if (i == 0):
                    gv_searchTerm = gv_searchTerm + item["artist"] + " " + item["title"]
                else:
                    gv_searchTerm = gv_searchTerm + " " + item["artist"] + " " + item["title"]       
                i = i + 1


            '''--> perform initial search'''
            googleSearchResult   = googleSearchApiRequest(gv_searchTerm, 0)


            '''--> extract links from google response'''
            foundPlaylistResult     = []
            foundPlaylistResult     = extractItemsFromGoogleResponse(googleSearchResult, gv_maxResults )


            '''--> check response'''
            if foundPlaylistResult["result"] == False:  
                flash(foundPlaylistResult["message"], category="error")
                raise Exception("Faulty response from extractItemsFromGoogleResponse: " + foundPlaylistResult["message"])

            
            '''--> grab track ID's from jobList'''
            trackIds_jobList        = []
            for item in gv_jobList:
                trackIds_jobList.append(item["id"])

            
            '''--> grab tracks from found playlists'''
            trackIdsFoundPlaylists  = []


            '''--> for every found playlist, check if all tracks in gv_jobList appear in it'''
            for playlistLink in foundPlaylistResult["response"]:        #List of dicts, e.g.: {"result": True/False , "response":  list of links!, "message": toReturnMessage}
                #e.g.: linkList = https://open.spotify.com/playlist/7rSfWHAuBpnyimF9ki28o5?utm_campaign=s4a-notif-playlist&utm_source=s4a-notif&utm_medium=creator_email&utm_content=dc0a05e7bd7f42c2871cfb843b86c0ce&nd=1
                '''--> grab playlist ID from each link'''       
                regexResult     = re.search("https:\/\/open.spotify.com\/playlist\/([a-zA-Z0-9]+)", playlistLink) 
                playlistID      = regexResult.group(1)


                '''--> get playlist tracks + details'''
                playlistTracks          = getTracksFromPlaylist(playlistID, True)               #list of dict: {"id" :, "artists" :, "title" :}
                playlistInfo            = apiGetSpotify("playlists/" + playlistID)              #{"result": True/False, "response": list of playlistlinks, "message": ...}
                playlistImageInfo       = apiGetSpotify("playlists/" + playlistID + "/images")  #{"result": True/False, "response": list of playlistlinks, "message": ...


                '''--> check response'''
                if playlistTracks == "":
                    logAction("err - discover.py - discover_main search playlist google --> Error grabbing playlist " + playlistID + " tracks.")
                    flash("Error grabbing playlist tracks!", category="error")
                    raise Exception("Error grabbing playlist tracks!")

                if playlistInfo["result"] == False:
                    logAction("err - discover.py - discover_main search playlist google 15 --> Error grabbing playlist info: " + playlistID + ". Message: " + playlistInfo["message"] + ".")
                    flash("Error grabbing playlist info. See log for details.", category="error")
                    raise Exception("Error grabbing playlist info!")

                if playlistImageInfo["result"] == False:
                    logAction("err - discover.py - discover_main search playlist google 15 --> Error grabbing playlist image info: " + playlistID + ". Message: " + playlistImageInfo["message"] + ".")
                    flash("Error grabbing playlist image info. See log for details.", category="error")
                    raise Exception("Error grabbing playlist image info!")


                '''--> check gv_joblist tracks for appearance in found playlist'''
                if checkIfTracksInPlaylist(trackIds_jobList, playlistTracks, True):
                    #all tracks appear in playlist
                    '''--> add tracks of found playlist to result list'''
                    tempCnt         = 0
                    for item in playlistTracks:
                        # if (not checkIfTrackInDB(trckID, "ListenedTrack")) and (not checkIfTrackInDB(trckID, "ToListenTrack")) and (not checkIfTrackInDB(trckID, "WatchListNewTracks")):
                        tempCnt         = tempCnt + 1
                        trackIdsFoundPlaylists.append(item["id"])


                    '''--> add found playlist to result list'''
                    gv_foundPlaylistList.append({"id": playlistID, "name": playlistInfo["response"]["name"], 'imageurl': playlistImageInfo["response"][0]["url"], "nooftracks": tempCnt})


                    logAction("msg - discover.py - discover_main search playlist google --> Found playlist " + playlistID + " contains all gv_joblist tracks, tracks successfully grabbed.")
                else:
                    logAction("msg - discover.py - discover_main search playlist google --> Found playlist " + playlistID + " does not contain all gv_joblist tracks. Playlist not valid.")


            '''--> result'''
            logAction("msg - discover.py - discover_main search playlist google --> Result for " + gv_searchTerm + ": found " + str(len(foundPlaylistResult["response"])) + " playlists from which " + str(len(gv_foundPlaylistList)) + " were \'valid\', scraped a total of " + str(len(trackIdsFoundPlaylists)) + " tracks.")
            flash(str(len(foundPlaylistResult["response"])) + " playlists found for " + gv_searchTerm + ", from which " + str(len(gv_foundPlaylistList)) + " contain all searched tracks. " + str(len(trackIdsFoundPlaylists)) + " tracks in found playlists.", category="message")

            #Dispay search result info
            gv_noFoundPlaylists         = len(foundPlaylistResult["response"])
            gv_noFoundTracks            = len(trackIdsFoundPlaylists)

            return render_template("discover.html", 
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)

        except Exception as ex:
            logAction("err - discover.py - discover_main search playlist google --> error while searching for playlists --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error searching for playlists for search term " + gv_searchTerm + ". See log for details.", category="error")

            return render_template("discover.html", 
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


    elif request.method == "GET" and not ("addFavTrackID" in args) and not ("delTrackFromSearchJob" in args) and not ("addSearchedTrackID" in args) and ("showPlaylistTracks" in args) and not ("addPlaylistTracksToDB" in args) and not ("copyPlaylist" in args):    
        '''--> Show tracks in one of the found playlists - button pressed'''

        try:    
            '''--> initialize variables'''
            toReturnTracks      = []        #list of dicts 
            trackToAdd          = {}
            tempTracks          = []
            gv_playlistDetails  = {}        #{playlistName:, playlistID:, tracks: list of track ids}


            '''--> Get user input'''
            playlistID = args["showPlaylistTracks"]


            '''--> get playlist tracks'''
            tempTracks          = getTracksFromPlaylist(playlistID, True)     #returns lists of dict: {id: trackid, artists: list with artists, title: title}


            '''--> get db tracks and compare'''
            response        = getDBTracks("ListenedTrack")
            response2       = getDBTracks("ToListenTrack")
            response3       = getDBTracks("WatchListNewTracks")
            dbTracks        = []

            if (response["result"] == True) and (response2["result"] == True) and (response3["result"] == True):
                dbTracks    = response["response"].copy()
                dbTracks.extend(response2["response"])
                dbTracks.extend(response3["response"])
                logAction("msg - discover.py - discover_main search show playlist tracks4 --> " + response["message"] + ", " + response2["message"] + ", " + response3["message"])
            else:
                logAction("err - discover.py - discover_main search show playlist tracks5 --> " + response["message"] + ", " + response2["message"] + ", " + response3["message"])
                raise Exception("No valid trackID list received from DB.")


            '''--> create list of tracks'''
            for track in tempTracks:
                if not track["id"] in dbTracks:
                    trackToAdd={"id":track["id"], "artist":', '.join(track["artists"]), "title":track["title"],"inDB":False}
                else:
                    trackToAdd={"id":track["id"], "artist":', '.join(track["artists"]), "title":track["title"],"inDB":True}
                toReturnTracks.append(trackToAdd)


            '''--> get playlist name'''
            playlistName         = apiGetSpotify("playlists/" + playlistID)["name"]


            '''--> fill gv'''
            print("PLAYLISTNAME: " + playlistName + ", PLAYLISTID: " + playlistID + ", total tracks: " + str(len(toReturnTracks)))
            gv_playlistDetails      = {"playlistName": playlistName, "playlistID": playlistID, "tracks": toReturnTracks}


            '''--> return result'''
            return render_template("discover.html",  
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


        except Exception as ex:
            logAction("err - discover.py - discover_main search show playlist tracks10 --> error while showing playlist tracks --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error while showing playlist tracks. See log for details.", category="error")

            return render_template("discover.html",  
                        favList             = gv_favList, 
                        jobList             = gv_jobList, 
                        searchList          = gv_searchList, 
                        showFavTab          = "show active", 
                        showFavButton       = "active", 
                        showSearchTab       = "", 
                        showSearchButton    = "", 
                        foundPlaylists      = gv_noFoundPlaylists, 
                        searchTerm          = gv_searchTerm, 
                        maxResults          = gv_maxResults ,
                        validPlaylists      = len(gv_foundPlaylistList), 
                        noOfFoundTracks     = gv_noFoundTracks, 
                        validPlaylistList   = gv_foundPlaylistList,
                        playlistDetails     = gv_playlistDetails)
    


    elif not ("addFavTrackID" in args) and not ("delTrackFromSearchJob" in args) and ("addSearchedTrackID" in args) and not ("addPlaylistTracksToDB" in args) and not ("copyPlaylist" in args):
        '''--> Add searched track to joblist - button press'''

        '''--> get user input'''
        trackIdToAdd        = args["addSearchedTrackID"]


        '''--> get track info'''
        track_info          = getTrackInfo(trackIdToAdd, True)


        '''--> add to gv_jobList'''
        toAdd               = {"artist": ', '.join(track_info["artists"]), "title": track_info["title"], "id": trackIdToAdd}
        gv_jobList.append(toAdd)


        '''--> log'''    
        logAction("msg - discover.py - discover_main search playlist google --> Button press, added 'searched' track " + track_info["title"] + " to search job.")


        '''--> return result'''
        return render_template("discover.html",  
                                favList             = gv_favList, 
                                jobList             = gv_jobList, 
                                searchList          = gv_searchList, 
                                showFavTab          = "", 
                                showFavButton       = "", 
                                showSearchTab       = "show active", 
                                showSearchButton    = "active", 
                                foundPlaylists      = gv_noFoundPlaylists, 
                                searchTerm          = gv_searchTerm, 
                                maxResults          = gv_maxResults ,
                                validPlaylists      = len(gv_foundPlaylistList), 
                                noOfFoundTracks     = gv_noFoundTracks, 
                                validPlaylistList   = gv_foundPlaylistList,
                                playlistDetails     = gv_playlistDetails)



    elif request.method == "GET" and not ("addFavTrackID" in args) and not ("delTrackFromSearchJob" in args) and not ("addSearchedTrackID" in args) and not ("showPlaylistTracks" in args) and not ("copyPlaylist" in args) and ("addPlaylistTracksToDB" in args):
        '''--> Add tracks from found playlist to toListen database - button pressed'''

        try:
            '''--> initialize variables'''
            noAddedTracks       = 0


            '''--> get user input'''
            playlistID = args["addPlaylistTracksToDB"]


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> get playlist tracks'''
            tempTracks          = getTracksFromPlaylist(playlistID, False)     #returns lists of only track IDs


            '''--> get db tracks and compare'''
            response        = getDBTracks("ListenedTrack")
            response2       = getDBTracks("ToListenTrack")
            response3       = getDBTracks("WatchListNewTracks")
            dbTracks        = []

            if (response["result"] == True) and (response2["result"] == True) and (response3["result"] == True):
                dbTracks    = response["response"].copy()
                dbTracks.extend(response2["response"])
                dbTracks.extend(response3["response"])
                logAction("msg - discover.py - discover_main search add tracks tolisten db10 --> " + response["message"] + ", " + response2["message"] + ", " + response3["message"])
            else:
                logAction("err - discover.py - discover_main search add tracks tolisten db20 --> " + response["message"] + ", " + response2["message"] + ", " + response3["message"])
                raise Exception("No valid trackID list received from DB.")


            '''--> create list of tracks'''
            for trackID in tempTracks:
                if not trackID in dbTracks:
                    '''--> get track info'''
                    trackInfo       = getTrackInfo(trackID, True)       #{"trackid": string, "title": string, "artists": list of string, "album": string, "href": string, "popularity": string}


                    '''--> add tracks to toListen db'''
                    cursor.execute(
                        'INSERT INTO ToListenTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?)', 
                        (trackID, trackID, trackInfo["album"], ', '.join(trackInfo["artists"]), trackInfo["title"], trackInfo["href"], trackInfo["popularity"], playlistID, 0)
                    )
                    get_db().commit()
                    noAddedTracks       = noAddedTracks + 1


            '''--> get playlist name'''
            playlistName         = apiGetSpotify("playlists/" + playlistID)["name"]


            '''--> log'''
            logAction("msg - discover.py - discover_main search add tracks tolisten db50 --> Succesfully added " + str(noAddedTracks) + " tracks from playlist " + playlistName + " to ToListenDB.")
            flash("Succesfully added " + str(noAddedTracks) + " tracks from playlist " + playlistName + " to ToListenDB.", category="message")


            '''--> return result'''
            return render_template("discover.html",  
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


        except Exception as ex:
            logAction("err - discover.py - discover_main search add tracks tolisten db100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error adding tracks to toListen db. See log for details.", category="error")

            return render_template("discover.html",  
                        favList             = gv_favList, 
                        jobList             = gv_jobList, 
                        searchList          = gv_searchList, 
                        showFavTab          = "show active", 
                        showFavButton       = "active", 
                        showSearchTab       = "", 
                        showSearchButton    = "", 
                        foundPlaylists      = gv_noFoundPlaylists, 
                        searchTerm          = gv_searchTerm, 
                        maxResults          = gv_maxResults ,
                        validPlaylists      = len(gv_foundPlaylistList), 
                        noOfFoundTracks     = gv_noFoundTracks, 
                        validPlaylistList   = gv_foundPlaylistList,
                        playlistDetails     = gv_playlistDetails)


    elif request.method == "GET" and not ("addFavTrackID" in args) and not ("delTrackFromSearchJob" in args) and not ("addSearchedTrackID" in args) and not ("showPlaylistTracks" in args) and not ("addPlaylistTracksToDB" in args) and ("copyPlaylist" in args):
        '''--> Create new playlist with all (not-listened) tracks from found playlist - button pressed'''
        try:
            '''--> initialize variables'''
            noAddedTracks               = 0
            tracksToCopy                = []        #track IDs
            createPlaylistResponse      = {}
            addTracksResponse           = {}


            '''--> get user input'''
            playlistID = args["copyPlaylist"]


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> get playlist tracks'''
            tempTracks          = getTracksFromPlaylist(playlistID, False)     #returns lists of only track IDs


            '''--> get db tracks and compare'''
            response        = getDBTracks("ListenedTrack")
            response2       = getDBTracks("ToListenTrack")
            response3       = getDBTracks("WatchListNewTracks")
            dbTracks        = []

            if (response["result"] == True) and (response2["result"] == True) and (response3["result"] == True):
                dbTracks    = response["response"].copy()
                dbTracks.extend(response2["response"])
                dbTracks.extend(response3["response"])
                logAction("msg - discover.py - discover_main search copy playlist10 --> " + response["message"] + ", " + response2["message"] + ", " + response3["message"])
            else:
                logAction("err - discover.py - discover_main search copy playlist20 --> " + response["message"] + ", " + response2["message"] + ", " + response3["message"])
                raise Exception("No valid trackID list received from DB.")


            '''--> remove duplicates (if any) from list'''
            tempTracks = list(dict.fromkeys(tempTracks))


            '''--> create list of tracks which need to be added to new playlist'''
            for trackID in tempTracks:
                if not trackID in dbTracks:
                    '''--> get track info'''
                    trackInfo       = getTrackInfo(trackID, True)       #{"trackid": string, "title": string, "artists": list of string, "album": string, "href": string, "popularity": string}


                    '''--> add to temporary list'''
                    tracksToCopy.append(trackID)
                    

                    '''--> add tracks to ListenedTrack db'''
                    cursor.execute(
                        'INSERT INTO ListenedTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?)', 
                        (trackID, trackID, trackInfo["album"], ', '.join(trackInfo["artists"]), trackInfo["title"], trackInfo["href"], trackInfo["popularity"], playlistID, 0)
                    )
                    get_db().commit()
                    noAddedTracks       = noAddedTracks + 1


            '''--> get playlist name'''
            playlistName         = apiGetSpotify("playlists/" + playlistID)["name"]


            '''--> check for tracks in list'''
            if len(tracksToCopy) == 0:
                logAction("err - discover.py - discover_main search copy playlist 30 --> No (unlistened) tracks found in playlist " + playlistName + ".")
                raise TypeError("No (unlistened) tracks found in playlist " + playlistName + ".")


            '''--> create new empty playlist + check response'''
            createPlaylistResponse      = createPlaylist("spotr_copyOfPlaylist_" + playlistName, "")        #returns dict {result: True/false, response: {playlistid: }, message:...}

            if createPlaylistResponse["result"] == False:
                logAction("err - discover.py - discover_main search copy playlist 90 --> Negative feedback from createPlaylist: " + createPlaylistResponse["message"])
                raise Exception(createPlaylistResponse["message"])


            '''--> add tracks to newly created playlist + check response'''
            addTracksResponse       = addTracksToPlaylist(createPlaylistResponse["response"]["playlistid"], tracksToCopy)

            if addTracksResponse["result"] == False:
                logAction("err - discover.py - discover_main search copy playlist 100 --> Negative feedback from addTracksToPlaylist: " + addTracksResponse["message"])
                raise Exception(addTracksResponse["message"])


            '''--> log'''
            logAction("msg - discover.py - discover_main search add tracks tolisten db50 --> Succesfully added " + str(noAddedTracks) + " tracks from playlist " + playlistName + " to new playlist.")
            flash("Succesfully added " + str(noAddedTracks) + " tracks from playlist " + playlistName + " to new playlist.", category="message")


            '''--> return result'''
            return render_template("discover.html",  
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


        except TypeError:
            logAction("msg - discover.py - discover_main search copy playlist 110 --> No (unlistened) tracks found in playlist " + playlistName + ".")
            flash("No (unlistened) tracks found in playlist " + playlistName + ".", category="message")

            '''--> return result'''
            return render_template("discover.html",  
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)

        except Exception as ex:
            logAction("err - discover.py - discover_main search copy playlist 110 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error copying playlist tracks to new playlist. See log for details.", category="error")

            '''--> return result'''
            return render_template("discover.html",  
                                    favList             = gv_favList, 
                                    jobList             = gv_jobList, 
                                    searchList          = gv_searchList, 
                                    showFavTab          = "show active", 
                                    showFavButton       = "active", 
                                    showSearchTab       = "", 
                                    showSearchButton    = "", 
                                    foundPlaylists      = gv_noFoundPlaylists, 
                                    searchTerm          = gv_searchTerm, 
                                    maxResults          = gv_maxResults ,
                                    validPlaylists      = len(gv_foundPlaylistList), 
                                    noOfFoundTracks     = gv_noFoundTracks, 
                                    validPlaylistList   = gv_foundPlaylistList,
                                    playlistDetails     = gv_playlistDetails)


    elif request.method == "GET" and ("addFavTrackID" in args) and not ("delTrackFromSearchJob" in args) and not ("addSearchedTrackID" in args) and not ("addPlaylistTracksToDB" in args) and not ("showPlaylistTracks" in args) and not ("copyPlaylist" in args):
        '''--> add track from favorite section to search job - button press'''

        try:
            '''--> initialize variables'''
            toAdd               = {}
            track_info          = {}


            '''--> get user input'''
            trackIDToAdd        = args['addFavTrackID']


            '''--> log'''
            logAction("msg - discover.py - discover_main search add fav track 10 --> add favorite track " + trackIDToAdd + " to search job - button press.")  


            '''--> track info'''
            track_info          = getTrackInfo(trackIDToAdd, True)        #{"trackid": string, "title": string, "artists": list of string, "album": string, "href": string, "popularity": string}


            '''--> add to jobList'''
            toAdd               = {"artist": ', '.join(track_info["artists"]), "title": track_info["title"], "id": trackIDToAdd}
            gv_jobList.append(toAdd)
            logAction("msg - discover.py - discover_main search add fav track 20 --> favorite track " + trackIDToAdd + " added to search job.")  


            '''--> return html'''
            return render_template("discover.html",  
            favList             = gv_favList, 
            jobList             = gv_jobList, 
            searchList          = gv_searchList, 
            showFavTab          = "show active", 
            showFavButton       = "active", 
            showSearchTab       = "", 
            showSearchButton    = "", 
            foundPlaylists      = gv_noFoundPlaylists, 
            searchTerm          = gv_searchTerm, 
            maxResults          = gv_maxResults ,
            validPlaylists      = len(gv_foundPlaylistList), 
            noOfFoundTracks     = gv_noFoundTracks, 
            validPlaylistList   = gv_foundPlaylistList,
            playlistDetails     = gv_playlistDetails)


        except Exception as ex:
            logAction("err - discover.py - discover_main search add fav track 100 --> error while adding favorite " + trackIDToAdd + " track to jobList --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error while adding favorite track " + trackIDToAdd + " to jobList. See log for details.", category="error")

            return render_template("discover.html",  
                        favList             = gv_favList, 
                        jobList             = gv_jobList, 
                        searchList          = gv_searchList, 
                        showFavTab          = "show active", 
                        showFavButton       = "active", 
                        showSearchTab       = "", 
                        showSearchButton    = "", 
                        foundPlaylists      = gv_noFoundPlaylists, 
                        searchTerm          = gv_searchTerm, 
                        maxResults          = gv_maxResults ,
                        validPlaylists      = len(gv_foundPlaylistList), 
                        noOfFoundTracks     = gv_noFoundTracks, 
                        validPlaylistList   = gv_foundPlaylistList,
                        playlistDetails     = gv_playlistDetails)


    elif request.method == "GET" and not ("addFavTrackID" in args) and ("delTrackFromSearchJob" in args) and not ("addSearchedTrackID" in args) and not ("addPlaylistTracksToDB" in args) and not ("showPlaylistTracks" in args) and not ("copyPlaylist" in args): 
        '''--> delete track from search job - button press'''

        try:
            '''--> get user input'''
            trackIDToDelete         = args["delTrackFromSearchJob"] 


            '''--> log'''
            logAction("msg - discover.py - discover_main search del trackfrom search job 10 --> delete track " + trackIDToDelete + " from search job - button press.")  


            '''--> delete'''
            for item in gv_jobList:         #list of {"artist": , "title": , "id":}
                if item["id"] == trackIDToDelete:
                    gv_jobList.remove(item)                    
                    logAction("msg - discover.py - discover_main search del trackfrom search job 30 --> removed track " + trackIDToDelete + " from search job.")


            '''--> return html'''
            return render_template("discover.html",  
            favList             = gv_favList, 
            jobList             = gv_jobList, 
            searchList          = gv_searchList, 
            showFavTab          = "show active", 
            showFavButton       = "active", 
            showSearchTab       = "", 
            showSearchButton    = "", 
            foundPlaylists      = gv_noFoundPlaylists, 
            searchTerm          = gv_searchTerm, 
            maxResults          = gv_maxResults ,
            validPlaylists      = len(gv_foundPlaylistList), 
            noOfFoundTracks     = gv_noFoundTracks, 
            validPlaylistList   = gv_foundPlaylistList,
            playlistDetails     = gv_playlistDetails)  


        except Exception as ex:
            logAction("err - discover.py - discover_main search del trackfrom search job 100 --> error while deleting track " + trackIDToAdd + " from jobList --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error while deleting track " + trackIDToAdd + " from jobList. See log for details.", category="error")

            return render_template("discover.html",  
                        favList             = gv_favList, 
                        jobList             = gv_jobList, 
                        searchList          = gv_searchList, 
                        showFavTab          = "show active", 
                        showFavButton       = "active", 
                        showSearchTab       = "", 
                        showSearchButton    = "", 
                        foundPlaylists      = gv_noFoundPlaylists, 
                        searchTerm          = gv_searchTerm, 
                        maxResults          = gv_maxResults ,
                        validPlaylists      = len(gv_foundPlaylistList), 
                        noOfFoundTracks     = gv_noFoundTracks, 
                        validPlaylistList   = gv_foundPlaylistList,
                        playlistDetails     = gv_playlistDetails)