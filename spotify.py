import requests
from weighting import *

def getUserInfo(access_token):
    user_headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json"
    }
    user_params = {
        "limit": 50
    }
    user_info_response = requests.get("https://api.spotify.com/v1/me", params=user_params, headers=user_headers)
    user_info = user_info_response.json()
    return { "type":"user-info", "username": user_info['display_name'], "profile_pic": user_info['images'][0]['url'] }

def getRecSong(access_token):
    placeValues = weightSongs()
    user_headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json"
    }
    user_params = {
        "limit": 1,
        "seed_artists": "",
        "seed_tracks": "",
        "seed_genres": "hip-hop,pop",
        "min_danceability": placeValues["danceability"]-.05,
        "min_energy": placeValues["energy"]-.05,
        "min_valence": placeValues["valence"]-.05,
        "max_danceability": placeValues["danceability"]+.05,
        "max_energy": placeValues["energy"]+.05,
        "max_valence": placeValues["valence"]+.05,
    }
    song_response = requests.get("https://api.spotify.com/v1/recommendations", params=user_params, headers=user_headers)
    song = song_response.json()
    requests.put("https://api.spotify.com/v1/me/player/play", json={"uris": [song['tracks'][0]['uri']]}, headers=user_headers)
    return {"song": song['tracks'][0]['name']}