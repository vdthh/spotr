########################################################################################
##################################### watchlist.py #####################################
############### Handles all functions related to the watchlist section #################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from asyncio import wait_for
from cgi import test
import functools
from unittest import result
# from tabnanny import check
# from tarfile import LENGTH_NAME
from flask import (Blueprint, flash, g, redirect, render_template, request, url_for)
from datetime import datetime, timedelta
import json
import os
import binascii
import traceback
import sqlite3
from .common import addTracksToPlaylist, apiGetSpotify, changePlaylistDetails, checkIfTrackInDB, getTracksFromArtist, getTracksFromPlaylist, searchSpotify, returnSearchResults, getTrackInfo, createPlaylist, waitForGivenTimeIns, logAction, createPlaylistDescription, checkSourceAndCreatePlaylist, getDBTracks
from .db import get_db
from . import globalvariables

from flask import current_app
from flask_socketio import emit
# from . import gv_socketio
########################################################################################


########################################################################################
######################################## FLASK INIT ####################################
########################################################################################
bp_watchlist = Blueprint('watchlist', __name__, url_prefix="/watchlist")
########################################################################################


########################################################################################
###################################### SOCKETIO INIT ###################################
########################################################################################
def sendStatusViaSocket(note):
    print("MANUAL CALLBACK TRIGGERED")
    current_app.gv_socketio.emit('updateStatus', {"data": "note: " + note}, namespace='/watchlist')
    current_app.gv_socketio.send('message', {"data": "note: " + note}, namespace='/watchlist')
    # gv_socketio.emit('updateStatus', {"data": "note: " + note})
    print("TRIGGER DONE")
########################################################################################


