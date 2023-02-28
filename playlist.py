import requests
import json
import pymongo
import sys
import certifi

credentials_json = json.load(open("credentials.json"))
client = credentials_json["spotify_client_id"]
secret = credentials_json["spotify_client_secret"]


auth_url = 'https://accounts.spotify.com/api/token'
data = {
    'grant_type': 'client_credentials',
    'client_id': client,
    'client_secret': secret
}

dbClient = pymongo.MongoClient(
    "mongodb+srv://metal-user:djKjLBF62wmcu0gl@spotify-chatbot-cluster.pnezn7m.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=certifi.where())

myDB = dbClient["PlaceClusters"]

collection = myDB["PlaceType"]


auth_response = requests.post(auth_url, data=data).json()
token = auth_response['access_token']

danceability = 0
energy = 0
instrumentalness = 0
liveness = 0
loudness = 0
speechiness = 0
tempo = 0
valence = 0
trackNum = 0


gymPlaylists = ["37i9dQZF1DWTl4y3vgJOXW",
                "37i9dQZF1DX8CwbNGNKurt", "37i9dQZF1DX5gQonLbZD9s"]


libraryPlaylists = ["37i9dQZF1DX8NTLI2TtZa6",
                    "37i9dQZF1DX9sIqqvKsjG8", "37i9dQZF1DWZeKCadgRdKQ"]


barPlaylists = ["5xS3Gi0fA3Uo6RScucyct6",
                "5fAcG9Ac4qqGJJ3udoI1rt", "4ZO8nLqmmVX0y0PZfarUH4"]


restaurantPlaylists = ["2UJd3dltnIGkMqhAbQSkbS",
                       "345eEKyGNyluygzMsS1n1H", "4JFuLQEnxDu8UQUgGGzZzm"]

cafePlaylists = ["37i9dQZF1DXa1BeMIGX5Du",
                 "3gEQvSqzd61hRcwj0jUpL2", "2UdyLLfoU9RxSMOSQeHjRl"]

for x in range(len(cafePlaylists)):
    ids = ""
    headers = {"Authorization": "Bearer " + token}
    tracks = requests.get("https://api.spotify.com/v1/playlists/"+cafePlaylists[x] +
                          "/tracks?market=ES&fields=items(track(name%2Chref%2Cid))", headers=headers).json()

    for i in range(len(tracks["items"])):
        ids = ids + str(tracks["items"][i]["track"]["id"]) + ","

    trackNum = trackNum + len(tracks["items"])

    trackData = requests.get(
        "https://api.spotify.com/v1/audio-features?ids=" + ids, headers=headers).json()

    for i in range(len(trackData["audio_features"])):

        danceability = danceability + \
            trackData["audio_features"][i]["danceability"]
        energy = energy + trackData["audio_features"][i]["energy"]
        instrumentalness = instrumentalness + \
            trackData["audio_features"][i]["instrumentalness"]
        liveness = liveness + trackData["audio_features"][i]["liveness"]
        loudness = loudness + \
            trackData["audio_features"][i]["loudness"]
        speechiness = speechiness + \
            trackData["audio_features"][i]["speechiness"]
        tempo = tempo + \
            trackData["audio_features"][i]["tempo"]
        valence = valence + trackData["audio_features"][i]["valence"]


danceability = danceability / trackNum
energy = energy / trackNum
instrumentalness = instrumentalness / trackNum
liveness = liveness / trackNum
loudness = loudness / trackNum
speechiness = speechiness / trackNum
tempo = tempo / trackNum
valence = valence / trackNum

Cafe = {
    "Place": "Cafe",
    "danceability": danceability,
    "energy": energy,
    "instrumentalness": instrumentalness,
    "liveness": liveness,
    "loudness": loudness,
    "speechiness": speechiness,
    "tempo": tempo,
    "valence": valence
}


x = collection.insert_one(Cafe)
print(x)


# print("danceability: " + str(danceability))
# print("energy: " + str(energy))
# print("instrumentalness: " + str(instrumentalness))
# print("liveness: " + str(liveness))
# print("loudness: " + str(loudness))
# print("speechiness: " + str(speechiness))
# print("tempo: " + str(tempo))
# print("valence: " + str(valence))
