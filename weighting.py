import requests
import json
import pymongo
import sys
import certifi
from location import *

credentials_json = json.load(open("credentials.json"))
client = credentials_json["spotify_client_id"]
secret = credentials_json["spotify_client_secret"]


def weightSongs():


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

favSongs = userFav.find(songQuery).limit(45)

for doc in favSongs:
    print(doc)
