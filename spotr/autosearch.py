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
from .common import checkIfTrackInDB, logAction, getTracksFromPlaylist, getTrackInfo, googleSearchApiRequest, extractItemsFromGoogleResponse, checkIfTracksInPlaylist, checkIfTrackInDB_test, apiGetSpotify, createPlaylist, addTracksToPlaylist, waitForGivenTimeIns, googleSearchRetryContinueQuit
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
# gv_playlistToAnalyseID          = "4wC748pDf0gHnJRFyzb4l9"  #spotr_toAnalyze
gv_playlistToAnalyseID          = "7rUTMu5Ro26tIKyLYmSIkc"  #spotr_toAnalyze_test
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

        try:
            '''--> initialize variables'''
            response                = {}
            count_new_playlists     = 0
            global gv_searchResults


            '''--> fill/update toAnalyzeTracks list'''
            syncToAnalyzeTracks()


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


            '''--> update gv'''
            gv_searchResults        = response["response"]


        except Exception as ex:
            logAction("err - autosearch.py - autosearch_main start autosearchjob 140 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error performing searchForPlaylistsContainingTracks() - manually initiated. See log for details.", category="error")
            return render_template('autosearch.html', 
                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                        searchResult            = gv_searchResults)


        '''--> return html'''
        logAction("msg - autosearch.py - autosearch_main start searchjob 150 --> finished searchForPlaylistsContainingTracks() manually initiated! Found " + str(len(response["response"])) + " playlists, " + str(count_new_playlists) + " new playlists were saved.")
        flash("Finished searchForPlaylistsContainingTracks() manually initiated! Found " + str(len(response["response"])) + " playlists, " + str(count_new_playlists) + " new playlists were saved.", category="message")
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
            response_1          = {}
            response_2          = {}
            response_3          = {}


            '''--> db'''
            cursor = get_db().cursor()


            '''--> fill/update toAnalyzeTracks list'''
            syncToAnalyzeTracks()


            '''--> create list with searchterms'''
            response_1           = gcs_createSearchTerms()       # returns list of {"searchterm":, "trackid1":, "trackid2":, "item1_timessearched":}


            '''--> check result'''
            if response_1["result"] == False:
                flash("gcs_createSearchTerm aborted --> " + response_1["message"], category="error")
                return render_template('autosearch.html', 
                                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                        searchResult            = gv_searchResults)

            else:
                pass


            '''--> search for playlists'''
            response_2          = gcs_searchPlaylists(response_1["response"])    # returns list of {"playlistlink", "trackid1": ,"trackid2": }


            '''--> check result'''
            if response_2["result"] == False:
                flash("gcs_searchPlaylists aborted --> " + response_2["message"], category="error")
                return render_template('autosearch.html', 
                                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                        searchResult            = gv_searchResults)

            # elif response_2["message"] == "Daily rate limit exceeded.":
            #     '''--> daily rate limit exceeded, save and extract results before quit'''
            #     pass

            else:
                # pass
                flash("Finished searching for playlists!", category="message")
                return render_template('autosearch.html', 
                                        likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
                                        searchResult            = gv_searchResults)            #     flash("Finished searching for playlists!", category="message")


            # '''--> analyze and save results'''
            # response_3          = gcs_checkAndSaveResults(response_2["response"])


            # '''--> check result'''
            # if response_3["result"] == False:
            #     flash("gcs_checkAndSaveResults aborted --> " + response_3["message"], category="error")
            #     return render_template('autosearch.html', 
            #                             likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
            #                             searchResult            = gv_searchResults)

            # else:
            #     flash("Finished searching for playlists!", category="message")
            #     return render_template('autosearch.html', 
            #                             likedTracksList         = cursor.execute('SELECT * FROM ToAnalyzeTracks').fetchall(),
            #                             searchResult            = gv_searchResults)



        except Exception as ex:
            logAction("err - autosearch.py - autosearch_main start autosearchjob 40 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error performing searchForPlaylistsContainingTracks(). See log for details.", category="error")
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
def gcs_createSearchTerms():
    '''--> create searchterms based on the tracks in ToAnalyzeTracks db'''
    '''--> returns list of {"searchterm":, "trackid1":, "trackid2":, "item1_timessearched":}'''
    '''--> no db updates are done here, nor is anything saved!'''

    try:
        '''--> initialize variables'''
        lstSearchTerms          = []
        i1                      = 0
        i2                      = 0
        item1                   = {}
        item1_timessearched     = 0
        item2                  = {}
        search_string           = ""

        toReturnResult          = False
        toReturnResponse        = []
        toReturnMessage         = ""


        '''--> check source'''
        if len(gv_actdbTracks) == 0:
            #quit
            logAction("err - autosearch.py - gcs_createSearchTerms() 5 --> Source tracklist 'gv_actdbTracks' contains 0 tracks.")
            toReturnResult      = False
            toReturnResponse    = []
            toReturnMessage     = "Source tracklist 'gv_actdbTracks' contains 0 tracks."

            toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
            return toReturn


        '''--> loop through gv_actDBTracks'''
        '''--> and so create searchTerms'''   
   
        for i1 in range(0, len(gv_actdbTracks)):            #list of {"id": , "title": , "artists": , "times_searched": }
            item1       = gv_actdbTracks[i1]  

            if (item1["times_searched"] == None):
                #value not initialized yet
                item1_timessearched     = 0
            else:
                #normal situation, get value from db
                item1_timessearched     = int(item1["times_searched"])

            for i2 in range(i1 + item1_timessearched + 1, len(gv_actdbTracks)):
                item2       = gv_actdbTracks[i2]  
                search_string = item1["artists"] + " " + item1["title"] + " " + item2["artists"] + " " + item2["title"]

                '''--> add to result list'''
                lstSearchTerms.append({"searchterm": search_string, "trackid1": item1["id"], "trackid2": item2["id"], "item1_timessearched": item1_timessearched})
                logAction("msg - autosearch.py - gcs_createSearchTerms() 10 --> searchTerm created: " + str(search_string) + ", i1=" + str(i1) + ", i2=" +str(i2) + ", item1_timessearched=" + str(item1_timessearched) + ".")
         
            # '''calculate resting tracks in playlists after item1'''
            # rest_tracks             = len(gv_actdbTracks) -1 - i1 - item1_timessearched

            # print("rest tracks for " + item1["title"] + ": " + str(rest_tracks) + ", i1= " + str(i1) + ", item1_timessearched= " + str(item1_timessearched))

            # if rest_tracks > 0:
            #     for i2 in range(0, rest_tracks):
            #         reversed_list           = gv_actdbTracks.reverse()
            #         item2                   = gv_actdbTracks[i2]  

            #         search_string = item1["artists"] + " " + item1["title"] + " " + item2["artists"] + " " + item2["title"]
            #         print("--------i1: " + str(i1) + ", i2: " + str(i2) + ", search_string: " + search_string)
            # else:
            #     for i2 in range(i1, len(gv_actdbTracks)):
            #         item2                   = gv_actdbTracks[i2]  

            #         search_string = item1["artists"] + " " + item1["title"] + " " + item2["artists"] + " " + item2["title"]
            #         print("**********i1: " + str(i1) + ", i2: " + str(i2) + ", search_string: " + search_string)


            # if item1_timessearched < len(gv_actdbTracks):
            #         #for this track, not all searches have been performed yet

            #     for i2 in range(item1_timessearched, len(gv_actdbTracks)):
            #         item2       = gv_actdbTracks[i2]

            #         '''--> increase item1 timescounter'''
            #         times_counter       +=1
            #         '''--> create searchstring'''
            #         search_string = item1["artists"] + " " + item1["title"] + " " + item2["artists"] + " " + item2["title"]
            #         logAction("msg - autosearch.py - gcs_createSearchTerms() 10 --> searchTerm created: " + str(search_string) + ", i1=" + str(i1) + ", i2=" +str(i2) + ", item1_timessearched=" + str(times_counter) + ".")


            #         '''--> add to result list'''
            #         lstSearchTerms.append({"searchterm": search_string, "trackid1": item1["id"], "trackid2": item2["id"], "item1_timessearched": times_counter})




        # for i1 in range(0, len(gv_actdbTracks) - 1):            #list of {"id": , "title": , "artists": , "times_searched": }
        #     item1       = gv_actdbTracks[i1]  

        #     if (item1["times_searched"] == None):
        #         #value not initialized yet
        #         item1_timessearched     = i1 + 1
        #     else:
        #         if int(item1["times_searched"]) <= i1:
        #             #this should be prevented at all time
        #             item1_timessearched     = i1 + 1
        #         else:
        #             #normal situation, get value from db
        #             item1_timessearched     = int(item1["times_searched"])

        #     times_counter   = item1_timessearched

        #     if item1_timessearched < len(gv_actdbTracks):
        #             #for this track, not all searches have been performed yet

        #         for i2 in range(item1_timessearched, len(gv_actdbTracks)):
        #             item2       = gv_actdbTracks[i2]

        #             '''--> increase item1 timescounter'''
        #             times_counter       +=1
        #             '''--> create searchstring'''
        #             search_string = item1["artists"] + " " + item1["title"] + " " + item2["artists"] + " " + item2["title"]
        #             logAction("msg - autosearch.py - gcs_createSearchTerms() 10 --> searchTerm created: " + str(search_string) + ", i1=" + str(i1) + ", i2=" +str(i2) + ", item1_timessearched=" + str(times_counter) + ".")


        #             '''--> add to result list'''
        #             lstSearchTerms.append({"searchterm": search_string, "trackid1": item1["id"], "trackid2": item2["id"], "item1_timessearched": times_counter})


        '''--> return result'''
        logAction("msg - autosearch.py - gcs_createSearchTerms() 20 --> Searchterms created: " + str(len(lstSearchTerms)) + " terms created in list.")
        toReturnResult      = True
        toReturnResponse    = lstSearchTerms
        toReturnMessage     = "Searchterms created: " + str(len(lstSearchTerms)) + " terms created in list."

        toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn


    except Exception as ex:
        logAction("err - autosearch.py - gcs_createSearchTerms() 100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        toReturnResult      = False
        toReturnResponse    = []
        toReturnMessage     = "Error performing gcs_createSearchTerms(). See log for details."

        toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn
########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
def gcs_performSearchJob(iGcs_response, iSearchterm, iStartindex):
    '''--> perform searchjob for ove given searchstring'''
    '''--> return bad or good response'''
    '''--> response --> {"searchterm":,"resultTotal":,"resultCount":,"resultStartIndex": ,"resultJson":}'''

    try:
        '''--> initialize variables'''
        toReturnResult          = False
        toReturnResponse        = {}
        toReturnMessage         = ""

        gcsCheck_response       = {}
        gcs_response            = ""

        act_retries             = 0
        max_retries             = 10

        resultTotalFound        = 0
        resultCountItems        = 0
        resultStartIndex        = 0
        resultSearchterm        = ""


        '''--> check sources''' 
        if iGcs_response == "":
            logAction("err - autosearch.py - gcs_performSearchJob() 5 --> Input 'iGcs_response' is empty.")
            toReturnResult      = False
            toReturnResponse    = {}
            toReturnMessage     = "Input 'iGcs_response' is empty."

            toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
            return toReturn
        
        elif iSearchterm == "":            
            logAction("err - autosearch.py - gcs_performSearchJob() 6 --> Input 'iSearchterm' is empty.")
            toReturnResult      = False
            toReturnResponse    = {}
            toReturnMessage     = "Input 'iSearchterm' is empty."

            toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
            return toReturn


        '''--> check response: Retry? Quit?  Continue?'''
        gcs_response            = iGcs_response
        gcsCheck_response       = googleSearchRetryContinueQuit(gcs_response)       #{"result": true/false, "response": quit/retry/continue, "message":... }

        if gcsCheck_response["result"] == True:
            '''--> retry or continue'''
            if gcsCheck_response["response"] == "continue":
                pass

            elif gcsCheck_response["response"] == "retry":
                '''--> new google search request'''
                gcs_response            = ""
                gcs_response            = googleSearchApiRequest(iSearchterm, startIndex = iStartindex)

                '''--> Retry? Quit?  Continue?'''
                gcsCheck_response       = {}
                gcsCheck_response       = googleSearchRetryContinueQuit(gcs_response)       #{"result": true/false, "response": quit/retry/continue, "message":... 

                '''--> keep checking'''
                while gcsCheck_response["response"] != "continue":
                    logAction("msg - autosearch.py - gcs_performSearchJob() 25 --> retrying attempt " + str(act_retries) + ".")


                    if gcsCheck_response["response"] == "quit":
                        '''--> quit'''
                        logAction("err - autosearch.py - gcs_performSearchJob() 30 --> quit.")
                        toReturnResult      = False
                        toReturnResponse    = {}
                        toReturnMessage     = "Quitted autosearch --> " + gcsCheck_response["message"]

                        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                        return toReturn

                    elif act_retries >= max_retries:
                        '''--> quit'''
                        logAction("err - autosearch.py - gcs_performSearchJob() 35 --> too many retries --> quit.")
                        toReturnResult      = False
                        toReturnResponse    = {}
                        toReturnMessage     = "Quitted autosearch after too many retries."

                        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                        return toReturn


                    '''--> new google search request'''
                    gcs_response            = ""
                    gcs_response            = googleSearchApiRequest(iSearchterm, startIndex = iStartindex)

                    '''--> Retry? Quit?  Continue?'''
                    gcsCheck_response       = {}
                    gcsCheck_response       = googleSearchRetryContinueQuit(gcs_response)       #{"result": true/false, "response": quit/retry/continue, "message":... 

                    act_retries     +=1
                    waitForGivenTimeIns(1,2)

        elif gcsCheck_response["message"] == "Daily rate limit exceeded --> quit.":
            '''--> daily rate limit exceeded. quit search but contine to save and extract results'''
            toReturnResult      = True
            toReturnResponse    = {}
            toReturnMessage     = "Daily rate limit exceeded."

            toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
            return toReturn


        else:
            '''--> quit'''
            logAction("err - autosearch.py - gcs_performSearchJob() 50 --> quit.")
            toReturnResult      = False
            toReturnResponse    = {}
            toReturnMessage     = "Quitted autosearch --> " + gcsCheck_response["message"]

            toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
            return toReturn


        '''--> get info from response'''
        resultSearchterm        = gcs_response["queries"]["request"][0]["searchTerms"]
        resultTotalFound        = int(gcs_response["searchInformation"]["totalResults"])
        resultCountItems        = int(gcs_response["queries"]["request"][0]["count"])       # 20220220 - make extra check - count represents the number of items for this request. It has happened before that first request has more than 20 items, but second request only 12 (so only 2 for the second request)
        resultStartIndex        = int(gcs_response["queries"]["request"][0]["startIndex"])
        logAction("msg - autosearch.py - gcs_performSearchJob() 10 --> from google search response: searchTerm=" + resultSearchterm + ", totalResults=" + str(resultTotalFound) + ", counted items=" + str(resultCountItems) + ", start index=" + str(resultStartIndex) + ".")


        '''--> return result'''
        toReturnResult      = True
        toReturnResponse    = {"searchterm": resultSearchterm,"resultTotal": resultTotalFound,"resultCount":resultCountItems ,"resultStartIndex": resultStartIndex,"resultJson": gcs_response}
        toReturnMessage     = "Success --> total search results for \"" + resultSearchterm + "\": " + str(resultTotalFound) + ", results for this request: " + str(resultCountItems) +"."

        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn


    except Exception as ex:
        logAction("err - autosearch.py - gcs_performSearchJob() 100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        toReturnResult      = False
        toReturnResponse    = {}
        toReturnMessage     = "Error performing gcs_performSearchJob(). See log for details."

        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn

########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
def gcs_searchPlaylists(iSearchterms):
    '''--> perform google search jobs with entries from searchterm list'''
    '''--> input list: "searchterm":, "trackid1":, "trackid2":, "item1_timessearched":}'''
    '''--> returns list of {"playlistlink", "trackid1": ,"trackid2": }'''

    try:
        '''--> initialize variables'''
        gcs_response            = ""
        gcs_check_response      = {}
        search_string           = ""
        max_searchResults       = 0
        max_searchResultsFixed  = 15

        toReturnResult          = False
        toReturnResponse        = []
        toReturnMessage         = ""

        i                       = 0
        savedPlaylists          = 0
        playlistLink            = ""
        times_counter           = 0


        '''--> db'''
        cursor = get_db().cursor()


        '''--> check source'''
        if len(iSearchterms) == 0:
            logAction("err - autosearch.py - gcs_searchPlaylists() 5 --> Input list 'iSearchterms' contains 0 items.")
            toReturnResult      = False
            toReturnResponse    = []
            toReturnMessage     = "Source list 'iSearchterms' contains 0 items."

            toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
            return toReturn


        '''--> main loop'''
        for item in iSearchterms:
            '''--> extrach search_string'''
            search_string           = item["searchterm"]


            '''--> extract times_counter for item1 from db'''
            entry           = cursor.execute('SELECT * FROM ToAnalyzeTracks WHERE id=?',(item["trackid1"],)).fetchone()
            logAction("msg - autosearch.py - gcs_searchPlaylists() 7--> item1_timessearched extracted for " + item["trackid1"] + ": " + str(entry["times_searched"]))
            times_counter           = entry["times_searched"]


            '''--> log'''
            logAction("msg - autosearch.py - gcs_searchPlaylists() 10 --> Starting main loop with search_string " + search_string)


            '''--> make initial google search request'''
            gcs_response            = googleSearchApiRequest(search_string, startIndex = 0)


            '''--> perform search job'''
            gcs_check_response      = gcs_performSearchJob(iGcs_response = gcs_response, iSearchterm= search_string, iStartindex = 0)   #returns dict

            if gcs_check_response["result"] == False:
                logAction("err - autosearch.py - gcs_searchPlaylists() 21 --> bad gcs response: " + gcs_check_response["message"] + ". Quit")
                toReturnResult      = False
                toReturnResponse    = []
                toReturnMessage     = "Bad gcs response. See log for details."

                toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                return toReturn

            elif gcs_check_response["message"] == "Daily rate limit exceeded.":
                '''--> daily rate limit exceeded'''
                toReturnResult      = True
                toReturnResponse    = []
                toReturnMessage     = "Daily rate limit exceeded."

                toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                return toReturn

            else:
                #valid response
                logAction("msg - autosearch.py - gcs_searchPlaylists() 23 --> valid gcs response: " + gcs_check_response["message"] + ". Total results: " + str(gcs_check_response["response"]["resultTotal"]))
                pass

        
            '''--> check maxResults - extra check'''
            logAction("msg - autosearch.py - gcs_searchPlaylists() 24 --> maxsearchResults="  + str(max_searchResults) + ", gcs_check_response[\"response\"][\"resultTotal\"]="+ str(gcs_check_response["response"]["resultTotal"]))
            if gcs_check_response["response"]["resultTotal"] < max_searchResultsFixed:
                max_searchResults       = gcs_check_response["response"]["resultTotal"]
            else:
                max_searchResults       = max_searchResultsFixed

            logAction("msg - autosearch.py - gcs_searchPlaylists() 25 --> maxsearchResults="  + str(max_searchResults) + ", gcs_check_response[\"response\"][\"resultTotal\"]="+ str(gcs_check_response["response"]["resultTotal"]))


            '''--> grab playlist links from search results - per request max 10 results are provided (=google constraint)'''
            for i in range(0, max_searchResults):
                if (((i % 10) !=0) or (i == 0)) and (i < (gcs_check_response["response"]["resultCount"] + gcs_check_response["response"]["resultStartIndex"])-1):   # % --> restdeling bv. 23 % 15 = 8, 23 % 24 = 1

                    '''--> first pass and < 10'''
                    logAction("msg - autosearch.py - gcs_searchPlaylists() 30 --> i=" + str(i) + ", returnedCountItems=" + str(gcs_check_response["response"]["resultCount"]) + ", returnedStartIndex=" + str(gcs_check_response["response"]["resultStartIndex"]))
                    if "items" in gcs_check_response["response"]["resultJson"].keys():
                        playlistLink    = gcs_check_response["response"]["resultJson"]["items"][i % 10]["link"]

                        '''--> save results in between search jobs to prevent loss of search results'''
                        logAction("msg - autosearch.py - gcs_searchPlaylists() 31 --> saving results to db.")
                        response_temp        = {}
                        response_temp        = gcs_checkAndSaveResults([{"playlistlink":playlistLink, "trackid1": item["trackid1"],"trackid2": item["trackid2"]}])

                        '''--> check result'''
                        if response_temp["result"] == False:
                            toReturnResult      = False
                            toReturnResponse    = []
                            toReturnMessage     = "Failed to save results --> " + response_temp["message"]

                            toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                            return toReturn

                        else:
                            logAction("msg - autosearch.py - gcs_searchPlaylists() 32 --> successfully saved playlist " + str(playlistLink) + " to  db.")
                            savedPlaylists      += response_temp["response"]["totalPlaylistsSaved"]
                            pass

                    else:
                        logAction("err - autosearch.py -  gcs_searchPlaylists() 35 --> 'items' was not found in gcs response for searchterm " + str(gcs_check_response["response"]["searchterm"]) + ", startIndex: " + str(gcs_check_response["response"]["resultStartIndex"]) + ", count: " + str(gcs_check_response["response"]["resultCount"]))
                        continue    #move on to next loop

                elif i!=0 and ((gcs_check_response["response"]["resultTotal"] - gcs_check_response["response"]["resultStartIndex"]) !=0):        
                    '''--> 10th or more pass - new rrequest necesarry (only 10 search results per request are provided)'''
                    logAction("msg - autosearch.py -  gcs_searchPlaylists() 40 --> new request for loop " + str(i) + " ,startIndex: " + str(gcs_check_response["response"]["resultStartIndex"]) + ", total: " + str(gcs_check_response["response"]["resultTotal"]))


                    '''--> make new google search request'''
                    gcs_response            = googleSearchApiRequest(search_string, startIndex = i + 1)         #return json object


                    '''--> perform search job'''
                    gcs_check_response      = gcs_performSearchJob(iGcs_response = gcs_response, iSearchterm= search_string, iStartindex = 0)   #returns dict

                    if gcs_check_response["result"] == False:
                        logAction("err - autosearch.py - gcs_searchPlaylists() 45 --> bad gcs response: " + gcs_check_response["message"] + ". Quit")
                        toReturnResult      = False
                        toReturnResponse    = []
                        toReturnMessage     = "Bad gcs response. See log for details."

                        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                        return toReturn

                    else:
                        #valid response
                        logAction("msg - autosearch.py - gcs_searchPlaylists() 50 --> valid gcs response: " + gcs_check_response["message"] + ".")
                        pass


                    '''--> extract data from response'''
                    returnedCountItems      = int(gcs_check_response["response"]["resultCount"])     
                    returnedStartIndex      = int(gcs_check_response["response"]["resultStartIndex"])


                    waitForGivenTimeIns(1,2)


                    if "items" in gcs_check_response["response"]["resultJson"].keys():
                        playlistLink        = gcs_check_response["response"]["resultJson"]["items"][i % 10]["link"]
                        # lstResults.append({"playlistlink":playlistLink, "trackid1": item["trackid1"],"trackid2": item["trackid2"]})


                        '''--> save results in between search jobs to prevent loss of search results'''
                        logAction("msg - autosearch.py - gcs_searchPlaylists() 51 --> saving results to db.")
                        response_temp        = {}
                        response_temp        = gcs_checkAndSaveResults([{"playlistlink":playlistLink, "trackid1": item["trackid1"],"trackid2": item["trackid2"]}])

                        '''--> check result'''
                        if response_temp["result"] == False:
                            toReturnResult      = False
                            toReturnResponse    = []
                            toReturnMessage     = "Failed to save results --> " + response_temp["message"]

                            toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                            return toReturn

                        else:
                            logAction("msg - autosearch.py - gcs_searchPlaylists() 52 --> successfully saved playlist " + str(playlistLink) + " to  db.")
                            savedPlaylists      += response_temp["response"]["totalPlaylistsSaved"]
                            pass

                    elif int(gcs_check_response["response"]["resultJson"]["searchInformation"]["totalResults"]) == 0:
                        #no search results     
                        continue
                    else:
                        logAction("err - autosearch.py -  gcs_searchPlaylists() 55 --> 'items' was not found in gcs response for searchterm " + str(gcs_check_response["response"]["searchterm"]) + ", startIndex: " + str(gcs_check_response["response"]["resultStartIndex"]) + ", count: " + str(gcs_check_response["response"]["resultCount"]))
                        continue    #move on to next loop


            '''--> update times_counter for item1'''
            times_counter       +=1
            logAction("msg - autosearch.py -  gcs_searchPlaylists() 55 --> Updating times_counter to value " + str(times_counter))
            get_db().execute('UPDATE ToAnalyzeTracks SET times_searched=? WHERE id=?',(times_counter, item["trackid1"]))
            get_db().commit()


        '''--> return result'''
        logAction("msg - autosearch.py - gcs_searchPlaylists() 80 --> Finished  gcs_searchPlaylists: saved " + str(savedPlaylists) + " playlists.")
        toReturnResult      = True
        toReturnResponse    = [] #stResults
        toReturnMessage     = "Success: list with playlists length: " + str(savedPlaylists) + "."

        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn


    except Exception as ex:
        logAction("err - autosearch.py - gcs_searchPlaylists() 100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        toReturnResult      = False
        toReturnResponse    = []
        toReturnMessage     = "Error performing gcs_searchPlaylists(). See log for details."

        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn

########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
def gcs_checkAndSaveResults(iPlaylistList):
    '''--> source is list with playlist ID's and 2 track ID's'''
    '''--> check if 2 track ID's appear in playlist'''
    '''--> input is list of {"playlistlink", "trackid1": ,"trackid2": }'''
    '''--> returns  {"totalPlaylistsSaved":}'''

    try:
        '''--> initialize variables'''
        toReturnResult          = False
        toReturnResponse        = []
        toReturnMessage         = ""

        playlistID              = ""
        playlist_tracks         = []
        response_check          = False
        track_count             = 0
        trckinfo_1              = {}
        trckinfo_2              = {}

        lstResult               = []
        playlistName            = ""
        count_new_playlists     = 0


        '''--> db'''
        cursor = get_db().cursor()


        '''--> check source'''
        if len(iPlaylistList) == 0:
            logAction("err - autosearch.py - gcs_checkAndSaveResults() 5 --> Input list 'iPlaylistList' contains 0 items.")
            toReturnResult      = False
            toReturnResponse    = []
            toReturnMessage     = "Source list 'iPlaylistList' contains 0 items."

            toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
            return toReturn


        '''--> check if found playlists contains the 2 searched tracks'''
        for item in iPlaylistList:
            logAction("msg - autosearch.py - gcs_checkAndSaveResults() 0 --> starting check for playlist link " + item["playlistlink"] + ", trackid1: " + item["trackid1"] + ", trackid2: " + item["trackid2"] + ".")
            '''--> grab playlist ID from each link'''       
            regexResult     = re.search("https:\/\/open.spotify.com\/playlist\/([a-zA-Z0-9]+)", item["playlistlink"]) 
            playlistID      = regexResult.group(1)
            logAction("msg - autosearch.py - gcs_checkAndSaveResults() 5 --> playlist ID extracted: " + playlistID + ".")


            '''--> get playlist tracks + check'''
            playlist_tracks     = getTracksFromPlaylist(playlistID, True)
            response_check      = checkIfTracksInPlaylist([item["trackid1"], item["trackid2"]], playlist_tracks, True)

            if response_check == True:
                logAction("msg - autosearch.py - gcs_checkAndSaveResults() 10 --> playlistID " + playlistID + " contains both tracks!")

                track_count = 0
                for track in getTracksFromPlaylist(playlistID, False):
                    track_count     +=1

                trckinfo_1      = getTrackInfo(item["trackid1"],True)
                trckinfo_2      = getTrackInfo(item["trackid2"],True)

                '''--> update response'''   #{"playlistid":, "foundbytrack1":, "foundbytrack2":...}
                lstResult.append({"playlistid": playlistID, "foundbytrack1": ' '.join(trckinfo_1["artists"]) + " - " + trckinfo_1["title"], "foundbytrack2": ' '.join(trckinfo_2["artists"]) + " - " + trckinfo_2["title"], "nooftracks": track_count}) 
                logAction("msg - autosearch.py - gcs_checkAndSaveResults() 15 --> Added PlaylistID " + playlistID + " with " + str(track_count) + " tracks to lstResult.")

            else:
                #playlists does not contain both tracks
                logAction("msg - autosearch.py - gcs_checkAndSaveResults() 20 --> PlaylistID " + playlistID + " does NOT contain both tracks!")
                pass


        '''--> save valid playlists to db'''
        for entry in lstResult:

            '''--> playlistName'''
            playlistName         = apiGetSpotify("playlists/" + entry["playlistid"])["response"]["name"]     #returns {"result": True/False, "response": json response, "message": ...}
            logAction("msg - autosearch.py - gcs_checkAndSaveResults() 25 --> Checkking before save " + playlistName + " to ToAnalayzeResults")
            cursor.execute('SELECT * FROM ToAnalyzeResults WHERE playlistid=?', (entry["playlistid"],))

            if cursor.fetchone() == None:
                logAction("msg - autosearch.py - gcs_checkAndSaveResults() 30 --> " + playlistName + " NOT IN ToAnalyzeResults yet, so addit!")
                cursor.execute(
                    'INSERT INTO ToAnalyzeResults (playlistid, foundbytrack1, foundbytrack2, name_) VALUES (?,?,?,?)', 
                    (entry["playlistid"], entry["foundbytrack1"], entry["foundbytrack2"], playlistName)
                )
                get_db().commit()

                count_new_playlists     +=1
            else:
                logAction("msg - autosearch.py - gcs_checkAndSaveResults() 35 --> " + playlistName + " ALREADY IN ToAnalyzeResults yet, DONT ADD!")



        # '''--> increase times_searched value for item1 and save'''
        # !!!!!!!!!!!!!!!!!!
        # times_counter       +=1
        # logAction("TEMP --------------------- Updating times_counter to value " + str(times_counter))
        # get_db().execute('UPDATE ToAnalyzeTracks SET times_searched=? WHERE id=?',(times_counter, item1["id"]))
        # get_db().commit()


        '''--> return result'''
        logAction("msg - autosearch.py - gcs_checkAndSaveResults() 40 --> Finished gcs_checkAndSaveResults: " + str(count_new_playlists) + " playlists saved to ToAnalyzeResults.")
        toReturnResult      = True
        toReturnResponse    = {"totalPlaylistsSaved": count_new_playlists}
        toReturnMessage     = "Finished gcs_checkAndSaveResults: " + str(count_new_playlists) + " playlists saved to ToAnalyzeResults."

        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn


    except Exception as ex:
        logAction("err - autosearch.py - gcs_checkAndSaveResults() 100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        toReturnResult      = False
        toReturnResponse    = []
        toReturnMessage     = "Error performing gcs_searchPlaylists(). See log for details."

        toReturn                = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn

########################################################################################



########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
# def searchForPlaylistsContainingTracks(maxResultsPerSearch):
#     '''--> search for playlists that contain tracks from toAnalyzeTracks db'''
#     '''--> 2 tracks are being searched for each time'''
#     '''--> so a valid playlist contains at least 2 tracks of toAnalyzeTracks db'''
#     '''--> returns the following dict: {"result": True/False, "message": e.g. "Found 10 playlists.", "response": list of {"playlistid":, "foundbytrack1":, "foundbytrack2": ,"nooftracks": }'''


#     '''--> initialize variables'''
#     resultSuccess           = False
#     resultMessage           = ""
#     resultResponse          = []
#     i1                      = 0
#     i2                      = 0
#     item1                   = {}
#     item1_timessearched     = 0
#     item2                   = ""
#     times_counter           = 0
#     search_string           = ""
#     gcs_response            = ""
#     gcs_result              = []
#     playlist_tracks         = []
#     track_count             = 0
#     retryCounter            = 0

#     logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 0 --> Started.")

#     try:
#         '''--> check source'''
#         if len(gv_actdbTracks) == 0:
#             #leave
#             logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 10 --> Source tracklist contains 0 tracks.")
#             resultSuccess       = False
#             resultMessage       = "Source tracklist has no tracks."
#             toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#             return toReturn


#         '''--> perform search job'''
#         for i1 in range(0, len(gv_actdbTracks)):
#             item1       = gv_actdbTracks[i1]  

#             if (item1["times_searched"] == None):
#                 #value not initialized yet
#                 item1_timessearched     = i1 + 1
#             else:
#                 if int(item1["times_searched"]) <= i1:
#                     #this should be prevented at all time
#                     item1_timessearched     = i1 + 1
#                 else:
#                     #normal situation, get value from db
#                     item1_timessearched     = int(item1["times_searched"])

#             times_counter   = item1_timessearched

#             if item1_timessearched < len(gv_actdbTracks):
#                 #for this track, not all searches have been performed yet
#                 for i2 in range(item1_timessearched, len(gv_actdbTracks)):
#                     item2       = gv_actdbTracks[i2]

#                     '''--> create searchstring'''
#                     search_string = item1["artists"] + " " + item1["title"] + " " + item2["artists"] + " " + item2["title"]
#                     logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 20 --> start google search job for searchterm: " + str(search_string) + ", i1=" + str(i1) + ", i2=" +str(i2) + ", item1_timessearched=" + str(item1_timessearched) + ".")


#                     '''--> make initial google search request'''
#                     gcs_response      = googlSearchApiRequest(search_string, startIndex = 0)


#                     '''--> check response'''
#                     checkResponse       = checkGoogleResponse(gcs_response)      #returns dict {result: True/false, message:...}

#                     if checkResponse["result"] == False:
#                         '''--> check error code from response'''
#                         if checkResponse["response"] == 429:    
#                             #daily rate limit exceeded, end without error
#                             logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 24 --> " + gcs_result["message"])
#                             resultSuccess       = False
#                             resultMessage       = "Daily limit exceeded."
#                             toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#                             return toReturn
                            

#                     elif checkResponse["response"] == 503:
#                         tempStatus      = 503
#                         #service temporary unavailable, retry
#                         while tempStatus != 0:
#                             '''--> perform new request'''
#                             logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 25 --> 503 service temperary unavailable returned: retry no. " + str(retryCounter) + ".")

#                             if retryCounter  >= 10:
#                                 #too many retries, end with error
#                                 logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 28 --> too many retries.")
#                                 resultSuccess       = False
#                                 resultMessage       = "Too many retries after 503 'service temporary unavailable'."
#                                 toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#                                 return toReturn

#                             '''--> new request'''
#                             gcs_response        = googleSearchApiRequest(search_string, startIndex = 0)
#                             retryCounter        +=1


#                             '''--> new check'''
#                             checkResponse       = checkGoogleResponse(gcs_response) 
#                             if checkResponse["result"] == False:
#                                 tempStatus         = checkResponse["response"]
#                                 #still bad response
#                                 if checkResponse["response"] == 503:
#                                     #move on with next loop
#                                     continue

#                                 elif checkResponse["response"] == 429:
#                                     #daily limit exceeded, end without error
#                                     logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 29 --> " + gcs_result["message"])
#                                     resultSuccess       = False
#                                     resultMessage       = "Daily limit exceeded."
#                                     toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#                                     return toReturn

#                                 elif checkResponse["response"] == 0:
#                                     #success! leave loop and continue
#                                     break

#                                 else :
#                                     #different error, end with error
#                                     logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 35 --> bad response after " + str(retryCounter) + " retries.")
#                                     resultSuccess       = False
#                                     resultMessage       = "Bad response from gcs after " + str(retryCounter) + ", see log for details'."
#                                     toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#                                     return toReturn

#                     else:
#                         #different error, end with error
#                         logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 37 --> bad response after " + str(retryCounter) + " retries.")
#                         resultSuccess       = False
#                         resultMessage       = "Bad response from gcs after " + str(retryCounter) + ", see log for details'."
#                         toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#                         return toReturn


#                     '''--> get retults'''
#                     gcs_result        = extractItemsFromGoogleResponse(gcs_response, maxResults = maxResultsPerSearch)  #response: {"result": True/False, "response": list of playlistlinks, "message": ...}"
                    

#                     '''--> check response'''
#                     if gcs_result["result"] == False:  
#                         #leave
#                         logAction("err - autosearch.py - searchForPlaylistsContainingTracks() 10 --> Bad response from gcs: " + gcs_result["message"])
#                         resultSuccess       = False
#                         resultMessage       = "Bad response from gcs. See log for details."
#                         toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#                         return toReturn
#                     elif gcs_result["message"] == "Rate limit exceeded.": 
#                         '''--> special: rate limit exceeded. Don't generate error.'''
#                         logAction("msg - autosearch.py - searchForPlaylistsContainingTracks() 11 --> Bad response from gcs: " + gcs_result["message"])
#                         resultSuccess       = True
#                         resultMessage       = "Rate limit exceeded."
#                         toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#                         return toReturn
                        

#                     # print('Found results for ' + str(search_string) + ': ' + str(len(gcs_result['response'])))
#                     '''--> check if found playlists contains the 2 searched tracks'''
#                     for playlist_link in gcs_result["response"]:
#                         logAction("TEMP --------------------- Playlistlink: " + playlist_link + ".")
#                         '''--> grab playlist ID from each link'''       
#                         regexResult     = re.search("https:\/\/open.spotify.com\/playlist\/([a-zA-Z0-9]+)", playlist_link) 
#                         playlistID      = regexResult.group(1)
#                         logAction("TEMP --------------------- PlaylistID: " + playlistID + ".")

#                         '''--> get playlist tracks + check'''
#                         playlist_tracks     = getTracksFromPlaylist(playlistID, True)
#                         response_check      = checkIfTracksInPlaylist([item1["id"], item2["id"]], playlist_tracks, True)

#                         if response_check == True:
#                             logAction("TEMP --------------------- PlaylistID " + playlistID + " contains both tracks!")
#                             #playlists contains the 2 tracks
#                             # print("Playlist " + playlistID + " contains all tracks in list: " + str([item1["id"], item2["id"]]) + ".")
#                             # playlists_valid.append({"playlistid": playlistID, "track1": item1["artists"] + " - " + item1["title"], "track2": item2["artists"] + " - " + item2["title"]})

#                             track_count = 0
#                             for track in getTracksFromPlaylist(playlistID, False):
#                                 track_count     +=1

#                             '''--> update response'''   #{"playlistid":, "foundbytrack1":, "foundbytrack2":...}
#                             resultResponse.append({"playlistid": playlistID, "foundbytrack1": item1["artists"] + " - " + item1["title"], "foundbytrack2":item2["artists"] + " - " + item2["title"], "nooftracks": track_count}) 
#                             logAction("TEMP --------------------- ADDED PlaylistID " + playlistID + " WITH " + str(track_count) + " tracks to resultResponse.")

#                         else:
#                             logAction("TEMP --------------------- PlaylistID " + playlistID + " does NOT contain both tracks!")
#                             #playlists does not contain both tracks
#                             # print("Playlist " + playlistID + " does NOT contain all tracks in list: " + str([item1["id"], item2["id"]]) + ".")
#                             pass


#                     '''--> increase times_searched value for item1 and save'''
#                     times_counter       +=1
#                     get_db().execute('UPDATE ToAnalyzeTracks SET times_searched=? WHERE id=?',(times_counter, item1["id"]))
#                     get_db().commit()


#         # '''--> add tracks from found playlists to ScrapedTracks db'''
#         # for playlist in playlists_valid:
#         #     # print("Getting tracks from valid playlist: " + playlist["playlistid"])
#         #     track_count         = 0

#         #     for track in getTracksFromPlaylist(playlist["playlistid"], False):
#         #         track_count     +=1

#         #     '''--> update response'''   #{"playlistid":, "foundbytrack1":, "foundbytrack2":...}
#         #     resultResponse.append({"playlistid": playlist["playlistid"], "foundbytrack1": playlist["track1"], "foundbytrack2": playlist["track2"], "nooftracks": track_count}) 


#         '''--> finished, return response'''
#         resultSuccess       = True
#         resultMessage       = "Finished searchForPlaylistsContainingTracks()."
#         toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}  
#         return toReturn   


#     except Exception as ex:
#         logAction("err - common.py - searchForPlaylistsContainingTracks() --> error while performing: " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
#         logAction("TRACEBACK --> " + traceback.format_exc())

#         resultSuccess       = False
#         resultMessage       = "Error while performing searchForPlaylistsContainingTracks(). See log for details"
#         toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse}
#         return toReturn
