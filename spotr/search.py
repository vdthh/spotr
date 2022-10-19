########################################################################################
###################################### search.py #######################################
############# Search for item (track, playlist, artist, album, user,...) ###############
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from datetime import datetime
from flask import Blueprint, render_template, request, flash
import re   #regex
import json
import traceback
from .common import getTrackInfo, getTracksFromArtist, getTracksFromPlaylist, searchSpotify, apiGetSpotify, logAction, returnSearchResults
from .db import get_db
########################################################################################


########################################################################################
######################################## FLASK INIT ####################################
########################################################################################
bp_search = Blueprint('search', __name__, url_prefix="/search")
########################################################################################


########################################################################################
######################################## VARIABLES #####################################
########################################################################################
gv_searchTerm           = ""
gv_searchType           = "track"   #default value
gv_offset               = ""
gv_limit                = ""
gv_total                = ""
gv_searchResultList     = []
########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
# HTML ROUTING #
@bp_search.route("/", methods=["GET","POST"])
def search_main():
    '''--> main routine'''
    '''--> initialize global variables'''   
    global gv_searchTerm
    global gv_searchType
    global gv_offset
    global gv_limit    
    global gv_total
    global gv_searchResultList


    '''--> read query parameters'''
    args=request.args      


    #--> PAGE LOAD #
    if (request.method == "GET") and not ("offs" in args) and not ("lim" in args) and not ("searchTerm" in args) and not ("searchType" in args):
        '''--> page load'''
        return render_template('search.html', 
                                resList     = gv_searchResultList, 
                                offs        = gv_offset, 
                                lim         = gv_limit, 
                                tot         = gv_total, 
                                searchTerm  = gv_searchTerm, 
                                searchType  = gv_searchType)


    #--> SEARCH ARTIST - BUTTON PRESSED - PAGINATION #
    elif (request.method == "POST" and  ("submit_search" in request.form)) or (request.method == "GET") and ("offs" in args) and ("lim" in args) and ("searchTerm" in args) and ("searchType" in args) and not ("saveTo" in args) and not ("itemId" in args):
        try:
            '''--> pagination or search button press?'''
            if (request.method == "GET") and ("offs" in args) and ("lim" in args) and ("searchTerm" in args) and ("searchType" in args):
                paginReq = True     #pagination pressed
            else:
                paginReq = False    #search butten pressed


            '''--> update variables'''
            if paginReq:
                gv_searchTerm   = gv_searchTerm
                gv_searchType   = gv_searchType
                gv_offset       = int(args["offs"])
                gv_limit        = int(args["lim"])
            else:
                logAction("msg - search.py - search_main --> search button pressed: " + gv_searchTerm + ", " + gv_searchType)
                gv_searchTerm   = request.form["searchinput"]
                gv_searchType   = request.form["select_search_type_radiobtn"]
                gv_offset       = 0
                gv_limit        = 50      


            '''--> api request'''
            response = searchSpotify(gv_searchTerm, gv_searchType, gv_limit, gv_offset)


            '''--> fill result list'''
            gv_searchResultList = returnSearchResults(response, gv_searchType)


            '''--> check response before continuing'''
            if response == '':
                logAction("err - search.py - search_main8 --> empty api response for searching for " + gv_searchType + " " + gv_searchTerm + ".")
                flash("Error when searching for " + gv_searchType + " " + gv_searchTerm + ", empty response.", category="error")
                return render_template('search.html', 
                                        resList     = gv_searchResultList, 
                                        offs        = gv_offset, 
                                        lim         = gv_limit, 
                                        tot         = gv_total, 
                                        searchTerm  = gv_searchTerm, 
                                        searchType  = gv_searchType)


            '''--> retrieve pagination'''
            gv_total       = response[gv_searchType  + 's']['total']
            gv_limit       = response[gv_searchType  + 's']['limit']
            gv_offset      = response[gv_searchType  + 's']['offset']


            '''--> return html'''
            return render_template('search.html', 
                                        resList     = gv_searchResultList, 
                                        offs        = gv_offset, 
                                        lim         = gv_limit, 
                                        tot         = gv_total, 
                                        searchTerm  = gv_searchTerm, 
                                        searchType  = gv_searchType)


        except Exception as ex:
            logAction("err - search.py - search_main10 --> error when searching for " + gv_searchTerm + " --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())


    #--> ADD FOUND ITEM TO DB #
    elif ("itemId" in args) and ("saveTo" in args) and ("offs" in args) and ("lim" in args) and ("searchTerm" in args) and ("searchType" in args):
        try:
            '''--> add selected item to selected db'''
            '''--> get data'''          
            item_id     = args["itemId"]
            saveto      = args["saveTo"]
            searchType  = args["searchType"]


            '''--> which db?'''
            if saveto == "favorite":
                saveToDb = "FavoriteTrack"
            elif saveto == "tolisten":
                saveToDb = "ToListenTrack"


            '''--> what to save?'''
            trackLst = []
            if searchType == "album": 
                response        = apiGetSpotify("albums/" + item_id + "/tracks")        #{"result": True/False, "response": list of playlistlinks, "message": ...}

                if response["result"] == False:
                    logAction("err - search.py - search_main12 --> Bad api response when searching for album tracks.")
                    raise Exception("Bad api response when searching for album tracks.")

                trackLst        = response["response"]["items"]

            elif searchType == "track":
                trackLst.append({"id": item_id})        #add as dict to maintain compatibility with "album" tracklist

            elif searchType == "playlist":
                response        = getTracksFromPlaylist(item_id, False)
                for item in response:
                    trackLst.append({"id": item})       #add as dict to maintain compatibility with "album" tracklist

            elif searchType == "artist":
                response        = getTracksFromArtist(item_id, False)
                for item in response:
                    trackLst.append({"id": item})       #add as dict to maintain compatibility with "album" tracklist


            '''--> save tracks'''
            for item in trackLst:            
                '''--> already in db?''' 
                cursor          = get_db().cursor()
                if cursor.execute('SELECT * FROM ' + saveToDb  + ' WHERE id = ?', (item["id"],)).fetchone() == None:
                    #not in db yet, add
                    '''--> trackinfo'''
                    trackinfo = getTrackInfo(item["id"], True)
                    artists   = ', '.join(trackinfo["artists"])


                    '''--> add to db'''
                    if saveto == "favorite":
                        get_db().execute('INSERT INTO FavoriteTrack (id, spotify_id, album, artists, title, href, times_searched) VALUES (?,?,?,?,?,?,?)',(item["id"], item["id"], item_id, artists, trackinfo["title"], "", 0))
                    elif saveto == "tolisten":
                        get_db().execute('INSERT INTO ToListenTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?)',(item["id"], item["id"], item_id, artists, trackinfo["title"], "", 0, "", 0))
                    get_db().commit()

                else:
                    logAction("msg - search.py - watchlist_main40 --> " + searchType + " " + item["id"] + " already in " + saveToDb + " db.")

            '''--> log'''
            flash(searchType + " " + item_id + " added to " + saveToDb + " db.", category="message")
            logAction("msg - watchlist.py - watchlist_main --> " + searchType + " " + item_id + " added to " + saveToDb + " db.")

            return render_template('search.html', 
                            resList     = gv_searchResultList, 
                            offs        = gv_offset, 
                            lim         = gv_limit, 
                            tot         = gv_total, 
                            searchTerm  = gv_searchTerm, 
                            searchType  = gv_searchType)

        except Exception as ex:
            logAction("err - search.py - search_main45 --> error when adding " + searchType + " " + item["id"] + " to " + saveToDb + " db --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())

            return render_template('search.html', 
                            resList     = gv_searchResultList, 
                            offs        = gv_offset, 
                            lim         = gv_limit, 
                            tot         = gv_total, 
                            searchTerm  = gv_searchTerm, 
                            searchType  = gv_searchType)

########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################


########################################################################################