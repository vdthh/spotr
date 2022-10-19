########################################################################################
####################################### common.py ######################################
######################## functions used through whole project ##########################
########################################################################################


########################################################################################
######################################### IMPORTS ######################################
########################################################################################
from cmath import log
from datetime import datetime
from imp import load_source
from nturl2path import url2pathname
import os
import time
import random
import json
import re
import traceback
from unicodedata import category
from pip._vendor import requests

#from asyncio.mixins import _LoopBoundMixin #https://stackoverflow.com/questions/48775755/importing-requests-into-python-using-visual-studio-code
from .config import spotify_client_id, spotify_client_secret
from .db import get_db
########################################################################################

########################################################################################
######################################## VARIABLES #####################################
########################################################################################
'''--> Used for file locating'''
ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) #result --> E:\docs\python projects\SpotifyWebAppV3.0\spotr
CONFIG_PATH= os.path.join(ROOT_DIR, 'watchlist.py') #result --> E:\docs\python projects\SpotifyWebAppV3.0\spotr\common.py
########################################################################################


########################################################################################
######################################### LOGGING ######################################
########################################################################################
def logAction(msg):
    '''--> General log call'''
    fl1 = open(ROOT_DIR + "\logs\log_event.txt", "a", encoding="utf-8")        #https://stackoverflow.com/questions/27092833/unicodeencodeerror-charmap-codec-cant-encode-characters
    timedetail = str(datetime.now())
    fl1.write('\n' + timedetail + " " + str(msg))
    fl1.close()
########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
########################################################################################
def waitForGivenTimeIns(secondsMin, secondsMax):
    '''--> Wait for given time in s, timespan between min and max'''
    time.sleep(random.uniform(secondsMin, secondsMax))


########################################################################################
######################################## FUNCTIONS #####################################
def returnSearchResults(apiResponse, type):
    '''--> return list of dicts in desired format, starting from a raw json response'''
    resList = []
    for item in apiResponse[type + 's']['items']:
        if type  == 'track':
            ################################################## TRACK
            artistList = []
            for i in range(0,len(item['artists'])):
                artistList.append(item['artists'][i]['name'])

            resList.append({"artist": ', '.join(artistList), "id": str(item['id']), "title": str(item['name']), "album": str(item['album']['name']), "href": str(item['external_urls']['spotify'])})
        elif type  == "album":
            ################################################## ALBUM
            artistList = []
            for i in range(0,len(item['artists'])):
                artistList.append(item['artists'][i]['name'])

            if len(item['images']) !=0:
                imageUrl = item['images'][0]['url']
            else:
                imageUrl = ""

            resList.append({"artist": ', '.join(artistList), "id": str(item['id']), "title": str(item['name']), "release_date": str(item['release_date']), "total_tracks": str(item['total_tracks']), "imageurl": imageUrl, "href": str(item['external_urls']['spotify'])})
        elif type  == "artist":
            ################################################## ARTIST
            if len(item['images']) !=0:
                imageUrl = item['images'][0]['url']
            else:
                imageUrl = ""

            resList.append({"artist": str(item['name']), "id": str(item['id']), "popularity": str(item['popularity']), "imageurl": imageUrl, "href": str(item['external_urls']['spotify'])})
        elif type  == "playlist":
            ################################################## PLAYLIST
            if len(item['images']) !=0:
                imageUrl = item['images'][0]['url']
            else:
                imageUrl = ""

            if len(item['tracks']) !=0:
                totaltracks = item['tracks']['total']
            else:
                totaltracks = 0
            resList.append({"name": str(item['name']), "id": str(item['id']), "description": str(item['description']), "imageurl": imageUrl, "owner": str(item["owner"]["display_name"]), "totaltracks": totaltracks, "href": item['external_urls']['spotify']})
        elif type  == "show":
            ################################################## SHOW
            if len(item['images']) !=0:
                imageUrl = item['images'][0]['url']
            else:
                imageUrl = ""

            resList.append({"title": str(item['name']), "id": str(item['id']), "description": str(item['description']), "imageurl": imageUrl, "publisher": str(item["publisher"]), "href": str(item['external_urls']['spotify'])})
        elif type  == "episode":
            ################################################## EPISODE
            if len(item['images']) !=0:
                imageUrl = item['images'][0]['url']
            else:
                imageUrl = ""

            resList.append({"title": str(item['name']), "id": str(item['id']), "release_date": str(item['release_date']), "description": str(item['description']), "imageurl": imageUrl, "href": str(item['external_urls']['spotify'])})

    return resList
########################################################################################

