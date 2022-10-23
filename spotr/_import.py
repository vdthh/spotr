########################################################################################
###################################### import.py #######################################
################ Handles all functions related to the import section ###################
########################### VERY basic functionality here!!  ###########################
# Always start after 'flask init-db' command as no unique constraint-check id done here! 
# So this can only be ran once after a new sqlite db has been initialized ##############
########## This only works when columns of source/target tables are identical ##########
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
# from lib2to3.pgen2.pgen import DFAState
from flask import Blueprint, render_template, redirect, request, flash, current_app
from .db import get_db
import sqlite3
from .common import logAction
import traceback
import os
from datetime import datetime
import json
########################################################################################


########################################################################################
######################################## FLASK INIT ####################################
########################################################################################
bp_import = Blueprint('_import', __name__, url_prefix="/import")
########################################################################################


########################################################################################
######################################## VARIABLES #####################################
########################################################################################
gv_suggestedPlaylistName        = "sport_create_playlist_" + str(datetime.now().year)  + str(datetime.now().month) + str(datetime.now().day) + "_" + str(datetime.now().hour) + str(datetime.now().minute) + "_"

########################################################################################


########################################################################################
##################################### FLASK INTERFACE ##################################
########################################################################################
# HTML ROUTING #
@bp_import.route("/", methods=["GET","POST"])
def import_main():
    '''--> main routine'''
    '''--> initialize gloval variables'''
    global gv_suggestedPlaylistName


    '''--> read query parameters'''
    args=request.args      


    #--> PAGE LOAD #
    if request.method == "GET":
        '''--> return html'''
        logAction("msg - _import.py - import_main load page --> import.html page loaded.")
        return render_template("import.html")

    
    elif (request.method == "POST") and ("frm_load_access_file" in request.form):
        '''--> load data from .db file - button clicked'''
        try:   
            '''--> initialize variables'''
            locationPath        = ""


            '''--> retrieve user input'''
            locationPath        = request.form["sourcepath"]    
            logAction("msg - _import.py - import_main load data --> button load access table pressed :" + locationPath + ".")


            '''--> read .db file with sqlite3 and panda --> https://datacarpentry.org/python-ecology-lesson/09-working-with-sql/index.html'''
            '''--> https://www.dataquest.io/blog/python-pandas-databases/'''
            '''-->connect to db'''
            con         = sqlite3.connect(locationPath)
            cur         = con.cursor()


            '''--> ListenedTrack table'''
            for source_row in cur.execute("SELECT * FROM listened_track;"):        #result is tupple --> ('5S8YHkYgbbdvjXDlMkePyI', '5S8YHkYgbbdvjXDlMkePyI', 'Strange Secrets Worth Knowing', 'Improvement Movement', 'Strange Secrets Worth Knowing', '5S8YHkYgbbdvjXDlMkePyI', 9, 'No', '2022-04-15 22:36:20.862484', 0)
                get_db().execute('INSERT INTO ListenedTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, date_added, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (source_row[0], source_row[1], source_row[2], source_row[3], source_row[4], source_row[5], source_row[6], source_row[7], source_row[8], source_row[9]))
                get_db().commit()

            logAction("Done ListenedTrack table")


            '''--> ToListenTrack table'''
            for source_row in cur.execute("SELECT * FROM to_listen_track;"):        
                get_db().execute('INSERT INTO ToListenTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, date_added, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (source_row[0], source_row[1], source_row[2], source_row[3], source_row[4], source_row[5], source_row[6], source_row[7], source_row[8], 0))
                get_db().commit()

            logAction("msg - _import.py - import_main load data 20 --> Done ToListenTrack table")


            '''--> WatchList table'''
            for source_row in cur.execute("SELECT * FROM watch_list;"):        
                get_db().execute('INSERT INTO WatchList (id, _type, _name, date_added, last_time_checked, no_of_items_checked, href, list_of_current_items, imageURL, new_items_since_last_check) VALUES (?,?,?,?,?,?,?,?,?,?)',
                (source_row[0], source_row[1], source_row[2], source_row[3], source_row[4], source_row[5], source_row[6], source_row[7], source_row[8], source_row[9]))
                get_db().commit()

            logAction("msg - _import.py - import_main load data 30 --> Done WatchList table")


            '''--> WatchListNewTracks table'''
            '''--> not done yet'''
            # for source_row in cur.execute("SELECT * FROM new_playlist_tracks;"): 
            #     '''--> get target tracklist'''
            #     data                     = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone() 
            #     currentTrackList         = json.loads(data[1]) #data = first (and only) row of db table WatchListNewTracks, data[0] = id, data[1] = trackList
            #     # toAdd                    = {"id": trck, "from_type": lType, "from_name": lName} 


            #     '''--> get source tracklist'''
            #     if source_row:
            #         print(source_row)
            #         for trckID in source_row[1]:
            #              toAdd              = {"id": trckID, "from_type": "", "from_name": ""}  
            #              currentTrackList    = currentTrackList + [toAdd]

            #         get_db().execute('UPDATE WatchListNewTracks SET trackList=? WHERE id=?',(json.dumps(currentTrackList), "newTracks"))
            #         get_db().commit()

            #     print("DONE DONE DONE ")


            '''--> FavoriteTrack table'''
            for source_row in cur.execute("SELECT * FROM favorite_track;"):        
                get_db().execute('INSERT INTO FavoriteTrack (id, spotify_id, album, artists, title, href, date_added, times_searched) VALUES (?,?,?,?,?,?,?,?)',
                (source_row[0], source_row[1], source_row[2], source_row[3], source_row[4], source_row[5], source_row[6], source_row[7]))
                get_db().commit()

            logAction("msg - _import.py - import_main load data 40 --> Done FavoriteTrack table")


            '''--> LikedTrack table'''
            for source_row in cur.execute("SELECT * FROM liked_tracks;"):        
                get_db().execute('INSERT INTO LikedTrack (id, album, artists, title, href, date_added, times_searched) VALUES (?,?,?,?,?,?,?)',
                (source_row[0], source_row[1], source_row[2], source_row[3], source_row[4], source_row[5], source_row[6]))
                get_db().commit()

            logAction("msg - _import.py - import_main load data 50 --> Done LikedTrack table")


            '''--> EverynoiseGenre table'''
            for source_row in cur.execute("SELECT * FROM everynoise_genre;"):        
                get_db().execute('INSERT INTO EverynoiseGenre (genre, link) VALUES (?,?)',
                (source_row[0], source_row[1]))
                get_db().commit()

            logAction("msg - _import.py - import_main load data 60 --> Done EverynoiseGenre table")


            '''--> ScrapedTracks'''
            for source_row in cur.execute("SELECT * FROM scraped_from_playlists_track;"):        
                get_db().execute('INSERT INTO ScrapedTracks (id, album, artists, title, href, popularity, from_playlist, found_by_tracks, date_added) VALUES (?,?,?,?,?,?,?,?,?)',
                (source_row[0], source_row[2], source_row[3], source_row[4], source_row[5], source_row[6], source_row[7], "", source_row[8]))
                get_db().commit()

            logAction("msg - _import.py - import_main load data 70 --> Done ScrapedTracks table")


            '''--> close connection'''
            con.close()


            '''--> return html'''
            flash("Finished importing data from " + locationPath + "!", category="message")
            return render_template("import.html")
    
        except Exception as ex:
            logAction("err - _import.py - import_main load data 100 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            flash("Error loading data from .db file. See log for details.", category="error")

            
            '''--> close connection'''
            con.close()

            return render_template("import.html")
########################################################################################

        