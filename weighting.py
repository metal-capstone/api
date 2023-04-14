import json
import pymongo
import certifi
import httpx
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
    lim = 75

    songQuery = {"danceability": {
        "$gte": (placeValues["danceability"]-0.1), "$lte": (placeValues["danceability"]+.1)}, "energy": {
        "$gte": (placeValues["energy"]-0.1), "$lte": (placeValues["energy"]+.1)}, "valence": {
        "$gte": (placeValues["valence"]-0.1), "$lte": (placeValues["valence"]+.1)}}

    relSongs = list(userRel.find(songQuery).limit(30))

    favSongs = list(userFav.find(songQuery).limit(75-len(relSongs)))
    lim = 75 - len(relSongs) - len(favSongs)
    print(lim)

    user_params = {
        "limit": lim,
        "seed_artists": "",
        "seed_tracks": "",
        "seed_genres": "hip-hop,pop,house,chill,alternative",
        "min_danceability": placeValues["danceability"]-.2,
        "target_danceability": placeValues["danceability"],
        "min_energy": placeValues["energy"]-.2,
        "target_energy": placeValues["energy"],
        "min_valence": placeValues["valence"]-.2,
        "max_danceability": placeValues["danceability"]+.2,
        "max_energy": placeValues["energy"]+.2,
        "max_valence": placeValues["valence"]+.2,
        "target_valence": placeValues["valence"],
    }

    headers = {"Authorization": "Bearer " +
               token, "Content-Type": "application/json"}
    reqSongs = {}
    reqList = []
    if (lim > 0):
        reqSongs = httpx.get(
            "https://api.spotify.com/v1/recommendations", params=user_params, headers=headers).json()
        reqList = list(reqSongs['tracks'])

    data = {
        'name': placeType,
        'description': "Playlist for " + placeType.capitalize(),
        'public': True

    }

    userID = userID.split(':')[2]

    playlist = httpx.post(
        "https://api.spotify.com/v1/users/"+userID+"/playlists", data=json.dumps(data), headers=headers).json()

    playIds = []
    for doc in favSongs:
        playIds.append("spotify:track:" + str(doc['_id']))

    for doc in relSongs:
        playIds.append("spotify:track:" + str(doc['_id']))

    for doc in reqList:
        playIds.append("spotify:track:" + str(doc['id']))

    uris = {"uris": playIds, "position": 0}

    playlistID = playlist['id']

    playlistURI = playlist['uri']

    httpx.post("https://api.spotify.com/v1/playlists/" +
                  playlistID + "/tracks", data=json.dumps(uris), headers=headers)

    uriJson = {"context_uri": playlistURI}

    headers = {"Authorization": "Bearer " +
               token, "Content-Type": "application/json"}

    httpx.put("https://api.spotify.com/v1/me/player/play",
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