########################################################################################
######################################## FUNCTIONS #####################################
def checkIfTrackInDB(trackID, dbName):
    '''--> check if given track is in certain db'''
    '''return True if in db'''
    '''return False if not in db'''

    try:
        '''--> db'''
        cursor              = get_db().cursor()


        '''-->track details'''
        try:
            trackDetails    = getTrackInfo(trackID, True)


            '''--> make check'''
            if not "artists" in trackDetails.keys():
                logAction("err - common.py - checkIfTrackInDB000 --> no \"artists\" entry in trackInfo response for track " + trackID)
                return False

            artistsList     = []
            artistsList     = trackDetails["artists"]
            artists         = ', '.join(artistsList) #create one string with all artist names in the list, seperated by a whitespace
            title           = trackDetails["title"]
        except Exception as ex:
            logAction("err - common.py - checkIfTrackInDB00 --> error while runnin 'getTrackInfo' for " + trackID + "--> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            return False


        '''--> check ListenedTrack and ToListenTrack'''
        if dbName == "ListenedTrack" or dbName == "ToListenTrack":
            # https://stackoverflow.com/questions/54659595/checking-for-multiple-values-python-mysql
            cursor.execute('SELECT * FROM ' + dbName + ' WHERE id=? OR artists=? AND title=?', (trackID, artists, title))
            if cursor.fetchone() == None:
                return False    #not in db
            else:
                return True     #in db
        elif dbName == "WatchListNewTracks":
            entry = cursor.execute('SELECT * FROM WatchListNewTracks').fetchone()
            if entry != None:
                trackList = json.loads(entry["trackList"])
                if trackID in trackList:
                    return True
                else:
                    return False
            else:
                #no valid data in table yet
                pass
        else:
            logAction("err - common.py - checkIfTrackInDB0 --> no valid table selected for id " + trackID)
            return False
            

    except Exception as ex:
        logAction("err - common.py - checkIfTrackInDB1 --> error while checking trackID " + trackID + " in table " + dbName + " --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return False

########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
def checkSourceAndCreatePlaylist(input):
    '''--> 20220921 - create general procedure for the following:'''
    '''--> Check a given source for tracks'''
    '''--> decide if a playlist needsto be or can be created from this'''
    '''--> given source can be: datatable Watchlist, a playlist,... '''
    '''--> returns the following dict: {"result": True/False, "message": e.g. "Added tracks to playlist.", "response": json result of 'addTracksToPlaylist', "noOfTracksInNewPlaylist": total tracks, "noOfCreatedPlaylists": ...}'''
    '''--> input requirements'''
    # {"source": "watchlist" or "trackIdList", 
    # "sourceName": e.g. "everynoise dream pop", 
    # "sourceType": e.g. "playlist", 
    # "sourceTracklist": list of track ids, 
    # "noOfTracksPerCreatedPlaylist": number of tracks in to create playlist(s), 
    # "nameCreatedPlaylist": ..., 
    # "descriptionCreatedPlaylist": , ...}
    
    
    '''--> initialize variables'''
    toReturn                = {}
    toCreateList            = []
    newTracksList           = []
    lSource                 = "" 
    loopCnt                 = 0
    loopMin                 = 0
    noOfPlaylistsToCreate   = 0
    plstName                = ""
    CreatedPlaylist         = ""
    createdPlaylistID       = ""
    resultTotalTracks       = 0
    resultTotalPlaylists    = 0
    resultSuccess           = True
    resultMessage           = ""
    resultResponse          = ""
    createPlaylistResponse      = {}
    addTracksResponse           = {}
    

    '''--> check input'''
    if input["source"] == "watchlist":
        #check db WatchlistNewTracks
        lSource     = "watchlist"
    elif input["source"] == "trackIdList":
        #check tracks from given tracklist
        lSource     = "trackIdList"   
    else:
        #leave
        logAction("err - common.py - checkSourceAndCreatePlaylist0 --> No valid source given.")
        resultSuccess       = False
        resultMessage       = "No valid source given."
        toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse, "noOfTracksInNewPlaylist": resultTotalTracks, "noOfCreatedPlaylists": resultTotalPlaylists}
        return toReturn


    '''--> db'''
    cursor              = get_db().cursor()


    '''--> collect tracks from source'''
    if lSource == "watchlist":
        data                = get_db().execute('SELECT * FROM WatchlistNewTracks WHERE id=?',("newTracks",)).fetchone() 
        for item in json.loads(data[1]):           #data = first (and only) row of db table WatchListNewTracks, data[0] = id, data[1] = trackList
            if not checkIfTrackInDB(item["id"],"ListenedTrack") and not checkIfTrackInDB(item["id"],"ToListenTrack") and not checkIfTrackInDB(item["id"],"WatchListNewTracks"):
                #unlistened track
                newTracksList.append(item)
            else:
                #listened track
                pass
    elif lSource == "trackIdList":
        for trckID in input["sourceTracklist"]:  
            if not checkIfTrackInDB(trckID,"ListenedTrack") and not checkIfTrackInDB(trckID,"ToListenTrack") and not checkIfTrackInDB(trckID,"WatchListNewTracks"):
                #unlistened track
                newTracksList.append(trckID)
            else:
                #listened track
                pass

    print("INPUT TRACKS LENGTH: " + str(len(newTracksList)))

    '''--> how many playlists to create?'''
    tempA = len(newTracksList) // input["noOfTracksPerCreatedPlaylist"]     # mod division
    if len(newTracksList) % input["noOfTracksPerCreatedPlaylist"] != 0:     # rest value?          
        noOfPlaylistsToCreate = tempA + 1
    else:
        noOfPlaylistsToCreate = tempA

    print("PLSYLSTS TO CREATE: " + str(noOfPlaylistsToCreate))


    '''--> loop parameters'''
    if lSource == "watchlist":
        loopMin      = input["noOfTracksPerCreatedPlaylist"]
    elif lSource == "trackIdList":
        loopMin      = 1

    print('LOOPMIN: ' + str(loopMin))


    '''--> loop: generate playlists'''
    while len(newTracksList) >= loopMin:
        loopCnt                 = loopCnt + 1
        toCreateList            = newTracksList[:input["noOfTracksPerCreatedPlaylist"]]    #grab first 50 items --> https://stackoverflow.com/questions/10897339/python-fetch-first-10-results-from-a-list

        print("toCREATELIST LENGHT: " + str(len(toCreateList)))

        '''--> create new empty playlist'''
        plstName                = input["nameCreatedPlaylist"] + "_" + str(datetime.now().year).zfill(4) + str(datetime.now().month).zfill(2) + str(datetime.now().day).zfill(2) + "_" + str(datetime.now().hour).zfill(2) + "h" + str(datetime.now().minute).zfill(2)
        createPlaylistResponse  = createPlaylist(plstName, input["descriptionCreatedPlaylist"])
        resultTotalPlaylists    = resultTotalPlaylists + 1


        '''--> check response'''
        if createPlaylistResponse["result"] == False:
            logAction("err - common.py - checkSourceAndCreatePlaylist7 --> Negative feedback from createPlaylist: " + createPlaylistResponse["message"])

            resultSuccess       = False
            resultMessage       = "Error creating new empty playlist"
            resultResponse      = ""
            toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse, "noOfTracksInNewPlaylist": resultTotalTracks, "noOfCreatedPlaylists": resultTotalPlaylists}
            return toReturn

        else:
            '''--> grab ID of newly created playlist'''
            createdPlaylistID          = createPlaylistResponse["response"]["playlistid"]      


            '''--> wait'''
            waitForGivenTimeIns(1, 2)   #Experience learns it can take a few moments for a newly created playlist to become available within spotify (api)


            '''--> add grabbed tracks to new playlist'''
            '''--> First create list of track IDs in WatchlistNewTracks table'''
            '''--> playlist_description_list is used to add to playlist description'''
            id_list                     = []
            playlist_description_list   = [[],[]]   #[0] --> from_type, [1] --> from_name
            for item in toCreateList:
                if lSource == "watchlist":
                    id_list.append(item["id"])
                    playlist_description_list[0].append(item["from_type"])
                    playlist_description_list[1].append(item["from_name"])
                elif lSource == "trackIdList":
                    id_list.append(item)
                    playlist_description_list[0].append(input["sourceType"])    # e.g. playlist  
                    playlist_description_list[1].append(input["sourceName"])    # e.g. everynoise dream pop

            addTracksResponse   = addTracksToPlaylist(createdPlaylistID, id_list)
            resultTotalTracks   = resultTotalTracks + len(toCreateList)

            print("APPENDED TRACKS: " + str(len(id_list)))


            '''--> check response'''
            if addTracksResponse["result"] == False:
                logAction("err - common.py - checkSourceAndCreatePlaylist25 --> Negative feedback from addTracksToPlaylist: " + addTracksResponse["message"])
                
                resultSuccess       = False
                resultMessage       = "Error creating new empty playlist"
                resultResponse      = ""
                toReturn            = {"result": resultSuccess, "message": resultMessage, "response": resultResponse, "noOfTracksInNewPlaylist": resultTotalTracks, "noOfCreatedPlaylists": resultTotalPlaylists}
                return toReturn

            else:
                '''--> add tracks to ListenedTrack db - check has already happened in a previous step'''
                if lSource == "watchlist":
                    for item in toCreateList:
                        trck_info = getTrackInfo(item["id"], True)
                        get_db().execute('INSERT INTO ListenedTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?)',(item["id"], item["id"], trck_info["album"], ', '.join(trck_info["artists"]), trck_info["title"], trck_info["href"], trck_info["popularity"], "", 0))
                        get_db().commit()
                elif lSource == "trackIdList":
                    for item in toCreateList:
                        trck_info = getTrackInfo(item, True)
                        get_db().execute('INSERT INTO ListenedTrack (id, spotify_id, album, artists, title, href, popularity, from_playlist, how_many_times_double) VALUES (?,?,?,?,?,?,?,?,?)',(item, item, trck_info["album"], ', '.join(trck_info["artists"]), trck_info["title"], trck_info["href"], trck_info["popularity"], "", 0))
                        get_db().commit()


                '''--> delete tracks/update db before continuing loop'''
                del newTracksList[:input["noOfTracksPerCreatedPlaylist"]]  
                if lSource == "watchlist":
                        get_db().execute('UPDATE WatchListNewTracks SET trackList=? WHERE id=?',(json.dumps(newTracksList), "newTracks"))
                        get_db().commit()
                        logAction("msg - common.py - checkSourceAndCreatePlaylist40 --> Tracks left in table WatchListNewTracks: " + str(len(newTracksList)))


                '''--> adjust playlist details with tracks sources'''             
                changePlaylistDetails(createdPlaylistID, '', input["descriptionCreatedPlaylist"] + createPlaylistDescription(playlist_description_list))

    else:
        '''--> finished'''
        logAction("msg - common.py - checkSourceAndCreatePlaylist60 --> ended --> total of " + str(loopCnt) + " playlists created.")
        resultMessage       = "Succesfully finished checkSourceAndCreatePlaylist()."
        toReturn = {"result": resultSuccess, "message": resultMessage, "response": resultResponse, "noOfTracksInNewPlaylist": resultTotalTracks, "noOfCreatedPlaylists": resultTotalPlaylists}
        return toReturn

