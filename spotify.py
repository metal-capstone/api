import httpx
import base64
import weighting
import json

credentials = json.load(open('credentials.json'))

# This is the scope for what info we request access to on spotify, make sure to add more to it if you need more data
scope = ' '.join(['user-read-private', 'user-read-email', 'user-top-read',
                  'user-follow-read', 'user-library-read', 'user-read-playback-state',
                  'user-modify-playback-state', 'playlist-modify-public', 'playlist-modify-private'])

# Builds auth url from credentials and scope
def getAuthLink(state):
    authorizeLink = 'https://accounts.spotify.com/authorize?response_type=code&client_id=' + \
                    credentials['spotify_client_id'] + '&scope=' + scope + \
                    '&redirect_uri=http://localhost:8000/callback&state=' + state
    return authorizeLink

# Header and payload needed for access tokens
def accessTokenRequestInfo(code):
    encoded_credentials = base64.b64encode(credentials['spotify_client_id'].encode() + b':' +
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

# function to get a new access token from spotify, either returns new token or raises exception
def getAccessToken(refresh_token):
    header, unused_payload = accessTokenRequestInfo('')
    payload = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    access_token_response = httpx.post('https://accounts.spotify.com/api/token', data=payload, headers=header)
    if (access_token_response.status_code == 200):
        return access_token_response.json()['access_token']
    else:
        raise Exception(f"Error getting new token (Status Code: {access_token_response.status_code})")

# gets users spotify info for a new session, returns uri and username. Sent to start session in util
def getSessionUserInfo(access_token):
    user_header = getUserHeader(access_token)
    user_info_response = httpx.get('https://api.spotify.com/v1/me', headers=user_header)
    if (user_info_response.status_code == 200):
        user_info = user_info_response.json()
        return user_info['uri'], user_info['display_name']
    else:
        raise Exception(f"Error getting user info (Status Code: {user_info_response.status_code})")

# Users spotify info, returns username and profile picture if it exists. Sent to user via websocket
def getUserInfo(access_token):
    user_header = getUserHeader(access_token)
    try:
        user_info_response = httpx.get('https://api.spotify.com/v1/me', headers=user_header)
        if (user_info_response.status_code == 200):
            user_info = user_info_response.json()
            # checks if user has a profile picture
            if ('images' in user_info and user_info['images']):
                return {'type': 'user-info', 'username': user_info['display_name'], 'id': user_info['id'], 'profile_pic': user_info['images'][0]['url']}
            else:
                return {'type': 'user-info', 'username': user_info['display_name'], 'id': user_info['id']}
        else:
            return {'type': 'error', 'error': f"(getUserInfo) Error getting spotify user info. (Status Code:{user_info_response.status_code})"}
    except httpx.RequestError as error:
        return {'type': 'error', 'error': f"(getUserInfo) Error getting response from spotify. ({error})"}
    
async def getUserTopItemsAsync(access_token, type, time_range, limit, offset):
    user_header = getUserHeader(access_token)
    params = {
        'time_range': time_range,
        'limit': limit,
        'offset': offset
    }
    async with httpx.AsyncClient() as client:
        top_items_response = await client.get(f"https://api.spotify.com/v1/me/top/{type}", params=params, headers=user_header)
        if (top_items_response.status_code == 200):
            top_items = top_items_response.json()
            return [ item['uri'] for item in top_items['items'] ]
        else:
            print(f"Error getting top items ({top_items_response.status_code})")

def recommendSongs(access_token, params):
    user_header = getUserHeader(access_token)
    try:
        songs_response = httpx.get("https://api.spotify.com/v1/recommendations", params=params, headers=user_header)
        if (songs_response.status_code == 200):
            songs = songs_response.json()
            return songs['tracks']
        else:
            print(f"Error getting recommended songs ({songs_response.status_code})")
    except Exception as e:
        print(e)

def playSong(access_token, ids):
    user_header = getUserHeader(access_token)
    try:
        play_response = httpx.put("https://api.spotify.com/v1/me/player/play", json={"uris": ids}, headers=user_header)
        if (play_response.status_code != 204):
            print(f"Error playing songs ({play_response.status_code})")
    except Exception as e:
        print(e)

def playContext(access_token, playlist_uri):
    user_header = getUserHeader(access_token)
    httpx.put("https://api.spotify.com/v1/me/player/play", json={'context_uri': playlist_uri}, headers=user_header)

def createPlaylist(access_token, user_id, data):
    user_header = getUserHeader(access_token)
    playlist = httpx.post("https://api.spotify.com/v1/users/"+user_id+"/playlists", data=json.dumps(data), headers=user_header)
    return playlist.json()

def addToPlaylist(access_token, playlist_id, uris):
    user_header = getUserHeader(access_token)
    httpx.post("https://api.spotify.com/v1/playlists/" + playlist_id + "/tracks", data=json.dumps(uris), headers=user_header)

