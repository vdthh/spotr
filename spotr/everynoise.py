########################################################################################
#################################### everynoise.py #####################################
################# Use the everynoise sebsite to explore music by genre #################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from pickletools import read_string1
import traceback
from .db import get_db
from urllib.parse import urlencode
from flask import Blueprint, render_template, request, flash, redirect, url_for
from pip._vendor import requests
import re
from .common import addTracksToPlaylist, apiGetSpotify, changePlaylistDetails, checkIfTrackInDB, getTracksFromArtist, getTracksFromPlaylist, searchSpotify, returnSearchResults, getTrackInfo, createPlaylist, waitForGivenTimeIns, logAction, checkSourceAndCreatePlaylist
from datetime import datetime
import os
import json
import sqlite3
########################################################################################


########################################################################################
######################################## FLASK INIT ####################################
########################################################################################
bp_everynoise = Blueprint('everynoise', __name__, url_prefix="/everynoise")
########################################################################################


########################################################################################
######################################## VARIABLES #####################################
########################################################################################
gv_savedGenres          = ""
gv_playlistLinks        = ""
gv_searchResultList     = []
gv_searchArtistName     = ""
########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
# HTML ROUTING #
@bp_everynoise.route("/", methods=["GET","POST"])
def everynoise_main():
    '''--> main routine'''
    '''--> initialize global variables''' 
    global gv_savedGenres
    global gv_playlistLinks
    global gv_searchResultList
    global gv_searchArtistName


    '''--> read query parameters'''
    args=request.args    


    if request.method == "GET" and not ("genre" in args) and not ("link" in args) and not ("toDelete" in args) and not ("linkToPlaylist" in args) and not ("nameOfPlaylist" in args)  and not ('submit_everynoise_search' in request.form):
    #--> PAGE LOAD #
        try:
            '''--> page load'''
            '''--> refresh values'''
            refreshValues()


            '''--> return html'''
            return render_template("everynoise.html", 
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)

        except Exception as ex:
            logAction("err - everynoise.py - everynoise_main()0 --> loading page --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            return render_template("everynoise.html")

    elif ('submit_everynoise_search' in request.form) and (request.method == 'POST'):
    #--> SEARCH ARTIST - BUTTON PRESS #
        try:
            '''--> get artist name'''
            gv_searchArtistName     = request.form["search_everynoiseinput"]


            '''--> initialize variables'''
            gv_searchResultList      = []


            '''--> perform search job on everynoise.com'''
            gv_searchResultList      = searchEverynoise(gv_searchArtistName)


            '''--> evaluate result'''
            if len(gv_searchResultList) != 0:
                return render_template("everynoise.html", 
                                        savedList           = gv_savedGenres, 
                                        playlists           = gv_playlistLinks, 
                                        searchResultList    = gv_searchResultList,    
                                        searchedArtistName  = gv_searchArtistName)
            else:
                logAction("msg - everynoise.py - everynoise_main30 --> no genres found for artist " + gv_searchArtistName + ".")
                flash("No genres found for artist " + gv_searchArtistName + "!" , category="message")
                return render_template("everynoise.html",                                     
                                        savedList           = gv_savedGenres, 
                                        playlists           = gv_playlistLinks, 
                                        searchResultList    = gv_searchResultList,    
                                        searchedArtistName  = gv_searchArtistName)

        except Exception as ex:       
                logAction("err - everynoise.py - everynoise_main34 --> Something went wrong when searching genres for artist " + gv_searchArtistName + ". --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
                logAction("TRACEBACK --> " + traceback.format_exc())
                flash("Something went wrong when searching genres for artist " + gv_searchArtistName + "!", category="error")
                return render_template("everynoise.html",                                     
                                        savedList           = gv_savedGenres, 
                                        playlists           = gv_playlistLinks, 
                                        searchResultList    = gv_searchResultList,    
                                        searchedArtistName  = gv_searchArtistName)


    elif ("genre" in args) and ("link" in args) and not ("toDelete" in args):
    #--> ADD GENRE - BUTTON PRESS #
        try:
            '''--> add clicked, add genre to db EverynoiseGenre'''
            '''--> retrieve user input'''
            genreName       = args["genre"]
            link            = args["link"]


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> check and add to EverynoiseGenreDB'''
            cursor.execute('SELECT * FROM EverynoiseGenre WHERE genre=?', (genreName,))
            if cursor.fetchone() == None:
                #not in db
                get_db().execute('INSERT INTO EverynoiseGenre (genre, link) VALUES (?,?)',(genreName, link))
                get_db().commit()
                logAction("msg - everynoise.py - everynoise_main40 --> genre " + genreName + " added to EverynoiseGenre db.")
                flash("Genre " + genreName + " added to EverynoiseGenre db.", category="message")
            else:
                #in db
                logAction("msg - everynoise.py - everynoise_main44 --> genre " + genreName + " already in EverynoiseGenre db.")


            '''--> refresh values'''
            refreshValues()


            '''--> return html'''
            return render_template("everynoise.html",                                     
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)

        except Exception as ex:
            logAction("err - everynoise.py - everynoise_main38 --> Something went wrong when adding genre " + genreName + " to db EverynoiseGenre --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Something went wrong when adding genre " + genreName + " to db EverynoiseGenre!", category="error")
            return render_template("everynoise.html",                                     
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)


    elif not ("genre" in args) and not ("link" in args) and ("toDelete" in args):
    #--> DELETE GENRE - BUTTON PRESS #
        try:
            '''--> delete clicked, delete genre from db EverynoiseGenre'''
            '''--> retrieve user input'''
            genreName       = args["toDelete"]


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> check and delete from EverynoiseGenreDB'''
            cursor.execute('SELECT * FROM EverynoiseGenre WHERE genre=?', (genreName,))
            if cursor.fetchone() == None:
                #not in db
                logAction("err - everynoise.py - everynoise_main50 --> genre " + genreName + " not in EverynoiseGenre db, not deleted!.")
            else:
                #in db
                get_db().execute('DELETE FROM EverynoiseGenre WHERE genre LIKE ?', (genreName,))
                get_db().commit()
                logAction("msg - everynoise.py - everynoise_main44 --> genre " + genreName + " deleted from EverynoiseGenre db.")
                flash("genre " + genreName + " deleted from EverynoiseGenre db!", category="message")


            '''--> refresh values'''
            refreshValues()
            

            '''--> return html'''
            return render_template("everynoise.html",                                    
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)


        except Exception as ex:
            logAction("err - everynoise.py - everynoise_main52 --> Something went wrong when deleting genre " + genreName + " to db EverynoiseGenre --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Something went wrong when adding genre " + genreName + " to db EverynoiseGenre!", category="error")
            return render_template("everynoise.html",                                     
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)


    elif ("linkToPlaylist" in args) and ("nameOfPlaylist" in args) and ("genreName" in args) and not ("linkToPlaylist_addToWatchlist" in args):
    #--> CREATE PLAYLIST(S) FROM ONE OF THE EVERYNOUSE.COM-GENRE PLAYLIST- BUTTON PRESS #
    #--> FOR EXAMPLE: 'INTRO' PLAYLIST FOR SOME GENRE #
        try:
            '''--> retrieve data'''
            link        = args["linkToPlaylist"]   #example: https://open.spotify.com/playlist/0OGpuF8rnCzlcjJLsdywny
            name        = args["nameOfPlaylist"]   #example: playlist, intro, scan,...
            genreName   = args["genreName"]        #example: pop, uk-pop, rock,..


            '''--> extract playlist ID from link'''
            regex                   = re.search("playlist\D(.+)", link)
            toGrabPlaylistID        = regex.group(1)


            '''--> grab playlist tracks (ID's only)'''
            tracks          = getTracksFromPlaylist(toGrabPlaylistID, False)


            '''--> create playlist(s)?'''
            response        = {}
            input           = {"source": "trackIdList", "sourceName": "everynoise - " + genreName, "sourceType": "playlist", "sourceTracklist": tracks, "noOfTracksPerCreatedPlaylist": 50, "nameCreatedPlaylist": "spotr_everynoise_" + name + "_" + genreName, "descriptionCreatedPlaylist": "Generated by spotr. "}
            response        = checkSourceAndCreatePlaylist(input)   #returns dict

            
            '''--> check response'''
            '''--> checkSourceAndCreatePlaylist() returns a dict'''
            '''--> e.g. {"result": True/False, "message": e.g. "Added tracks to playlist.", "response": json result of 'addTracksToPlaylist', "noOfTracksInNewPlaylist": total tracks, "noOfCreatedPlaylists": ...}'''
            if response["result"] == False:
                #failed response, leave
                logAction("msg - everynoise.py - everynoise_main100 --> Negative response from checkSourceAndCreatePlaylist()")
                flash("Negative response from checkSourceAndCreatePlaylist()!", category="error")
                raise Exception(response["message"])
            else:
                #pass
                logAction("msg - everynoise.py - everynoise_main110 --> feedback from checkSourceAndCreatePlaylist() --> " + response["message"])

            '''--> refresh values'''
            refreshValues()


            '''--> how many playlists created?'''
            totalPlaylists = 0
            if "noOfCreatedPlaylists" in response.keys():
                totalPlaylists     = response["noOfCreatedPlaylists"]
            else:
                totalPlaylists     = 0


            '''--> how many tracks in created playlist(s)?'''
            totalTracks = 0
            if "noOfTracksInNewPlaylist" in response.keys():
                totalTracks     = response["noOfTracksInNewPlaylist"]
            else:
                totalTracks     = 0


            '''--> log'''
            if totalTracks != 0:
                logAction("msg - everynoise.py - everynoise_main65 --> Done creating playlist(s) from everynoise.com-genre " + genreName + ", total of " + str(totalTracks) + " tracks in created playlist(s).")
                flash("Checked playlist \"" + name + "\" for everynoise.com-genre \"" + genreName + "\"! " +  str(totalPlaylists) + " playlist(s) created containing " + str(totalTracks) + " tracks.", category="message")
            else:
                logAction("msg - everynoise.py - everynoise_main66 --> None playlist(s) from everynoise.com-genre " + genreName + " - all tracks in ListenedDB!")
                flash("No playlist(s) for everynoise.com-genre " + genreName + " created, all tracks in ListenedDB!", category="message")


            '''--> return html'''
            return render_template("everynoise.html",                                    
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)

            # else:
            #     #negative response
            #     logAction("msg - everynoise.py - everynoise_main64 --> Failed call off checkToCreatePlaylist2 for genre " + genreName + "!")
            #     flash("checkToCreatePlaylist2 call failed for genre " + genreName + "!", category="error")

            #     '''--> return html'''
            #     return render_template("everynoise.html",                                    
            #                             savedList           = gv_savedGenres, 
            #                             playlists           = gv_playlistLinks, 
            #                             searchResultList    = gv_searchResultList,    
            #                             searchedArtistName  = gv_searchArtistName)


        except Exception as ex:
            logAction("err - everynoise.py - everynoise_main70 --> Something went wrong when creating playlist " + name + "--> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Something went wrong when creating playlist " + name + "!", category="error")
            return render_template("everynoise.html",                                     
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)


    elif not ("linkToPlaylist" in args) and ("nameOfPlaylist" in args) and ("genreName" in args) and ("linkToPlaylist_addToWatchlist" in args):
    #--> FOLLOW THE CLICKED EVERYNOUSE.COM-GENRE PLAYLIST (ADD TO WATCHLIST)- BUTTON PRESS #
        try:
            '''--> retrieve data'''
            link        = args["linkToPlaylist_addToWatchlist"]   #example: https://open.spotify.com/playlist/0OGpuF8rnCzlcjJLsdywny
            name        = args["nameOfPlaylist"]                  #example: playlist, intro, scan,...
            genreName   = args["genreName"]                       #example: pop, uk-pop, rock,..


            '''--> extract playlist ID from link'''
            regex                   = re.search("playlist\D(.+)", link)
            toGrabPlaylistID        = regex.group(1)


            '''--> get details'''
            response = apiGetSpotify("playlists/" + toGrabPlaylistID)       #{"result": True/False, "response": list of playlistlinks, "message": ...}


            '''--> check response before continuing'''
            if response["result"] == False:
                logAction("err - everynoise.py - everynoise_main71--> empty api response when grabbing details for playlist " + toGrabPlaylistID + ". Message: " + response["message"] + ".")
                flash("Error when grabbing details for for playlist " + toGrabPlaylistID + ", empty response.", category="error")


            '''--> db'''
            cursor          = get_db().cursor()


            '''--> in watchlist yet?'''
            if cursor.execute('SELECT id FROM WatchList WHERE id = ?', (toGrabPlaylistID,)).fetchone() == None:
                pass    #not in watchlist yet
            else:       #leave
                logAction("msg - everynoise.py - everynoise_main72 --> playlist" + name + " " + toGrabPlaylistID  + " from everynoise.com-genre " + genreName + " already in watchlist.")
                flash("Playlist" + name + " " + toGrabPlaylistID  + " from everynoise.com-genre " + genreName + " already in watchlist.", category="message")

                return render_template("everynoise.html",                                     
                        savedList           = gv_savedGenres, 
                        playlists           = gv_playlistLinks, 
                        searchResultList    = gv_searchResultList,    
                        searchedArtistName  = gv_searchArtistName)


            '''--> grab tracks'''
            tracklist       = getTracksFromPlaylist(toGrabPlaylistID, False)
            logAction("msg - everynoise.py - everynoise_main74 --> grabbed " + name + " " + genreName + "'s tracks: " + str(len(tracklist)))


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
                logAction("msg - everynoise.py - everynoise_main76 --> error while adding entry in db table WatchListNewTracks")


            '''--> add artist/playlist/... to WatchList db'''
            get_db().execute(
                'INSERT INTO WatchList (id, _type, _name, last_time_checked, no_of_items_checked, href, list_of_current_items, imageURL, new_items_since_last_check) VALUES (?,?,?,?,?,?,?,?,?)', 
                (toGrabPlaylistID, "playlist", "everynoise.com-genre " + genreName + " - " + name, datetime.now(), len(tracklist), response["response"]["external_urls"]["spotify"], json.dumps(tracklist), imglink, len(tracklist))
            )
            get_db().commit()
            logAction("msg - everynoise.py - everynoise_main78 --> playlist " + name + " from everynoise.com-genre " + genreName + " added to watchlist.")
            flash("everynoise.com-genre " + genreName + " - " + name + " added to watchlist.", category="message")


            '''--> add artist/playlist/... tracks to WatchListNewTracks'''
            '''check tracks if in db'''
            data                = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone() 
            currentTrackList    = json.loads(data[1])
            initLength          = len(currentTrackList)
            endLength           = 0

            for trck in tracklist:
                if not checkIfTrackInDB(trck, "ListenedTrack") and not checkIfTrackInDB(trck, "ToListenTrack") and not checkIfTrackInDB(trck, "WatchListNewTracks"):
                    #Not in db yet, update tracklist
                    data                = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone() 
                    currentTrackList    = json.loads(data[1])           #data = first (and only) row of db table WatchListNewTracks, data[0] = id, data[1] = trackList
                    toAdd               = {"id": trck, "from_type": "playlist", "from_name": "everynoise.com-genre " + genreName + " - " + name}  
                    currentTrackList    = currentTrackList + [toAdd]     #add track to existing tracklist
                    endLength           = len(currentTrackList) 
                    get_db().execute('UPDATE WatchListNewTracks SET trackList=? WHERE id=?',(json.dumps(currentTrackList), "newTracks"))
                    get_db().commit()
            logAction("msg - everynoise.py - everynoise_main80 --> Finished - tracks in tracklist before adding everynoise.com-genre " + name + " " + genreName + ": " + str(initLength) + ", length after adding tracks: " + str(endLength) + ".")
            flash(str(endLength - initLength) + " tracks added to WatchListNewTracks (total of " +  str(endLength) + ").", category="message")                               


            '''--> return html'''
            return render_template("everynoise.html",                                    
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)


        except Exception as ex:
            logAction("err - everynoise.py - everynoise_main80 --> Something went wrong when adding playlist from everynoise.com-genre to watchlist " + name + "--> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error when adding playlist from everynoise.com-genre " + name + " to watchlist!", category="error")
            return render_template("everynoise.html",                                     
                                    savedList           = gv_savedGenres, 
                                    playlists           = gv_playlistLinks, 
                                    searchResultList    = gv_searchResultList,    
                                    searchedArtistName  = gv_searchArtistName)

########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
def getPlaylistLinksForGenre(link, genreName):
    '''--> grab suggested playlist links from everynoise site for a given genre'''
    '''--> example of site's html:'''
    '''...<a style="color: #a6a6a6" href="https://open.spotify.com/user/particledetector/playlist/1y3xutKspHqFSvEpL8GD5N" title="listen to a shorter introduction to this genre">intro</a>\n&nbsp;...'''
    '''...<a style="color: #b4b4b4" href="https://open.spotify.com/user/particledetector/playlist/0YqU5nKvW037W4RkqpnKvx" title="listen to this genre\'s fans\' current favorites">pulse</a>\n&nbsp;...'''
    ''' Returns a list of dicts "name":, "description":, "genre":, "link":'''
    '''--> returns false in case of error'''

    try:
        '''--> initialize variables'''
        resultList      = []


        '''--> check url - valid url looks like this - https://everynoise.com/engenremap-moderndreampop.html'''
        url = ""
        if link.startswith("everynoise.com") or link.startswith("https://everynoise.com") or link.startswith("http://everynoise.com"):
            url = link
        else:
            #probably link is something like 'engenremap-chillhop.html'
            url = 'https://everynoise.com/' + link
        logAction("msg - everynoise.py - everynoise_main60 --> grabbing playlist link for genre " + genreName + ".")


        '''--> request'''
        r                   = requests.get(url = url, verify=False)
        r_status_code       = str(r.status_code)
        r_string            = r.text


        '''--> write request response for analyzing purposes'''
        with open (os.path.dirname(os.path.abspath(__file__)) + "/logs/everynoise_GetGenreLinksLAST.json", 'w', encoding="utf-8") as fi:
            fi.write(r.text)


        '''--> grab playlist links from raw string'''
        pl_link         = ""
        pl_descript     = ""
        pl_name         = ""
        pl_noOfTracks   = ""
        regexSearch     = re.search('''<a style="color:\s#[a-z0-9]*"\shref="([^"]*)"\stitle="([^"]*)">([^<]*)''', r_string)
        pl_link         = regexSearch.group(1)      #example: https://open.spotify.com/playlist/0OGpuF8rnCzlcjJLsdywny OR  https://open.spotify.com/user/particledetector/playlist/5HO6WUlXZgCexcoW2bQ7Le
        pl_descript     = regexSearch.group(2)      #example: listen to The Sound of UK Pop on Spotify
        pl_name         = regexSearch.group(3)      #Values: playlist, intro, pulse, edge and 2020 - so 5 key/value per genre


        '''--> api request for playlist details'''
        # regexSearch     = re.search('''/playlist/([a-zA-Z0-9]+)''', pl_link)  #grab playlist ID
        # result          = apiGetSpotify("playlists/" + regexSearch.group(1))
        # pl_noOfTracks   = int(result["tracks"]["total"])

        resultList.append({"name": pl_name, "description": pl_descript, "genre": genreName, "link": pl_link, "noOfTracks": pl_noOfTracks})

        #continue loop to grab other links
        #find end pos of actual part of interest
        pos1 = r_string.find(pl_name) + len(pl_name)
        r_string = r_string[pos1:]


        '''--> loop to grab all links'''
        while pl_link != "":
            regexSearch = re.search('''<a style="color:\s#[a-z0-9]*"\shref="([^"]*)"\stitle="([^"]*)">([^<]*)''', r_string)
            if type(regexSearch) == type(None):
                break   #exit loop if nothing is found --> end of loop
            pl_link         = regexSearch.group(1)
            pl_descript     = regexSearch.group(2)
            pl_name         = regexSearch.group(3)


            '''--> api request for playlist details'''
            # regexSearch     = re.search('''/playlist/([a-zA-Z0-9]+)''', pl_link)  #grab playlist ID
            # result          = apiGetSpotify("playlists/" + regexSearch.group(1))
            # pl_noOfTracks   = int(result["tracks"]["total"])

            pos1 = r_string.find(pl_name) + len(pl_name)
            r_string = r_string[pos1:]  #prepare string for next loop

            resultList.append({"name": pl_name, "description": pl_descript, "genre": genreName, "link": pl_link, "noOfTracks": pl_noOfTracks})

        return resultList

    except Exception as ex:
        logAction("err - everynoise.py - everynoise_main62 --> Something went wrong when grabbing playlist links for genre " + genreName + " --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        flash("Something went wrong when grabbing playlist links for genre " + genreName + "!", category="error")
        return False

########################################################################################
def searchEverynoise(artistName):
    '''--> search genres for given artist'''
    '''--> returns list of dicts {genre:link}'''
    '''--> returns empty list if no genres found'''
    '''--> returns '' in case of error'''

    try:
        '''--> initialize variables'''
        resultList      = []


        '''--> request'''
        url                 = "http://everynoise.com/lookup.cgi?who=" + artistName + "&mode=map"
        r                   = requests.get(url = url, verify=False)
        r_status_code       = str(r.status_code)
        r_string            = r.text


        '''--> write request response for analyzing purposes'''
        with open (os.path.dirname(os.path.abspath(__file__)) + "/logs/everynoise_searchEverynoiseLAST.json", 'w', encoding="utf-8") as fi:
            fi.write(r.text)


        '''--> check request result'''
        if r_string.find("Sorry, that one") == -1:  #in case nothing was found, this text line is included in response
            #extract genrenames + links
            regexGenres     = re.search("target=_parent>([a-z-\s]+)<", r_string)
            regexLinks      = re.search("<a href=\"engenremap-([a-z-\s+]+)", r_string)
            resultGenre     = regexGenres.group(1)
            resultLink      = "http://everynoise.com/engenremap-" + re.sub(" ", "", regexLinks.group(1)) + ".html"
            resultList.append({resultGenre:resultLink})

            '''--> loop if more genres are found'''
            while resultGenre != "":
                pos1            = r_string.find(">" + resultGenre + "<")
                r_string        = r_string[(pos1 + len(resultGenre)):]
                regexGenres     = re.search("target=_parent>([a-z-\s]+)<", r_string)
                regexLinks      = re.search("<a href=\"engenremap-([a-z-\s+]+)", r_string)
                if regexGenres != None:
                    resultGenre = regexGenres.group(1)
                    resultLink  = "http://everynoise.com/engenremap-" + re.sub(" ", "", regexLinks.group(1)) + ".html"
                    resultList.append({resultGenre:resultLink})
                else:
                    resultGenre = ""
                    resultLink  = ""
            return resultList    
        else:
            #no genres found
            return []

    except Exception as ex:
        return ''

########################################################################################
def refreshValues():
    '''--> reload global variables'''
    '''--> call this before page reload or render/redirect/...'''
    '''--> initialize variables'''
    global gv_savedGenres
    global gv_playlistLinks

    gv_savedGenres      = []        #list of dict: {"genre":, "link": }
    gv_playlistLinks    = []        #list of dict: {"name":, "description":, "genre":, "link":}


    '''--> db'''
    gv_savedGenres      = get_db().execute('SELECT * FROM EverynoiseGenre').fetchall()


    '''--> grab genre details'''
    for item in gv_savedGenres:
        list1 = []
        list1 = getPlaylistLinksForGenre(item["link"], item["genre"])
        if list1 == False:
            logAction("err - everynoise.py - refreshValues --> Something went wrong when refreshing values.")
            flash("Something went wrong when refreshing values!", category="error")
            break
        else:              
            for listItem in list1:
                gv_playlistLinks.append(listItem) #dict: {"name":, "description":, "genre": }