########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
def createPlaylistDescription(input_list):
    '''--> Create playlist description as following:'''
    '''for each artist/playlist/... from which tracks are added to playlist'''
    '''add number & type in description'''
    '''for example: playlist Daily Mix 1: 5 tracks, playlist Daily Mix 3: 2 tracks, artist Jefke: 1 track, ...'''
    '''input_list contains 2 lists: [[from_type],[from_name]]'''
    resultString = ""
    tempList = [[],[],[]]   #from_type, from_name, sum of appearance
    for i in range(len(input_list[0])):    
        if not input_list[1][i] in tempList[1]:
            #new name
            tempList[0].append(input_list[0][i])        #from_type
            tempList[1].append(input_list[1][i])        #from_name
            tempList[2].append(1)                       #sum of appearance
        else:
            #only increase counter
            position = tempList[1].index(input_list[1][i])
            tempList[2][position] = tempList[2][position] + 1      #sum of appearance


    '''--> create result string'''
    for i in range(len(tempList[0])):
        if i == 0:
            resultString = str(tempList[2][i]) + " tracks from " + tempList[0][i] + " " + tempList[1][i]
        else:
            resultString = resultString + ", " + str(tempList[2][i]) + " tracks from " + tempList[0][i] + " " + tempList[1][i]

    return resultString
########################################################################################


########################################################################################
######################################## FUNCTIONS #####################################
def checkIfTracksInPlaylist(tracksToCheck, listToCheck, listInDetail):
    '''--> check if tracks in 'tracksToCheck' all appear in 'listToCheck' '''
    '''--> tracksToCheck and listToCheck = list with track ID's'''
    '''--> if listInDetail is False; listTocheck contains only trackIDs'''
    '''--> If true, it contains dicts: {"id" :, "artists" : , "title" : }'''
    '''--> returns True if all tracks appear in list'''

    '''--> initialize variables'''
    resultCnt       = 0


    '''--> make check'''
    if listInDetail:
        for trackId in tracksToCheck:
            '''--> get track details'''
            track_info      = getTrackInfo(trackId, True)   

            for list_track in listToCheck:
                '''--> get track details'''
                if ((track_info["artists"] == list_track["artists"]) and (track_info["title"] == list_track["title"])) or (trackId == list_track["id"]):
                    #track appears in listToCheck
                    resultCnt = resultCnt + 1

    
    '''--> final check'''
    if resultCnt == len(tracksToCheck):
        return True #all tracks appear in list
    else:
        return False 

########################################################################################

########################################################################################
######################################## FUNCTIONS #####################################
def getDBTracks(whichDB):
    '''--> returns a list of all tracks IDs from a given db'''
    '''--> returns dict {result: True/false, response: tracklist, message:...}'''
    '''--> Unlike with checkIfTrackInDB, this ONLY compares track ID's! Not artist or title!'''
    '''--> so for detailed comparision, use checkIfTrackInDB'''

    '''--> initialize variables'''
    tracks              =  []
    toReturnResult      = False
    toReturnMessage     = ""
    toReturnResponse    = []


    '''--> db'''
    cursor              = get_db().cursor()


    '''--> chich db?'''
    if (whichDB == 'ToListenTrack') or (whichDB == 'ListenedTrack'):
        for item in cursor.execute('SELECT * FROM ' + whichDB).fetchall():
            tracks.append(item["id"])

        toReturnResult      = True
        toReturnMessage     = "Returned " + str(len(tracks)) + " tracks from db " + whichDB + "."
        toReturnResponse    = tracks     

    elif whichDB == "WatchListNewTracks":
        entry = cursor.execute('SELECT * FROM WatchListNewTracks').fetchone()
        if entry != None:
            tracks = json.loads(entry["trackList"])

            toReturnResult      = True
            toReturnMessage     = "Returned " + str(len(tracks)) + " tracks from db " + whichDB + "."
            toReturnResponse    = tracks

        else:
            toReturnResult      = False
            toReturnMessage     = "No tracks yet in db " + whichDB + "."
            toReturnResponse    = []

    else:
        toReturnResult      = False
        toReturnMessage     = "No valid db name given:\'" + whichDB + "\'."
        toReturnResponse    = []


    '''--> return result'''
    toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}  
    return toReturn
########################################################################################


