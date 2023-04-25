import httpx
import base64
import json

CREDENTIALS = json.load(open('credentials.json'))

# This is the scope for what info we request access to on spotify, make sure to add more to it if you need more data
SCOPE = ' '.join(['user-read-private', 'user-read-email', 'user-top-read',
                  'user-follow-read', 'user-library-read', 'user-read-playback-state',
                  'user-modify-playback-state', 'playlist-modify-public', 'playlist-modify-private'])

REDIRECT_URI = 'http://localhost:8000/callback'

# Builds auth url from credentials and scope, url goes to spotify accounts page for user approval
def generateAuthLink(state: str, showDialog: bool) -> str:
    authorizeLink = (f"https://accounts.spotify.com/authorize?response_type=code"
                     f"&client_id={CREDENTIALS['spotify_client_id']}&scope={SCOPE}"
                     f"&redirect_uri={REDIRECT_URI}&state={state}&show_dialog={showDialog}")
    return authorizeLink

# header to use for spotify requests for the server like auth
def generateAuthHeader() -> dict[str, str]:
    encodedCredentials = base64.b64encode(CREDENTIALS['spotify_client_id'].encode() + b':' +
                                          CREDENTIALS['spotify_client_secret'].encode()).decode('utf-8')
    return {
        'Authorization': 'Basic ' + encodedCredentials,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

# used in callback in main, gets the auth tokens from spotify and returns them
def getAuthTokens(code: str) -> tuple[str, str]:
    authHeader = generateAuthHeader()
    authData = {
        'grant_type': 'authorization_code',
        'code': code,  # Use auth code granted from user to get access token
        'redirect_uri': REDIRECT_URI
    }
    authTokens = httpx.post(url='https://accounts.spotify.com/api/token', data=authData, headers=authHeader).json()
    return authTokens['access_token'], authTokens['refresh_token']
    

# User header needed for specific user requests
def getUserHeader(accessToken: str) -> dict[str, str]:
    userHeader = {
        'Authorization': 'Bearer ' + accessToken,
        'Content-Type': 'application/json'
    }
    return userHeader

# function to get a new access token from spotify, returns new token
def getAccessToken(refreshToken: str) -> str:
    header = generateAuthHeader()
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refreshToken
    }
    tokens = httpx.post('https://accounts.spotify.com/api/token', data=data, headers=header).json()
    return tokens['access_token']

# gets users spotify info for a new session, returns uri and username. Sent to start session in session manager
def getSessionUserInfo(accessToken: str) -> tuple[str, str]:
    userHeader = getUserHeader(accessToken)
    userInfo = httpx.get('https://api.spotify.com/v1/me', headers=userHeader).json()
    return userInfo['uri'], userInfo['display_name']

# Users spotify info, returns username and profile picture if it exists. Sent to user via websocket
def getUserInfo(accessToken: str) -> tuple[str, str] | str:
    userHeader = getUserHeader(accessToken)
    userInfo = httpx.get('https://api.spotify.com/v1/me', headers=userHeader).json()
    # checks if user has a profile picture
    if ('images' in userInfo and userInfo['images']):
        return userInfo['display_name'], userInfo['images'][0]['url']
    else:
        return userInfo['display_name'], None
    
# method to get users top artists or tracks, async to make large, concurrent requests quicker
async def getUserTopItemsAsync(accessToken: str, type: str, timeRange: str, limit: int, offset: int) -> list[str]:
    userHeader = getUserHeader(accessToken)
    params = {
        'time_range': timeRange,
        'limit': limit,
        'offset': offset
    }
    async with httpx.AsyncClient() as client:
        topItems = await client.get(f"https://api.spotify.com/v1/me/top/{type}", params=params, headers=userHeader)
        topItems = topItems.json() # take json after await so it does not happen on the coroutine
        return [ item['uri'] for item in topItems['items'] ]

# method to use spotify's recommendation endpoint, needs to have all relevant params before call
def recommendSongs(accessToken: str, params: dict[str, any]) -> list[dict]:
    userHeader = getUserHeader(accessToken)
    songs = httpx.get("https://api.spotify.com/v1/recommendations", params=params, headers=userHeader, timeout=10.0).json()
    return songs['tracks']

# plays the list of song uris on the users active playback
def playSong(accessToken: str, songURIs: list[str]):
    userHeader = getUserHeader(accessToken)
    httpx.put("https://api.spotify.com/v1/me/player/play", json={"uris": songURIs}, headers=userHeader)

# plays the context (album or playlist) on the users active playback
def playContext(accessToken: str, contextURI: str):
    userHeader = getUserHeader(accessToken)
    httpx.put("https://api.spotify.com/v1/me/player/play", json={'context_uri': contextURI}, headers=userHeader)

# creates playlist on users profile, returns new playlist data, needs all relevant data before call
def createPlaylist(accessToken: str, userID: str, data: dict[str, any]) -> dict[str, any]:
    userHeader = getUserHeader(accessToken)
    playlist = httpx.post(f"https://api.spotify.com/v1/users/{userID}/playlists", json=data, headers=userHeader)
    return playlist.json()

# adds the song uris to the playlist
def addToPlaylist(accessToken: str, playlistID: str, songURIS: list[str]):
    userHeader = getUserHeader(accessToken)
    httpx.post(f"https://api.spotify.com/v1/playlists/{playlistID}/tracks", json=songURIS, headers=userHeader)