########################################################################################
######################################## VARIABLES #####################################
########################################################################################
gv_artistList              = []     #list of {"artist": , "id": , "popularity": , "image": }
gv_playlistList            = []     #list of {"name": , "id": , "description": , "image": , "owner": , "totaltracks": }
gv_watchlistItems          = []     #list of {"id:" , "type": , "name": , "image": , "dateAdded": , "dateLastCheck": , "noOfNewItems": , "listOfNewItemsID": }
gv_newTracksToSave         = []     #list of tracks ID's of new tracks to add to NewPlaylistTracks DB
gv_searchType              = ""
gv_searchTerm              = ""
gv_offset                  = 0
gv_limit                   = 0
gv_total                   = 0
########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
# HTML ROUTING #
@bp_watchlist.route("/", methods=["GET","POST"])
def watchlist_main():
    '''--> main routine'''
    '''--> initialize global variables'''
    global gv_artistList        
    global gv_playlistList     
    global gv_watchlistItems    
    global gv_newTracksToSave
    global gv_searchType     
    global gv_searchTerm         
    global gv_offset                  
    global gv_limit                   
    global gv_total                

    '''--> read query parameters'''
    args=request.args      


    #--> PAGE LOAD #
    if request.method == "GET" and not ("addArtist" in args) and not ("addPlaylist" in args) and not ("delItem" in args) and not ("offs" in args) and not ("lim" in args) and not ("searchTerm" in args) and not ("searchType" in args):
        try:
            '''--> page load  - show playlist items with info'''
            '''--> initialize variables'''
            '''TODO'''
            gv_watchlistItems = []  #list empty, initialize it every reload

            print("PAGE LOAD")
            current_app.gv_socketio.emit('updateStatus', {"data": "111111"}, namespace='/watchlist')
            # gv_socketio.send('message', {"data": "note: " + 'note'}, namespace='/watchlist')
            # gv_socketio.emit('updateStatus', {"data": "note: " + 'note'})
            # gv_socketio.send('message', {"data": "note: " + 'note'})
            # sendStatusViaSocket("11111111111111")

            '''--> db operation'''
            data = get_db().execute('SELECT * FROM WatchList').fetchall()    #returns list of dicts https://docs.python.org/3/library/sqlite3.html


            '''--> check data'''
            if data is None:
                flash("No entries in watchlist yet!", category="error")
                logAction("msg - watchlist.py - watchlist_main --> page reload --> no items to show!")


            '''--> (re)load watchlist items'''
            loadWatchlistItems()

            # sendStatusViaSocket("222222222222222222")

            '''--> return html'''
            return render_template('watchlist.html', 
                                    watchlistItems      = gv_watchlistItems,
                                    showArtistBtn       = "active", 
                                    showArtistTab       = "show active", 
                                    showPlaylistBtn     = "" , 
                                    showPlaylistTab     = "", 
                                    showUserBtn         = "", 
                                    showUserTab         = "",
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)

        except Exception as ex:
            logAction("err - watchlist.py - watchlist_main2 --> error while loading page --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
        

    #--> SEARCH ARTIST - BUTTON PRESSED - PAGINATION # 
    if (request.method == "POST" and  ("artist_search" in request.form)) or (request.method == "GET" and not ("addArtist" in args) and ("offs" in args) and ("lim" in args) and ("searchTerm" in args) and ("searchType" in args)):
        try:
            '''--> pagination or search button press?'''
            if (request.method == "GET" and not ("addArtist" in args) and ("offs" in args) and ("lim" in args) and ("searchTerm" in args) and ("searchType" in args)):
                paginReq = True
            else:
                paginReq = False


            '''--> initialize variables'''
            gv_artistList       = [] #(re-)initialize global artist list
            gv_watchlistItems   = []


            '''--> (re)load watchlist items'''
            loadWatchlistItems()


            '''--> update variables'''
            if paginReq:
                gv_searchTerm   = args["searchTerm"]
                gv_searchType   = args["searchType"]
                gv_offset       = int(args["offs"])
                gv_limit        = int(args["lim"])
            else:
                print("SEARCH BUTTON PRESS")
                gv_searchTerm   = request.form["searchartistinput"] #searchterm entered in page
                gv_searchType   = "artist"
                gv_offset       = 0
                gv_limit        = 10


            '''--> api request'''
            logAction("msg - watchlist.py - watchlist_main3 --> searching for artist " + gv_searchTerm)
            response             = searchSpotify(gv_searchTerm, gv_searchType, gv_limit, gv_offset)
            

            '''--> check response before continuing'''
            if response == '':
                logAction("err - watchlist.py - watchlist_main4 --> empty api response for searching artist.")
                flash("Error when searching for artist " + gv_searchTerm + ", empty response.", category="error")
                return render_template('watchlist.html', 
                        showArtistBtn       = "active", 
                        showArtistTab       = "show active", 
                        showPlaylistBtn     = "" , 
                        showPlaylistTab     = "", 
                        showUserBtn         = "", 
                        showUserTab         = "",
                        status_general      = globalvariables.general_status,
                        show_spinner        = globalvariables.general_status_show_spinner)


            '''--> retrieve pagination'''
            total       = response[gv_searchType  + 's']['total']
            gv_limit    = response[gv_searchType  + 's']['limit']
            gv_offset   = response[gv_searchType  + 's']['offset']


            '''--> fill artistList'''
            for item in returnSearchResults(response, "artist"):  #{"artist": , "id": , "popularity": , "image": }
                gv_artistList.append({"artist": item["artist"], "id": item['id'], "popularity": item['popularity'], "image": item['imageurl']})


            '''--> return html'''
            return render_template("watchlist.html", 
                                    watchlistItems      = gv_watchlistItems,
                                    artistList          = gv_artistList, 
                                    playlistList        = gv_playlistList,
                                    showArtistBtn       = "active", 
                                    showArtistTab       = "show active", 
                                    showPlaylistBtn     = "" , 
                                    showPlaylistTab     = "", 
                                    showUserBtn         = "", 
                                    showUserTab         = "",
                                    tot                 = total,
                                    lim                 = gv_limit,
                                    offs                = gv_offset,
                                    searchType          = gv_searchType,
                                    searchTerm          = gv_searchTerm,
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)

        except Exception as ex:
            flash("Error while searching for artist " + gv_searchTerm + ".", category="error")
            logAction("err - watchlist.py - watchlist_main5 --> error while loading page --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            return render_template('watchlist.html', 
                                    artistList = gv_artistList,
                                    showArtistBtn       = "active", 
                                    showArtistTab       = "show active", 
                                    showPlaylistBtn     ="" , 
                                    showPlaylistTab     = "", 
                                    showUserBtn         = "", 
                                    showUserTab         = "",
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)


    #--> SEARCH PLAYLIST - BUTTON PRESSED - PAGINATION # 
    if (request.method == "POST" and  ("playlist_search" in request.form)) or (request.method == "GET" and not ("addArtist" in args) and ("offs" in args) and ("lim" in args) and ("searchTerm" in args) and ("searchType" in args)):
        try:
            '''--> pagination or search button press?'''
            if (request.method == "GET" and not ("addPlaylist" in args) and ("offs" in args) and ("lim" in args) and ("searchTerm" in args) and ("searchType" in args)):
                paginReq = True
                print("search playlist - pagination")
            else:
                paginReq = False
                print("search playlist - button press")

            '''--> initialize variables'''
            gv_playlistList   = [] #(re-)initialize global artist list
            gv_watchlistItems = []


            '''--> (re)load watchlist items'''
            loadWatchlistItems()


            '''--> update variables'''
            if paginReq:
                gv_searchTerm   = args["searchTerm"]
                gv_searchType   = args["searchType"]
                gv_offset       = int(args["offs"])
                gv_limit        = int(args["lim"])
            else:
                gv_searchTerm   = request.form["searchplaylistinput"] #searchterm entered in page
                gv_searchType   = "playlist"
                gv_offset       = 0
                gv_limit        = 10


            '''--> api request'''
            logAction("msg - watchlist.py - watchlist_main50 --> searching for playlist " + gv_searchTerm)
            response = searchSpotify(gv_searchTerm, gv_searchType, gv_limit, gv_offset)
            

            '''--> check response before continuing'''
            if response == '':
                logAction("err - watchlist.py - watchlist_main51 --> empty api response for searching playlist.")
                flash("Error when searching for playlist " + gv_searchTerm + ", empty response.", category="error")
                return render_template('watchlist.html', 
                        showArtistBtn       = "", 
                        showArtistTab       = "", 
                        showPlaylistBtn     = "active" , 
                        showPlaylistTab     = "show active", 
                        showUserBtn         = "", 
                        showUserTab         = "",
                        status_general      = globalvariables.general_status,
                        show_spinner        = globalvariables.general_status_show_spinner)


            '''--> retrieve pagination'''
            total       = response[gv_searchType  + 's']['total']
            gv_limit    = response[gv_searchType  + 's']['limit']
            gv_offset   = response[gv_searchType  + 's']['offset']


            '''--> fill playlistList'''
            for item in returnSearchResults(response, "playlist"):  #{"name": , "id": , "description": , "image": , "owner": , "totaltracks": }
                gv_playlistList.append({"name": item["name"], "id": item['id'], "description": item['description'], "image": item['imageurl'], "owner": item['owner'], "totaltracks": item['totaltracks']})


            '''--> return html'''
            return render_template("watchlist.html", 
                                    watchlistItems      = gv_watchlistItems,
                                    artistList          = gv_artistList, 
                                    playlistList        = gv_playlistList,
                                    showArtistBtn       = "", 
                                    showArtistTab       = "", 
                                    showPlaylistBtn     = "active" , 
                                    showPlaylistTab     = "show active", 
                                    showUserBtn         = "", 
                                    showUserTab         = "",
                                    tot                 = total,
                                    lim                 = gv_limit,
                                    offs                = gv_offset,
                                    searchType          = gv_searchType,
                                    searchTerm          = gv_searchTerm,
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)

        except Exception as ex:
            flash("Error while searching for artist " + gv_searchTerm + ".", category="error")
            logAction("err - watchlist.py - watchlist_main5 --> error while loading page --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            return render_template('watchlist.html', 
                                    artistList = gv_artistList,
                                    showArtistBtn       = "", 
                                    showArtistTab       = "", 
                                    showPlaylistBtn     = "active", 
                                    showPlaylistTab     = "show active", 
                                    showUserBtn         = "", 
                                    showUserTab         = "",
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)


    #--> ADD ARTIST OR PLAYLIST TO WATCHLIST - BUTTON PRESSED #
    if request.method == "GET"  and not ("delItem" in args) and not ("offs" in args) and not ("lim" in args) and not ("searchTerm" in args) and not ("searchType" in args):   
        '''--> local variables'''
        lType       = ""
        lID         = ""
        lArtistBtn  = ""
        lArtistTab  = ""
        lPlstBtn    = ""
        lPlstTab    = ""
        lName       = ""


        '''--> artist or playlist?'''
        try:
            if ("addArtist" in args):
                lType   = "artist"
                lName   = args["artistName"]
            elif ("addPlaylist" in args):
                lType   = "playlist"
                lName   = args["playlistName"]
            else:
                lType   = ""
                lName   = ""


            '''--> get details'''
            if lType == "artist":
                lID         = args["addArtist"]
                lArtistBtn  = "active"
                lArtistTab  = "show active"
            elif lType == "playlist":
                lID         = args["addPlaylist"]
                lPlstBtn    = "active"
                lPlstTab    = "show active"  
            response = apiGetSpotify(lType + "s/" + lID)        #{"result": True/False, "response": list of playlistlinks, "message": ...}
            logAction("msg - watchlist.py - watchlist_main80 --> add " + lType + " " + lID + " to watchlist --> starting.") 
        

            '''--> (re)load watchlist items'''
            gv_watchlistItems = []  #list empty, initialize it every reload
            loadWatchlistItems()


            '''--> check response before continuing'''
            if response["result"] == False:
                logAction("err - watchlist.py - watchlist_main81 --> empty api response for searching " + lType + ". Message: " + response["message"] + ".")
                flash("Error when searching for " + lType + " " + gv_searchTerm + ", empty response.", category="error")


                '''--> return html'''
                return render_template('watchlist.html', 
                                        watchlistItems      = gv_watchlistItems,
                                        artistList          = gv_artistList,
                                        playlistList        = gv_playlistList,
                                        showArtistBtn       = lArtistBtn, 
                                        showArtistTab       = lArtistTab, 
                                        showPlaylistBtn     = lPlstBtn , 
                                        showPlaylistTab     = lPlstTab, 
                                        showUserBtn         = "", 
                                        showUserTab         = "",
                                        status_general      = globalvariables.general_status,
                                        show_spinner        = globalvariables.general_status_show_spinner)


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> artist/playlist/... in watchlist?'''        
            if cursor.execute('SELECT id FROM WatchList WHERE id = ?', (lID,)).fetchone() == None:
                pass    #not in db yet
            else:
                logAction("msg - watchlist.py - watchlist_main80.1 --> " + lType + " " + response["response"]["name"] + " already in watchlist.")
                flash(lType + " " + response["response"]["name"] + " already in watchlist.", category="error")


                '''--> return html'''
                return render_template('watchlist.html', 
                                        watchlistItems      = gv_watchlistItems,
                                        artistList          = gv_artistList,
                                        playlistList        = gv_playlistList,
                                        showArtistBtn       = lArtistBtn, 
                                        showArtistTab       = lArtistTab, 
                                        showPlaylistBtn     = lPlstBtn , 
                                        showPlaylistTab     = lPlstTab, 
                                        showUserBtn         = "", 
                                        showUserTab         = "",
                                        status_general      = globalvariables.general_status,
                                        show_spinner        = globalvariables.general_status_show_spinner)


            '''--> grab tracks'''
            if lType == "artist":
                tracklist       = getTracksFromArtist(lID, False)
            elif lType == "playlist":
                tracklist       = getTracksFromPlaylist(lID, False)
            logAction("msg - watchlist.py - watchlist_main82 --> grabbed " + lType + " " + lID + "'s tracks: " + str(len(tracklist)))


            '''--> check data'''
            if response["response"]["name"]:
                name = response["response"]["name"]
            else:
                name = ""

            if response["response"]["images"]:
                imglink = response["response"]["images"][0]["url"]
            else:
                imglink = ""


            '''--> check if entry in db table WatchListNewTracks exists, before adding tracks to it'''
            try:
                if cursor.execute('SELECT * FROM WatchListNewTracks').fetchone() == None:    #add first entry to db table
                    dummyList = []
                    get_db().execute('INSERT INTO WatchListNewTracks (id, trackList) VALUES (?,?)',("newTracks", json.dumps(dummyList)))
                    get_db().commit()
            except sqlite3.OperationalError:
                logAction("msg - watchlist.py - watchlist_main83 --> error while adding entry in db table WatchListNewTracks")


                '''--> return html'''
                return render_template('watchlist.html', 
                                        watchlistItems      = gv_watchlistItems,
                                        artistList          = gv_artistList,
                                        playlistList        = gv_playlistList,
                                        showArtistBtn       = lArtistBtn, 
                                        showArtistTab       = lArtistTab, 
                                        showPlaylistBtn     = lPlstBtn , 
                                        showPlaylistTab     = lPlstTab, 
                                        showUserBtn         = "", 
                                        showUserTab         = "",
                                        status_general      = globalvariables.general_status,
                                        show_spinner        = globalvariables.general_status_show_spinner)


            '''--> add artist/playlist/... to WatchList db'''
            get_db().execute(
                'INSERT INTO WatchList (id, _type, _name, last_time_checked, no_of_items_checked, href, list_of_current_items, imageURL, new_items_since_last_check) VALUES (?,?,?,?,?,?,?,?,?)', 
                (lID, lType, name, datetime.now(), len(tracklist), response["response"]["external_urls"]["spotify"], json.dumps(tracklist), imglink, len(tracklist))
            )
            get_db().commit()
            logAction("msg - watchlist.py - watchlist_main84 --> " + lType + " " + name + " added to watchlist.")
            flash(lType + " " + name + " added to watchlist.", category="message")


            '''--> add artist/playlist/... tracks to WatchListNewTracks'''
            '''check tracks if in db'''
            data                = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone()   #needed to get trackList length before stating to add tracks...
            currentTrackList    = json.loads(data[1])
            initLength          = len(currentTrackList)
            endLength           = 0


            for trck in tracklist:
                if not checkIfTrackInDB(trck, "ListenedTrack") and not checkIfTrackInDB(trck, "ToListenTrack") and not checkIfTrackInDB(trck, "WatchListNewTracks"):
                    #Not in db yet, update tracklist
                    data                = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone() 
                    currentTrackList    = json.loads(data[1])           #data = first (and only) row of db table WatchListNewTracks, data[0] = id, data[1] = trackList
                    toAdd               = {"id": trck, "from_type": lType, "from_name": lName}  
                    currentTrackList    = currentTrackList + [toAdd]     #add track to existing tracklist
                    endLength           = len(currentTrackList) 
                    get_db().execute('UPDATE WatchListNewTracks SET trackList=? WHERE id=?',(json.dumps(currentTrackList), "newTracks"))
                    get_db().commit()
            logAction("msg - watchlist.py - watchlist_main85 --> Finished - tracks in tracklist before adding " + lType + " " + lID + ": " + str(initLength) + ", length after adding tracks: " + str(endLength) + ".")
            flash(str(endLength - initLength) + " tracks added to WatchListNewTracks (total of " +  str(endLength) + ").", category="message")                               


            '''--> (re)load watchlist items'''
            gv_watchlistItems = []  #list empty, initialize it every reload
            loadWatchlistItems()


            '''--> finished,  return html'''
            return render_template('watchlist.html', 
                                    watchlistItems      = gv_watchlistItems,
                                    artistList          = gv_artistList,
                                    playlistList        = gv_playlistList,
                                    showArtistBtn       = lArtistBtn, 
                                    showArtistTab       = lArtistTab, 
                                    showPlaylistBtn     = lPlstBtn, 
                                    showPlaylistTab     = lPlstTab, 
                                    showUserBtn         = "", 
                                    showUserTab         = "", 
                                    offs                = gv_offset, 
                                    lim                 = gv_limit, 
                                    tot                 = gv_total, 
                                    searchTerm          = gv_searchTerm, 
                                    searchType          = gv_searchType,
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)


        except Exception as ex:
            flash("Error ...", category="error")
            logAction("err - watchlist.py - watchlist_main76 --> ... --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            return render_template('watchlist.html', 
                                    watchlistItems      = gv_watchlistItems,
                                    artistList          = gv_artistList,
                                    playlistList        = gv_playlistList,
                                    showArtistBtn       = "", 
                                    showArtistTab       = "", 
                                    showPlaylistBtn     = "active" , 
                                    showPlaylistTab     = "show active", 
                                    showUserBtn         = "", 
                                    showUserTab         = "",
                                    offs                = gv_offset, 
                                    lim                 = gv_limit, 
                                    tot                 = gv_total, 
                                    searchTerm          = gv_searchTerm, 
                                    searchType          = gv_searchType,
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)


#--> DELETE ITEM FROM WATCHLIST - BUTTON PRESSED #
    if request.method == "GET" and not ("addArtist" in args) and ("delItem" in args) and not ("offs" in args) and not ("lim" in args) and not ("searchTerm" in args) and not ("searchType" in args):
        # https://pynative.com/python-mysql-delete-data/
        try:
            '''--> item'''
            toDelID = args["delItem"]
            logAction("msg - watchlist.py - watchlist_main30 --> delete item " + toDelID + " from watchlist --> starting.")

  
            '''--> delete from db'''
            cursor = get_db().cursor()
            cursor.execute('DELETE FROM WatchList WHERE id = ?', (toDelID,))

            if cursor.rowcount != 0:
                flash("Succesfully deleted "+ str(cursor.rowcount) + " item (" + toDelID + ") from watchlist.", category="message")
                logAction("msg - watchlist.py - watchlist_main31 --> succesfully deleted " + str(cursor.rowcount) + " item (" + toDelID + ") from watchlist.")
            else:
                flash("Nothing found while deleting item " + toDelID + " from watchlist...", category="error")
                logAction("msg - watchlist.py - watchlist_main32 --> nothing found while deleting item " + toDelID + " from watchlist.")

            get_db().commit()


            '''--> (re)load watchlist items'''
            gv_watchlistItems = []  #list empty, initialize it every reload
            loadWatchlistItems() 
 

            '''--> return html'''
            return render_template('watchlist.html', 
                                    watchlistItems      = gv_watchlistItems,
                                    artistList          = gv_artistList,
                                    playlistList        = gv_playlistList,
                                    showArtistBtn       = "active", 
                                    showArtistTab       = "show active", 
                                    showPlaylistBtn     = "", 
                                    showPlaylistTab     = "", 
                                    showUserBtn         = "", 
                                    showUserTab         = "", 
                                    offs                = gv_offset, 
                                    lim                 = gv_limit, 
                                    tot                 = gv_total, 
                                    searchTerm          = gv_searchTerm, 
                                    searchType          = gv_searchType,
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)


        except Exception as ex:
            flash("Error deleting item " + toDelID + " from watchlist!", category="error")
            logAction("err - watchlist.py - watchlist_main33 --> Error deleting item " + toDelID + " --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            return render_template('watchlist.html', 
                                    artistList = gv_artistList,
                                    showArtistBtn       = "active", 
                                    showArtistTab       = "show active", 
                                    showPlaylistBtn     = "" , 
                                    showPlaylistTab     = "", 
                                    showUserBtn         = "", 
                                    showUserTab         = "",
                                    status_general      = globalvariables.general_status,
                                    show_spinner        = globalvariables.general_status_show_spinner)


########################################################################################
@bp_watchlist.route('/checkForNewTracks', methods=['GET', 'POST'])
def watchlist_checkForNewTracks():
    '''--> Check watchlist items for new track initiated from html page (button press) OR automatically initiated by external .py script (via crontab)'''
    logAction("msg - watchlist.py - watchlist_checkForNewTracks() --> started via button press/automatically initiated.") 

    if not checkWatchlistItems():
        logAction("err - watchlist.py - watchlist_checkForNewTracks2() --> failed! --> false returned.") 
        flash("checkForNewTracks - failed!", category="error")
    else:
        logAction("msg - watchlist.py - watchlist_checkForNewTracks3() --> finished succefully.") 
        flash("checkForNewTracks - finished!", category="success")


    '''--> (re)load watchlist items'''
    loadWatchlistItems()


    '''--> return html'''
    return redirect("/watchlist")

########################################################################################
@bp_watchlist.route('/update_status', methods=['GET'])
def updateGeneralStatus(message):
    '''--> to be called in fixed intervals by javascript in html code'''
    globalvariables.general_status = message
    print(globalvariables.general_status)
    return globalvariables.general_status

########################################################################################
########################################################################################

########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
def loadWatchlistItems():
    '''--> fill global list with watchlist items from db'''
    '''--> db'''
    logAction("msg - watchlist.py - watchlist_main40 --> (re)loading watchlist items")
    cursor = get_db().cursor()


    '''--> load items from db and fill gv list'''
    for item in cursor.execute('SELECT * FROM WATCHLIST').fetchall():
        gv_watchlistItems.append({"id": item['id'], 
                                "type": item['_type'], 
                                "name": item["_name"], 
                                "image": item["imageURL"], 
                                "dateAdded": item["date_added"], 
                                "dateLastCheck": item["last_time_checked"], 
                                "noOfNewItems": item["new_items_since_last_check"], 
                                "listOfNewItemsID": item["list_of_current_items"],
                                "href": item["href"]})


########################################################################################
def checkWatchlistItems():
    '''--> check every watchlist item for new tracks <--'''
    '''--> Add new tracks to table WatchListNewTracks - trackList'''
    '''--> Create playlists of these tracks of 50 tracks each'''
    '''--> RETURN FALSE IN CASE OF ERROR'''
    logAction("msg - watchlist.py - checkWatchListItems --> starting.") 
    try:
        '''--> db'''
        cursor = get_db().cursor()


    except Exception as ex:
        logAction("err - watchlist.py - checkWatchListItems2 --> error setting up db connection --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return False


    '''--> check if entry in db table WatchListNewTracks exists, before adding tracks to it'''
    try:
        if cursor.execute('SELECT * FROM WatchListNewTracks').fetchone() == None:    #add first entry to db table
            dummyList = []
            get_db().execute('INSERT INTO WatchListNewTracks (id, trackList) VALUES (?,?)',("newTracks", json.dumps(dummyList)))
            get_db().commit()
            logAction("msg - watchlist.py - checkWatchListItems3 --> Initial entry in table WatchListNewTracks created")


    except sqlite3.OperationalError:
        logAction("msg - watchlist.py - checkWatchListItems4 --> error while adding entry in db table WatchListNewTracks")
        return False


    '''--> check watchlist items for new tracks'''
    try:
        for wl_item in cursor.execute('SELECT * FROM WatchList').fetchall():
            actTracks = []  #track ids on spotify
            dbTracks  = []  #track ids in db

            if wl_item["_type"] == "artist":
                actTracks   = getTracksFromArtist(wl_item["id"], False)
            elif wl_item["_type"] == "playlist":
                actTracks   = getTracksFromPlaylist(wl_item["id"], False)
            dbTracks = json.loads(wl_item["list_of_current_items"])     #saved as string (json.dumps), converted to list with json.loads


            '''--> use crc to check for changes'''
            crcactTracks    = binascii.crc32(json.dumps(actTracks).encode('utf8'))
            crcdbTracks     = binascii.crc32(json.dumps(dbTracks).encode('utf8'))


            '''--> set new_items_since_last_check'''
            get_db().execute('UPDATE WatchList SET no_of_items_checked=? WHERE id=?',(len(actTracks) - len(dbTracks), wl_item["id"]))
            get_db().commit()

            if crcactTracks != crcdbTracks:
                '''--> new track(s) found, update db tracklist'''
                get_db().execute('UPDATE WatchList SET list_of_current_items=? WHERE id=?',(json.dumps(actTracks), wl_item["id"]))
                get_db().commit()
                get_db().execute('UPDATE WatchList SET no_of_items_checked=? WHERE id=?',(len(actTracks), wl_item["id"]))
                get_db().commit()


                # '''--> get db tracks for comparison'''
                # response        = getDBTracks("ListenedTrack")
                # response2       = getDBTracks("ToListenTrack")
                # response3       = getDBTracks("WatchListNewTracks")
                # dbTracks        = []

                # if (response["result"] == True) and (response2["result"] == True) and (response3["result"] == True):
                #     dbTracks    = response["response"].copy()
                #     dbTracks.extend(response2["response"])
                #     dbTracks.extend(response3["response"])
                # else:
                #     raise Exception("No valid trackID list received from DB.")

                # '''--> check tracks'''
                # for actTrck in actTracks:
                #     if not actTrck in dbTracks:
                #         #Not in db yet, update tracklist
                #         data                = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone() 
                #         currentTrackList    = json.loads(data[1])           #data = first (and only) row of db table WatchListNewTracks, data[0] = id, data[1] = trackList
                #         toAdd               = {"id": actTrck, "from_type": wl_item["_type"], "from_name": wl_item["_name"]}  
                #         currentTrackList    = currentTrackList + [toAdd]     #add track to existing tracklist
                #         get_db().execute('UPDATE WatchListNewTracks SET trackList=? WHERE id=?',(json.dumps(currentTrackList), "newTracks"))
                #         get_db().commit()

                '''--> check act tracks and add to WatchlistNewTracks'''
                for actTrck in actTracks:
                    if not actTrck in dbTracks:
                        #Not in db yet, update tracklist
                        data                = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone() 
                        currentTrackList    = json.loads(data[1])           #data = first (and only) row of db table WatchListNewTracks, data[0] = id, data[1] = trackList
                        toAdd               = {"id": actTrck, "from_type": wl_item["_type"], "from_name": wl_item["_name"]}  
                        currentTrackList    = currentTrackList + [toAdd]     #add track to existing tracklist
                        get_db().execute('UPDATE WatchListNewTracks SET trackList=? WHERE id=?',(json.dumps(currentTrackList), "newTracks"))
                        get_db().commit()












                # '''--> check act tracks and add to WatchlistNewTracks'''
                # for actTrck in actTracks:
                #     if not checkIfTrackInDB(actTrck,"ListenedTrack") and not checkIfTrackInDB(actTrck, "ToListenTrack") and not checkIfTrackInDB(actTrck, "WatchListNewTracks"):
                #         #Not in db yet, update tracklist
                #         data                = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone() 
                #         currentTrackList    = json.loads(data[1])           #data = first (and only) row of db table WatchListNewTracks, data[0] = id, data[1] = trackList
                #         toAdd               = {"id": actTrck, "from_type": wl_item["_type"], "from_name": wl_item["_name"]}  
                #         currentTrackList    = currentTrackList + [toAdd]     #add track to existing tracklist
                #         get_db().execute('UPDATE WatchListNewTracks SET trackList=? WHERE id=?',(json.dumps(currentTrackList), "newTracks"))
                #         get_db().commit()


                '''--> Set noOfNewItems (new tracks since last 8h)'''
                date_limit = datetime.strptime(str(wl_item["last_time_checked"]),'%Y-%m-%d %H:%M:%S.%f')  + timedelta(hours=8)
                if datetime.now() > date_limit:
                    #more than 8 hours passed since a new item has been added, set noOfNewItems back to 0.
                    get_db().execute('UPDATE WatchList SET new_items_since_last_check=? WHERE id=?',(0, wl_item["id"]))
                    get_db().commit()
                    logAction("msg - watchlist.py - checkWatchListItems5 --> Set new_items_since_last_check for " + wl_item["id"] + " to 0 after 8h.") 


        '''--> Check if enough tracks in table WatchlistNewTracks for creating new playlist'''
        result  = {}
        input   = {"source": "watchlist", "sourceName": "watchlist new tracks", "sourceType": "watchlist", "sourceTracklist": [], "noOfTracksPerCreatedPlaylist": 50, "nameCreatedPlaylist": "spotr_watchlistitems_", "descriptionCreatedPlaylist": "Generated by spotr. "}
        result      = checkSourceAndCreatePlaylist(input)

        if result["result"] == True:
            logAction("msg - watchlist.py - checkWatchListItems5.1 --> Succesfully finished checkSourceAndCreatePlaylist(): " + str(result["noOfTracksInNewPlaylist"]) + " tracks in " + str(result["noOfCreatedPlaylists"]) + " playlist(s) created.")
            flash("Watchlist items done checking for new tracks." +  str(result["noOfCreatedPlaylists"]) + " playlist(s) created containing " + str(result["noOfTracksInNewPlaylist"]) + " tracks.", category="message")
        else:
            logAction("err - watchlist.py - checkWatchListItems5.2 --> error checkToCreatePlaylist()")
            flash("Something went wrong during checkSourceAndCreatePlaylist()!", category="error")
            return False


        '''--> finished succesfully'''
        return True        


    except Exception as ex:
        logAction("err - watchlist.py - checkWatchListItems6 --> error checking watchlist items for new tracks --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return False



