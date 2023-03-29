import requests
import json
import pymongo
import sys
import certifi
from location import *
from main import *
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

    print(placeValues)

    userDB = dbClient["UsersSpotifyData"]

    userFav = userDB["FavSongs"]

    userRel = userDB["RelatedSongs"]

    songQuery = {"danceability": {
        "$gte": (placeValues["danceability"]-0.1), "$lte": (placeValues["danceability"]+.1)}, "energy": {
        "$gte": (placeValues["energy"]-0.1), "$lte": (placeValues["energy"]+.1)}, "valence": {
        "$gte": (placeValues["valence"]-0.1), "$lte": (placeValues["valence"]+.1)}}

    relSongs = list(userRel.find(songQuery).limit(30))
    favSongs = list(userFav.find(songQuery).limit(75 - len(relSongs)))
    playIds = []

    data = {
        'name': placeType,
        'description': "Playlsist for " + placeType}

    headers = {"Authorization": "Bearer " + token}

    playlist = requests.post(
        "https://api.spotify.com/v1/users/"+userID+"/playlists", data=data, headers=headers)

    print(5)

    for doc in favSongs:

        playIds.append("spoitfy:track:" + doc["_id"])

    for doc in relSongs:
        playIds.append("spoitfy:track: " + doc["_id"])

    uris = {"uris": playIds}

    requestBody = json.dumps(uris)

    playlistID = playlist.json()["id"]

    requests.post("https:/api.spotify.com/v1/playlists/" +
                  playlistID+"/tracks", data=requestBody, headers=headers)


weightSongs()
