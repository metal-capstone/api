import requests
import json
import pymongo
import sys
import certifi
from location import *

credentials_json = json.load(open("credentials.json"))
client = credentials_json["spotify_client_id"]
secret = credentials_json["spotify_client_secret"]


def weightSongs(userID, token):

    dbClient = pymongo.MongoClient(
        "mongodb+srv://metal-user:djKjLBF62wmcu0gl@spotify-chatbot-cluster.pnezn7m.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=certifi.where())

    placeDB = dbClient["PlaceClusters"]

    placeCollection = placeDB["PlaceType"]

    placeType = getPlace()

    placeQuery = {"Place": placeType}

    placeValues = placeCollection.find_one(placeQuery)

    userDB = dbClient["UsersSpotifyData"]

    userFav = userDB["FavSongs"]

    userRel = userDB["RelatedSongs"]

    songQuery = {"danceability": {
        "$gte": (placeValues["danceability"]-0.1), "$lte": (placeValues["danceability"]+.1)}, "energy": {
        "$gte": (placeValues["energy"]-0.1), "$lte": (placeValues["energy"]+.1)}, "valence": {
        "$gte": (placeValues["valence"]-0.1), "$lte": (placeValues["valence"]+.1)}}

    relSongs = list(userRel.find(songQuery).limit(30))

    favSongs = list(userFav.find(songQuery).limit(75-len(relSongs)))

    data = {
        'name': placeType,
        'description': "Playlist for " + placeType.capitalize(),
        'public': True

    }

    headers = {"Authorization": "Bearer " +
               token, "Content-Type": "application/json"}

    playlist = requests.post(
        "https://api.spotify.com/v1/users/"+userID+"/playlists", data=json.dumps(data), headers=headers).json()
    print(playlist)

    playIds = []
    for doc in favSongs:
        playIds.append("spotify:track:" + str(doc['_id']))

    for doc in relSongs:
        playIds.append("spotify:track:" + str(doc['_id']))

    uris = {"uris": playIds, "position": 0}

    playlistID = playlist['id']
    print(playlistID)

    playlistURI = playlist['uri']
    print(playlistURI)

    requests.post("https://api.spotify.com/v1/playlists/" +
                  playlistID + "/tracks", data=json.dumps(uris), headers=headers)

    uriJson = {"context_uri": playlistURI}

    headers = {"Authorization": "Bearer " +
               token, "Content-Type": "application/json"}

    requests.put("https://api.spotify.com/v1/me/player/play",
                 data=json.dumps(uriJson), headers=headers)
    return {'txt': str("Playlist Created for " + placeType.capitalize())}


def weightSongsTemp():  # temporary weight songs method for time box 4

    dbClient = pymongo.MongoClient(
        "mongodb+srv://metal-user:djKjLBF62wmcu0gl@spotify-chatbot-cluster.pnezn7m.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=certifi.where())

    placeDB = dbClient["PlaceClusters"]

    placeCollection = placeDB["PlaceType"]

    placeType = getPlace()

    placeQuery = {"Place": placeType}

    placeValues = placeCollection.find_one(placeQuery)

    return placeValues