########################################################################################
######################################### SPOTIFY ######################################
########################################################################################
########################################################################################
def apiGetSpotify(urlExtension):
    '''--> general procedure for every Spotify API request <--'''
    '''--> as of 20221013 - returns a dict with a response and list of links'''
    '''--> response: {"result": True/False, "response": list of playlistlinks, "message": ...}'''

    '''--> initialize variables'''
    toReturn                = {}
    toReturnResult          = True
    toReturnResponse        = {}
    toReturnMessage         = ""
    maxRetries              = 30


    '''--> always request a new access token'''
    result = getNewAccessToken()
    if result == '':
        '''error'''
        logAction("err - common.py - apiGetSpotify --> error getNewAccessToken()")
        
        toReturnResult      = False
        toReturnMessage     = "Error getNewAccessToken()."
        toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn

    elif result == None:
        '''ok'''
        pass

    else:
        '''not possible?'''
        logAction("err - common.py - apiGetSpotify2 --> something unusual with getNewAccessToken()")

        toReturnResult      = False
        toReturnMessage     = "Something unusual with getNewAccessToken()."
        toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn


    '''-->  wait given timespan'''
    waitForGivenTimeIns(0.1,0.2)


    '''--> create and perform request'''
    if urlExtension.startswith("https://"):
        url = urlExtension
    else:
        url = 'https://api.spotify.com/v1/' + urlExtension

    headers = {'Authorization': 'Bearer ' + gv_access_token}

    try:
        response = requests.get(url, headers=headers, verify=False)
    except Exception as ex:
        logAction("err - common.py - apiGetSpotify3 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())

        toReturnResult      = False
        toReturnMessage     = "Faulty response from request."
        toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn


    '''--> check for error in response'''
    try:
        retryCnt = 0
        while (response.status_code != 200):    #bad response
            print("*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*/*")
            print("RESPONSE: " + str(response))
            logAction("msg - common.py - apiGetSpotify5 --> bad response status_code: " + str(response.status_code))

            # if (response.status_code == 404):
            #     #requested object not found


            errStr = ""
            if "status" in response.json().keys():
                errStr = "status: " + str(response.json()["status"])
            if "error" in response.json().keys():
                errStr = errStr + " error: " + str(response.json()["error"])
            if "message" in response.json().keys():
                errStr = errStr + " message: " + str(response.json()["message"])
                if response.message == "invalid id" or response.message == "Invalid id":
                    logAction("msg - common.py - apiGetSpotify6 --> Invalid track ID response!")
                    
                    toReturnResult      = False
                    toReturnMessage     = "Invalid ID provided."
                    toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                    return toReturn

            logAction("msg - common.py - apiGetSpotify7 --> error details: " + errStr + ". Retrying request #" + str(retryCnt))
     

            waitForGivenTimeIns(1,3)


            '''--> retrying if invalid response'''
            if retryCnt >= maxRetries:
                logAction("err - common.py - apiGetSpotify9 --> too many retries requesting acces token, aborting.")


                '''--> save last result for debugging'''
                with open (ROOT_DIR + "/logs/spotify_apiGetSpotify_RETRY.json", 'w', encoding="utf-8") as fi:
                    fi.write(json.dumps(response.json(), indent = 4))
                
                toReturnResult      = False
                toReturnMessage     = "After " + str(maxRetries) + " requests, still no valid response."
                toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
                return toReturn

            '''--> new request for next retry'''
            response              = requests.get(url, headers=headers, verify=False)
            retryCnt              +=1

    except Exception as ex:
        logAction("err - common.py - apiGetSpotify11 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        
        toReturnResult      = False
        toReturnMessage     = "Error in response from request."
        toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn


    '''--> save last result for debugging'''
    with open (ROOT_DIR + "/logs/spotify_apiGetSpotify_LAST.json", 'w', encoding="utf-8") as fi:
        fi.write(json.dumps(response.json(), indent = 4))


    '''--> prepare return value'''
    jsonResponse            = {}
    try:
        jsonResponse        = response.json()
    except Exception as ex:
        toReturnResult      = False
        toReturnMessage     = "Error converting response to json format."
        toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
        return toReturn


    '''--> finally, return a valid response in json format'''
    toReturnResult      = True
    toReturnMessage     = "Error in response from request."
    toReturnResponse    = jsonResponse
    toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
    return toReturn

########################################################################################

########################################################################################
######################################### SPOTIFY ######################################
def getNewAccessToken():
    '''--> Load the saved 'refresh_token' from external file'''
    '''--> return empty string in case of error'''
    '''--> if everything went ok, nothing (None) is returned'''
    try:
        fileOpen = open(ROOT_DIR + "/static/refresh_token.txt", "r")      
        refresh_token = fileOpen.read()
        fileOpen.close()
    except Exception as ex:
        logAction("err - common.py - getNewAccessToken1 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''


    '''--> Assuming a refresh_token has already been received, request new access token with it.
            See spotify api auto documentation: 4. Requesting a refreshed access token; 
            Spotify returns a new access token to your app
    '''


    '''--> Create body params and request parameters'''
    grant_type= 'refresh_token'
    url = 'https://accounts.spotify.com/api/token'
    body_params = {'grant_type': grant_type, 'refresh_token': refresh_token}


    '''--> perform the request'''
    try:
        response = requests.post(url, data=body_params, auth=(spotify_client_id, spotify_client_secret), verify=False)
    except Exception as ex:
        logAction("err - common.py - getNewAccessToken2 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''


    '''--> check for error in response'''
    try:
        retryCnt = 0
        while (response.status_code != 200) :
            waitForGivenTimeIns(0.5,1)
            logAction("msg - common.py - getNewAccessToken3 --> retrying request #" + str(retryCnt))

            if retryCnt >= 10:
                logAction("err - common.py - getNewAccessToken4 --> too many retries requesting acces token.")

            response = requests.post(url, data=body_params, auth=(spotify_client_id, spotify_client_secret), verify=False)
            retryCnt+=1

            '''--> save last result for debugging'''
            with open (ROOT_DIR + "/logs/spotify_getNewAccessToken_LAST.json", 'w', encoding="utf-8") as fi:
                fi.write(json.dumps(response.json(), indent = 4))
            return ''
    except Exception as ex:
        logAction("err - common.py - getNewAccessToken4.5 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''


    '''--> save last result for debugging'''
    with open (ROOT_DIR + "/logs/spotify_getNewAccessToken_LAST.json", 'w', encoding="utf-8") as fi:
       fi.write(json.dumps(response.json(), indent = 4))


    '''--> check if (json-converted) response contains a new refresh_token.
    if so, it needs to be stored!
    '''
    try:
        if hasattr(response.json(), 'refresh_token'):
            fileOpen = open(ROOT_DIR + "/static/refresh_token.txt", 'w')  #'w' = overwrite
            fileOpen.write(response.json()['refresh_token'])
            fileOpen.close()
    except Exception as ex:
        logAction("err - common.py - getNewAccessToken5 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''


    '''--> store received access_token also in external file'''
    try:
        fileOpen = open(ROOT_DIR + "/static/access_token.txt", 'w')    #20210723 filopen('access_token.txt, 'w') doesn't seem to work
        fileOpen.write(response.json()['access_token'])
        global gv_access_token      #create global variable
        gv_access_token = response.json()['access_token']
        fileOpen.close()
    except Exception as ex:
        logAction("err - common.py - getNewAccessToken6 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''

########################################################################################

########################################################################################
######################################### SPOTIFY #####################################
def getTrackInfo(trackID, artistsAsList):
    '''--> Get track details via API'''
    '''Returns a dict containing track info:'''
    '''input artistsAsList returns the artist names as list or only the first name'''
    '''{"trackid": string, "title": string, "artists": list of string, "album": string, "href": string, "popularity": string}'''
    '''Returns empty string in case of error'''


    '''--> perform request'''  
    track_info = apiGetSpotify('tracks/' + trackID)     #{"result": True/False, "response": list of playlistlinks, "message": ...}


    '''--> check response'''
    if track_info["result"] == False:
        logAction("err - common.py - getTrackInfo2 --> empty api response for track " + trackID + "! Message: " + track_info["message"] + ".")
        return ''


    '''--> save last result for debugging'''
    with open (ROOT_DIR + "/logs/common_getTrackInfo_LAST.json", 'w', encoding="utf-8") as fi:
        fi.write(json.dumps(track_info["response"], indent = 4))


    '''--> Extract track ID from the uri to create the url'''
    try:
        regexResult = re.search(":([a-zA-Z0-9]+):([a-zA-Z0-9]+)", str(track_info["response"]['uri'])) 
        urlLink = regexResult.group(2)
    except Exception as ex:
        logAction("err - common.py - getTrackInfo3 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''


    '''--> return first artist name or list of all artist names'''
    try:
        artistNames = []
        #get list of artist name(s)
        for artist in track_info["response"]["artists"]:
            #create list with artist names
            artistNames.append(artist["name"])
        if artistsAsList:
            return {"trackid": trackID, "title": track_info["response"]["name"], "artists": artistNames, "album": track_info["response"]["album"]["name"], "href": urlLink, "popularity": track_info["response"]["popularity"]}
        else:
            return {"trackid": trackID, "title": track_info["response"]["name"], "artists": track_info["response"]["artists"][0]["name"], "album": track_info["response"]["album"]["name"], "href": urlLink, "popularity": track_info["response"]["popularity"]}

    except Exception as ex:
        logAction("err - common.py - getTrackInfo4 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''

########################################################################################

########################################################################################
######################################### SPOTIFY #####################################
def getTracksFromLikedList():
    '''--> Return a list with track ID's (with pagination)'''
    '''Returns empty string in case of error'''


    '''--> perform request'''
    logAction("msg - common.py - getTracksFromLikedList --> requesting tracks from liked list.") 
    liked_tracks = apiGetSpotify("me/tracks?offset=0&limit=50")         #{"result": True/False, "response": list of playlistlinks, "message": ...}

    
    '''--> check response before continuing'''
    if liked_tracks["result"] == False:
        logAction("err - common.py - getTracksFromLikedList2 --> empty api response for liked tracks! Message: " + liked_tracks["message"] + ".")
        return ''


    try:
        '''--> check pagination - fill resultlist'''
        resultList      = []
        total           = liked_tracks["response"]["total"]
        limit           = liked_tracks["response"]["limit"]
        offset          = liked_tracks["response"]["offset"]

        while offset < total:
            for track in liked_tracks["response"]["items"]:
                if track["track"]["id"]: #check if valid item
                    resultList.append(track["track"]["id"]) #add track ID to resultList
            offset = offset + limit
            if offset < total: #new request
                liked_tracks = apiGetSpotify("me/tracks?offset=" + str(offset) + "&limit=" + str(limit))
                if liked_tracks["result"] == '': #invalid api response
                    logAction("err - common.py - getTracksFromLikedList3 --> empty api response for liked tracks! Message: " + liked_tracks["message"] + ".")
                    return ''
                continue

        logAction("msg - common.py - getTracksFromLikedList4 --> Succesfully returned list of " + str(len(resultList)) + " tracks from liked list.")
        return resultList

    except Exception as ex:
        logAction("err - common.py - getTracksFromLikedList5 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''

########################################################################################

########################################################################################
######################################### SPOTIFY ######################################
def getTracksFromArtist(artistID, trackDetails):
    '''--> Returns list with all track ID's or trackdetails for the given artist - pagination taken into account'''
    '''In case of error, '' is returned'''
    '''if trackDetails is TRUE, a list with dicts is returned containing detailed track info.  {id: trackid, artists: list with artists, title: title}'''
    '''if FALSE, a list containing only the track ID's is returned'''


    '''--> perform request, artist albums'''
    logAction("msg - common.py - getTracksFromArtist --> requesting albums from artist " + artistID + ".") 
    artist_albums = apiGetSpotify("artists/" + artistID + "/albums?offset=0&limit=50")          # {"result": True/False, "response": list of playlistlinks, "message": ...}


    '''--> check response before continuing'''
    if artist_albums["result"] == '':
        logAction("err - common.py - getTracksFromArtist2 --> empty api response for artists albums! Message: " + artist_albums["message"] + ".")
        return ''

    try:
        '''--> check pagination - fill resultlist'''
        resultList  = []
        total       = artist_albums["response"]["total"]
        limit       = artist_albums["response"]["limit"]
        offset      = artist_albums["response"]["offset"]

        while offset < total:
            for album in artist_albums["response"]["items"]: #album tracks            
                artist_album_tracks = apiGetSpotify("albums/" + album["id"] + "/tracks")
                if artist_album_tracks["result"] == True: #valid api response
                    for track in artist_album_tracks["response"]["items"]:
                        if track["id"]: #check if valid item
                            if trackDetails:
                                #detailed track info
                                #grab artist name(s)
                                artist_list = []
                                for artist in track["artists"]:
                                    artist_list.append(artist["name"])
                                artist_trck_dict_obj = {"id" : track["id"], "artists" : artist_list, "title" : track['name']}
                                resultList.append(artist_trck_dict_obj)         
                            else:
                                #only track ID
                                resultList.append(track["id"])
                        else: #invalid track
                            log("err - common.py - getTracksFromArtist3 --> invalid track[\"ID\"] for album " + str(album["id"]) + ".")
                            continue
                else: #invalid api response                  
                    logAction("msg - common.py - getTracksFromArtist4 --> empty api response for artist's album tracks (" + album["id"] + "), moving on to next. Message: " + artist_album_tracks["message"] + ".")
                    # return ''

            offset = offset + limit
            if offset < total: #new request
                artist_album_tracks = apiGetSpotify("albums/" + album["id"] + "/tracks?offset=" + str(offset) + "&limit=" + str(limit))
                if artist_album_tracks["result"] == False: #invalid api response
                    logAction("err - common.py - getTracksFromArtist5 --> empty api response for artist's album tracks! Message: "+ artist_album_tracks["message"] + ".")
                    return ''
                continue

        logAction("msg - common.py - getTracksFromArtist6 --> Succesfully returned list of " + str(len(resultList)) + " tracks from artist " + artistID)
        return resultList

    except Exception as ex:
        logAction("err - common.py - getTracksFromArtist7 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''

########################################################################################

########################################################################################
######################################### SPOTIFY ######################################
def getTracksFromPlaylist(playlistID, trackDetails):
    '''--> Returns list with all track ID's or trackdetails for the given playlist - pagination taken into account'''
    '''In case of error, '' is returned'''
    '''if trackDetails is TRUE, a list with dicts is returned containing detailed track info.  {id: trackid, artists: list with artists, title: title}'''
    '''if FALSE, a list containing only the track ID's is returned'''


    '''--> perform request'''
    logAction("msg - common.py - getTracksFromPlaylist --> requesting tracks from playlist " + playlistID + ".") 
    playlist_trcks = apiGetSpotify("playlists/" + playlistID + "/tracks?offset=0&limit=100")        #{"result": True/False, "response": list of playlistlinks, "message": ...}

    '''--> save last result for debugging'''
    with open (ROOT_DIR + "/logs/spotify_apiGetSpotify_LASTXXX.txt", 'w', encoding="utf-8") as fi:
        fi.write(str(playlist_trcks))


    '''--> check response before continuing'''
    if playlist_trcks["result"] == '':
        logAction("err - common.py - getTracksFromPlaylist2 --> empty api response for playlist tracks! Message: " + playlist_trcks["message"] + ".")
        return ''
    
    try:
        '''--> check pagination - fill resultlist'''
        resultList      = []
        total           = playlist_trcks["response"]["total"]
        limit           = playlist_trcks["response"]["limit"]
        offset          = playlist_trcks["response"]["offset"]

        while offset < total:          
            if playlist_trcks["result"] == True: #valid api response
                for track in playlist_trcks["response"]["items"]: #playlist tracks
                    try:
                        #if track["track"]["id"]: #check if valid item
                        if "track" in track.keys():
                            if "id" in track["track"].keys(): 
                                if trackDetails: #detailed track info                            
                                    #grab artist name(s)
                                    artist_list = []
                                    for artist in track["track"]["artists"]:
                                        artist_list.append(artist["name"])
                                    playlist_trck_dict_obj = {"id" : track["track"]["id"], "artists" : artist_list, "title" : track["track"]['name']}
                                    resultList.append(playlist_trck_dict_obj)         
                                else: #only track ID                          
                                    resultList.append(track["track"]["id"])
                        else: #invalid track
                            logAction("err - common.py - getTracksFromPlaylist3 --> invalid trackID in playlist " + playlistID + ".")
                            continue
                    except:
                        continue
            else:#invalid api response                  
                logAction("err - common.py - getTracksFromPlaylist4 --> empty api response for playlist tracks " + playlistID + ". Message: " + playlist_trcks["message"] + ".")
                return ''

            offset = offset + limit
            if offset < total: #new request
                playlist_trcks = apiGetSpotify("playlists/" + playlistID + "/tracks?offset=" + str(offset) + "&limit=" + str(limit))
                if playlist_trcks["result"] == False: #invalid api response
                    logAction("err - common.py - getTracksFromPlaylist5 --> empty api response for playlist tracks - offset=" + str(offset) + ", limit=" + str(limit) + ". Message: " + playlist_trcks["message"] + ".")
                    return ''
                continue

        logAction("msg - common.py - getTracksFromPlaylist6 --> Succesfully returned list of " + str(len(resultList)) + " tracks from playlist that contains " + str(total) + " tracks.")
        return resultList

    except Exception as ex:
        logAction("err - common.py - getTracksFromPlaylist7 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''


########################################################################################
######################################### SPOTIFY ######################################
def createPlaylist(name, description):
    '''--> Create a new empty playlist'''
    '''--> returns dict {result: True/false, response: {playlistid: }, message:...}'''
    '''--> response is modified on 20221009'''

    '''--> initialize variables'''
    toReturnResult      = False
    toReturnMessage     = ""
    toReturnResponse    = {}
    playlistID          = ""



    '''--> get new access token - prepare request'''
    if getNewAccessToken() == "":
        logAction("err - common.py - createPlaylist --> error requesting new access token.")

        toReturnResult      = False
        toReturnResponse    = {}
        toReturnMessage     = "Error requesting new access token."
        return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}


    waitForGivenTimeIns(0.1,1)


    '''--> prepare payload'''
    headers = {'Authorization': 'Bearer ' + gv_access_token}         
    payload = {
        "name"          : name, 
        "public"        : False,
        "description"   : description 
        }


    '''--> perform POST request'''
    try:      
        logAction("msg - common.py - createPlaylist3 --> about to create a new playlist: " + name)  
        response = requests.post(url='https://api.spotify.com/v1/users/bakzgzahvlg9pjp9g7hxaav00/playlists', headers = headers, data = json.dumps(payload), verify=False)
    except Exception as ex:
        logAction("err - common.py - createPlaylist4 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        
        toReturnResult      = False
        toReturnResponse    = {}
        toReturnMessage     = "Error performing POST request."
        return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}


    '''--> save last result for debugging'''
    with open (ROOT_DIR + "/logs/spotify_apiPostSpotify_createPlaylist_LAST.json", 'w', encoding="utf-8") as fi:
        fi.write(json.dumps(response.json(), indent = 4))


    '''--> check response'''
    if "error" in response.json():
        logAction("err - common.py - createPlaylist5 --> error from POST request: " + str(response.json()["error"]["status"]) + ", " + str(response.json()["error"]["message"]))

        toReturnResult      = False
        toReturnResponse    = {}
        toReturnMessage     = "Negative feedback from POST request."
        return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
 
    elif response == "":
        logAction("err - common.py - createPlaylist6 --> empty response from POST request.")
        
        toReturnResult      = False
        toReturnResponse    = {}
        toReturnMessage     = "Empty response from POST request."
        return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}


    '''--> grab ID of new playlist'''
    playlistID  = response.json()["id"]

    '''--> finally, return a valid response'''
    logAction("msg - common.py - createPlaylist7 --> Succesfully created playlist " + name + ", ID = " + playlistID)

    toReturnResult      = True
    toReturnResponse    = {"playlistid": playlistID}
    toReturnMessage     = "Succesfully created playlist " + name + " with ID " + playlistID +"."
    return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage} 
########################################################################################


########################################################################################
######################################### SPOTIFY ######################################
def changePlaylistDetails(id, newName, newDescription):
    '''--> Change details of an existing playlist'''
    '''if empty string input is given, nothing is changed'''
    '''in case of error, '' is returned'''


    '''--> prepare request'''
    if getNewAccessToken() == "":
        logAction("err - common.py - changePlaylistDetails --> error requesting new access token.")
        return ''

    waitForGivenTimeIns(0.1,1)
        

    try: #create payload
        headers = {'Authorization': 'Bearer ' + gv_access_token}

        if newName != "" and newDescription != "":         
            payload = {
                "name"          : newName, 
                "public"        : False,
                "description"   : newDescription 
                }
        elif newName == "" and newDescription != "":         
            payload = {
                "public"        : False,
                "description"   : newDescription 
                }
        elif newName != "" and newDescription == "":         
            payload = {
                "name"          : newName, 
                "public"        : False,
                }

    except Exception as ex:
        logAction("err - common.py - changePlaylistDetails2 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''


    '''--> perform PUT request'''
    try:      
        logAction("msg - common.py - changePlaylistDetails3 --> about to change playlist details for: " + str(id))  
        response = requests.put(url='https://api.spotify.com/v1/playlists/' + str(id), headers = headers, data = json.dumps(payload), verify=False)
    except Exception as ex:
        logAction("err - common.py - changePlaylistDetails4 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''


    '''--> check response'''
    if "error" in response:
        print("err - common.py - changePlaylistDetails5 --> error from PUT request: " + str(response.json()["error"]["status"]) + ", " + str(response.json()["error"]["message"]))
        return ''
    elif response == "":
        print("err - common.py - changePlaylistDetails6 --> empty response from PUT request.")
        return ''

    '''--> finally, return non-empty string to mark succesful finish'''
    logAction("msg - common.py - changePlaylistDetails7 --> Succesfully changed playlist details for " + str(id)) 
    return "done"

########################################################################################


########################################################################################
######################################### SPOTIFY ######################################
def addTracksToPlaylist(playlistID, trackIDList):
    '''--> Add tracks to existing playlist'''
    '''--> Playlist already has to exist!'''
    '''--> returns dict {result: True/false, response: {"snapshot_id": response["snapshot_id"], "tracks_added": str(len(trackIDList))}, message:...}'''
    '''--> response is modified on 20221009'''
    '''--> only 100 tracks can be added per request'''

    '''--> initialize variables'''
    toReturnResult      = False
    toReturnMessage     = ""
    toReturnResponse    = {}
    localTrackIDList    = []
    localTrackIDList2   = []

    '''--> copy list for internal use'''
    localTrackIDList = trackIDList.copy()


    '''--> loop, as 100 tracks per request max'''
    while len(localTrackIDList) > 0:
        localTrackIDList2=localTrackIDList[:100]

        '''--> prepare request'''
        if getNewAccessToken() == "":
            logAction("err - spotify.py - addTracksToPlaylist1 --> error requesting new access token.")

            toReturnResult      = False
            toReturnResponse    = {}
            toReturnMessage     = "Error requesting new access token."
            return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}

        waitForGivenTimeIns(0.1,1)

        '''--> create payload'''
        headers = {'Authorization': 'Bearer ' + gv_access_token}         
        track_uri_list = [] #List with track uris
        for i in range(len(localTrackIDList2)):
            track_uri_list.append("spotify:track:" + str(localTrackIDList2[i]))

        payload = {"uris":track_uri_list}


        '''--> perform POST request'''
        try:      
            logAction("msg - common.py - addTracksToPlaylist3 --> about to add a total of " + str(len(localTrackIDList2)) + " tracks to playlist " + playlistID + ".") 
            response = requests.post(url='https://api.spotify.com/v1/playlists/' + playlistID + "/tracks", headers = headers, data = json.dumps(payload), verify=False)
            # response_json = response.json() #extra line to trigger error in case of faulty response object
        except Exception as ex:
            logAction("err - common.py - addTracksToPlaylist4 --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
            logAction("TRACEBACK --> " + traceback.format_exc())
            toReturnResult      = False
            toReturnResponse    = {}
            toReturnMessage     = "Error performing POST request."
            return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}


        '''--> save last result for debugging'''
        with open (ROOT_DIR + "/logs/spotify_apiPostSpotify_addTracks_LAST.json", 'w', encoding="utf-8") as fi:
            fi.write(json.dumps(response.json(), indent = 4))


        '''--> check response'''
        if "error" in response.json():
            logAction("err - common.py - addTracksToPlaylist5 --> error from POST request: " + str(response.json()["error"]["status"]) + ", " + str(response.json()["error"]["message"]))

            toReturnResult      = False
            toReturnResponse    = {}
            toReturnMessage     = "Negative feedback from POST request."
            return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}

        elif response == "":
            logAction("err - common.py - addTracksToPlaylist10 --> empty response from POST request.")
            
            toReturnResult      = False
            toReturnResponse    = {}
            toReturnMessage     = "Empty response from POST request."
            return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}


        '''--> adjust tracklist'''
        del localTrackIDList[:100]


    '''--> finally, return a valid response'''
    logAction("msg - common.py - addTracksToPlaylist6 --> Succesfully added " + str(len(trackIDList)) + " tracks to playlist " + playlistID + ".") 

    toReturnResult      = True
    toReturnResponse    = {"snapshot_id": response.json()["snapshot_id"], "tracks_added": str(len(trackIDList))}
    toReturnMessage     = "Succesfully added " + str(len(trackIDList)) + " tracks to playlist " + playlistID + "."
    return {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage} 

########################################################################################

########################################################################################
######################################### SPOTIFY ######################################
def searchSpotify(searchstring, searchtype, limit, offset):
    '''--> Search on spotify via the api'''
    '''Returns a dictionary of the search result, depending on the selected type (track, playlist, artist,...)'''
    '''in case of error, '' is returned'''


    '''--> perform request - returns a dict!'''
    try:
        response = apiGetSpotify('search?q=' + str(searchstring) + '&type=' + str(searchtype) + '&limit=' + str(limit) + '&offset=' + str(offset))      #{"result": True/False, "response": list of playlistlinks, "message": ...}
    except Exception as ex:
        logAction("err - common.py - searchSpotify --> " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''

    '''--> check response'''
    if response["result"] == False:
        logAction("common.py - searchSpotify 10 --> Bad response from apiGetSpotify. Message: " + response["message"] + ".")


    '''--> save last result for debugging'''
    with open (ROOT_DIR + "/logs/spotify_apiSearchSpotify_LAST.json", 'w', encoding="utf-8") as fi:
        fi.write(json.dumps(response["response"], indent = 4))


    '''--> check response'''
    if "error" in response["response"]:
        logAction("err - common.py - searchSpotify2 --> error from request: " + str(response["response"].json()["error"]["status"]) + ", " + str(response["response"].json()["error"]["message"]), category="error")
        return ''


    '''--> finally, return a valid response in json format'''
    logAction("msg - common.py - searchSpotify3 --> Succesfully returning search results for " + searchtype + " " + searchstring + ".") 
    return response["response"]


########################################################################################


########################################################################################
######################################### GOOGLE #######################################
########################################################################################
########################################################################################
def googleSearchApiRequest(searchTerm, startIndex):
    '''--> standard google api custom search request'''
    '''--> search is site-restricted to spotify with inurl:playlist '''
    '''--> limited to 100 requests/day'''
    '''--> returns json object'''

    '''--> initialize variables'''
    google_key      = ""
    google_cx       = ""
    key_data        = {}


    '''--> load key value from external file'''
    try:
        fileOpen    = open(ROOT_DIR + "/static/google_api.txt", "r")      
        key_data    = json.loads(fileOpen.read())
        google_key  = key_data["key"]
        google_cx   = key_data["cx"]
        fileOpen.close()
    except Exception as ex:
        logAction("err - common.py - googleSearchApiRequest --> error loading google keys from external files: " + str(type(ex)) + " - " + str(ex.args) + " - " + str(ex))
        logAction("TRACEBACK --> " + traceback.format_exc())
        return ''
    

    '''--> request'''
    url             = '''https://www.googleapis.com/customsearch/v1/siterestrict?key=''' + google_key + '''&cx=''' + google_cx + '''&q=''' + str(searchTerm)  + '''&start=''' + str(startIndex)
    req             = requests.get(url, verify=False)
    result_json     = json.loads(req.text)


    '''--> save result for debug purposes'''
    with open (ROOT_DIR + '/logs/gcs_result_LAST' + str(random.randrange(1, 50, 1)) + '.json', 'w') as f:
        json.dump(result_json, f, indent=2)


    '''--> return result'''
    return result_json
########################################################################################

########################################################################################

########################################################################################
######################################### GOOGLE #######################################
def extractItemsFromGoogleResponse(json_input, maxResults):
    '''--> extract requested info from a google api search response - json format'''
    '''--> returns a dict with a response and list of links'''
    '''--> response: {"result": True/False, "response": list of playlistlinks, "message": ...}'''

    '''--> initialize variables'''
    toReturn                = {}
    toReturnResult          = True
    toReturnResponse        = []
    toReturnMessage         = ""
    returnedSearchTerm      = ""
    returnedtotalResults    = 0
    returnedCountItems      = 0
    returnedStartIndex      = 0
    result_json             = json_input

    '''--> check if google search api daily rate limit is exceeded'''
    checkResponse       = checkGoogleResponse(result_json)      #returns dict {result: True/false, message:...}

    if checkResponse["result"] == False:
        toReturnResult      = False
        toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": checkResponse["message"]}
        return toReturn


    '''--> get info from response'''
    returnedSearchTerm      = result_json["queries"]["request"][0]["searchTerms"]
    returnedtotalResults    = int(result_json["searchInformation"]["totalResults"])
    returnedCountItems      = int(result_json["queries"]["request"][0]["count"])       # 20220220 - make extra check - count represents the number of items for this request. It has happened before that first request has more than 20 items, but second request only 12 (so only 2 for the second request)
    returnedStartIndex      = int(result_json["queries"]["request"][0]["startIndex"])
    logAction("msg - common.py - extractItemsFromGoogleResponse20 --> from google search response: searchTerm=" + returnedSearchTerm + ", totalResults=" + str(returnedtotalResults) + ", counted items=" + str(returnedCountItems) + ", start index=" + str(returnedStartIndex) + ".")


    '''--> check maxResults - extra check'''
    if returnedtotalResults < maxResults:
        maxResults = returnedtotalResults


    '''--> get requested data'''
    resultList      = []
    logAction("msg - common.py - extractItemsFromGoogleResponse30 --> Starting search job for " + str(returnedSearchTerm) + ", max " + str(maxResults) + " results")

    for i in range(0, maxResults):
        #if (((i % 10) !=0) or (i == 0)) and (i < returnedCountItems):
        if (((i % 10) !=0) or (i == 0)) and (i < (returnedCountItems + returnedStartIndex)-1):
            if "items" in result_json.keys():
                playlistLink    = result_json["items"][i % 10]["link"]
                resultList.append(playlistLink)
            else:
                logAction("err - common.py - googleSearchApiRequest30 --> 'items' was not found in gcs response for searchterm " + str(returnedSearchTerm) + ", startIndex: " + str(returnedStartIndex) + ", count: " + str(returnedCountItems))
                continue    #move on to next loop

        # elif i!=0 and (i < (returnedCountItems + returnedStartIndex)-1):
        elif i!=0 and ((returnedtotalResults - returnedStartIndex) !=0):
            '''--> new request every 10th loop --> next 10 results'''
            result_json     = googleSearchApiRequest(returnedSearchTerm, i+1)


            '''--> check response'''
            checkResponse       = checkGoogleResponse(result_json)      #returns dict {result: True/false, message:...}
            if checkResponse["result"] == False:
                toReturnResult      = False
                toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": checkResponse["message"]}
                return toReturn


            '''--> extract data from response'''
            returnedCountItems      = int(result_json["queries"]["request"][0]["count"])     
            returnedStartIndex      = int(result_json["queries"]["request"][0]["startIndex"])

            waitForGivenTimeIns(1,2)

            if "items" in result_json.keys():
                playlistLink        = result_json["items"][i % 10]["link"]
                # playlistName = r_json["items"][i % 10]["title"]
                resultList.append(playlistLink)
            else:
                logAction("err - common.py - googleSearchApiRequest40 --> 'items' was not found in gcs response for searchterm " + str(returnedSearchTerm) + ", startIndex: " + str(returnedStartIndex) + ", count: " + str(returnedCountItems))
                toReturnMessage     = "Fault code " + str(result_json["error"]["code"])
                continue

    '''--> return result'''
    toReturnMessage     = "Succesfully finished extractItemsFromGoogleResponse, grabbed " + str(len(resultList)) + " links."
    toReturnResult      = True
    toReturnResponse    = resultList.copy()
    toReturn            = {"result": toReturnResult, "response": toReturnResponse, "message": toReturnMessage}
    return toReturn

########################################################################################


########################################################################################
######################################### GOOGLE #######################################
def checkGoogleResponse(input_json):
    '''--> Check response from a api google custom search response'''
    '''--> Returns dict: {result: True/false, message:...}'''
    '''--> If response is ok, result = True'''

    '''--> initialize variables'''
    toReturnMessage     = ""
    toReturnResult      = False
    toReturn            = {}


    '''--> check'''
    if "error" in input_json.keys():
        if input_json["error"]["code"] == 429:
            logAction("err - common.py - checkGoogleResponse --> daily rate limit exceeded.")
            toReturnMessage     = "Rate limit exceeded."
        elif input_json["error"]["code"] == 503:
            logAction("err - common.py - checkGoogleResponse10 --> service is currently unavailable.")
            toReturnMessage     = "Service is currently unavailable."
        else:
            logAction("msg - common.py - checkGoogleResponse20 --> error from api request: " + str(input_json["error"]["code"]))
            toReturnMessage     = "Fault code " + str(input_json["error"]["code"])

        toReturnResult      = False
        toReturn            = {"result": toReturnResult, "message": toReturnMessage}
        return toReturn

    elif "searchInformation" in input_json.keys():
        if input_json["searchInformation"]["totalResults"] == "0":
            logAction("msg - common.py - checkGoogleResponse30 --> No playlists found!")
            toReturnMessage     = "No playlists found."

            toReturnResult      = False
            toReturn            = {"result": toReturnResult, "message": toReturnMessage}
            return toReturn
        else:
            toReturnResult      = True
            toReturn            = {"result": toReturnResult, "message": toReturnMessage}
            return toReturn




########################################################################################



