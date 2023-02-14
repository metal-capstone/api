import requests
import json

credentials_json = json.load(open("credentials.json"))

client = credentials_json["spotify_client_id"]
secret = credentials_json["spotify_client_secret"]

auth_url = 'https://accounts.spotify.com/api/token'
data = {
    'grant_type': 'client_credentials',
    'client_id': client,
    'client_secret': secret
}

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
for x in range(len(gymPlaylists)):
    gymids = ""
    headers = {"Authorization": "Bearer " + token}
    tracks = requests.get("https://api.spotify.com/v1/playlists/"+gymPlaylists[x] +
                          "/tracks?market=ES&fields=items(track(name%2Chref%2Cid))", headers=headers).json()
    for i in range(len(tracks["items"])):
        gymids = gymids + str(tracks["items"][i]["track"]["id"]) + ","

    trackNum = trackNum + len(tracks["items"])

    trackData = requests.get(
        "https://api.spotify.com/v1/audio-features?ids=" + gymids, headers=headers).json()

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

print(danceability)
print(energy)
print(instrumentalness)
print(liveness)
print(loudness)
print(speechiness)
print(tempo)
print(valence)
