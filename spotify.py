import requests
import base64
import weighting
import json

credentials = json.load(open('credentials.json'))

# This is the scope for what info we request access to on spotify, make sure to add more to it if you need more data
scope = ' '.join(['user-read-private','user-read-email','user-top-read',
                  'user-follow-read','user-library-read','user-read-playback-state',
                  'user-modify-playback-state'])

# Builds auth url from credentials and scope
def getAuthLink(state):
    authorizeLink = 'https://accounts.spotify.com/authorize?response_type=code&client_id=' + \
                    credentials['spotify_client_id'] + '&scope=' + scope + \
                    '&redirect_uri=http://localhost:8000/callback&state=' + state
    return authorizeLink

# Header and payload needed for access tokens
def accessTokenRequestInfo(code):
    encoded_credentials = base64.b64encode(credentials['spotify_client_id'].encode() + b':' + \
                                           credentials['spotify_client_secret'].encode()).decode('utf-8')
    headers = {
        'Authorization': 'Basic ' + encoded_credentials,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {
        'grant_type': 'authorization_code',
        'code': code,  # Use auth code granted from user to get access token
        'redirect_uri': 'http://localhost:8000/callback'
    }
    return headers, payload
    
# User header needed for specific user requests
def getUserHeader(access_token):
    user_header = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }
    return user_header

# Users spotify info, returns username and profile picture if it exists
def getUserInfo(access_token):
    user_header = getUserHeader(access_token)
    try:
        user_info_response = requests.get('https://api.spotify.com/v1/me', headers=user_header)
        if (user_info_response.status_code == 200):
            user_info = user_info_response.json()
            if ('images' in user_info and user_info['images']): # checks if user has a profile picture
                return {'type': 'user-info', 'username': user_info['display_name'], 'profile_pic': user_info['images'][0]['url']}
            else:
                return {'type': 'user-info', 'username': user_info['display_name']}
        else:
            return {'type': 'error', 'error': f"(getUserInfo) Error getting spotify user info. (Status Code:{user_info_response.status_code})"}
    except requests.exceptions.RequestException as error:
        return {'type': 'error', 'error': f"(getUserInfo) Error getting response from spotify. ({error})"}

# Temp function for time box 4
def getRecSong(access_token):
    placeValues = weighting.weightSongsTemp()
    user_header = getUserHeader(access_token)
    user_params = {
        "limit": 1,
        "seed_artists": "",
        "seed_tracks": "",
        "seed_genres": "hip-hop,pop",
        "min_danceability": placeValues["danceability"]-.05,
        "min_energy": placeValues["energy"]-.05,
        "min_valence": placeValues["valence"]-.05,
        "max_danceability": placeValues["danceability"]+.1,
        "max_energy": placeValues["energy"]+.1,
        "max_valence": placeValues["valence"]+.05,
    }
    song_response = requests.get("https://api.spotify.com/v1/recommendations", params=user_params, headers=user_header)
    song = song_response.json()
    requests.put("https://api.spotify.com/v1/me/player/play", json={"uris": [song['tracks'][0]['uri']]}, headers=user_header)
    return {"song": song['tracks'][0]['name']}