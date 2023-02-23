from fastapi import FastAPI, WebSocket
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import string
import random
import json
import requests
import base64
from pymongo import MongoClient
import database
import models

from songCollection import *

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

creds = json.load(open('credentials.json')) # load in creds from json file

app.scope = "user-read-private user-read-email user-top-read user-follow-read user-library-read" # This is the scope for what info we request access to on spotify, make sure to add more to it if you need more data
app.state = '' # TODO update api to work with multiple users, this should be per user not global. Still could work with multiple user might be issues if multiple are signing in at the same time
app.access_token = ''
app.refresh_token = ''

@app.on_event("startup")
def startup_db_client():
    app.mongodb_client = MongoClient(database.MONGODB_DATABASE_URL)
    app.database = app.mongodb_client[database.MONGODB_CLUSTER_NAME]

    database.test_mongodb(app.database)

@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()

@app.get("/")
async def root():
    return {"message": "api is running"}

# Endpoint that generates the authorization url for the user
@app.get("/spotify-login")
async def root():
    # random state to check if callback request is legitimate
    app.state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    # builds auth url from credentials and scope
    authorizeLink = 'https://accounts.spotify.com/authorize?response_type=code&client_id=' + creds['spotify_client_id'] + '&scope=' + app.scope + '&redirect_uri=http://localhost:8000/callback&state=' + app.state
    return { "auth_url": authorizeLink }

# Endpoint for the callback from the spotify login, updates access token and redirect user to dashboard when successful.
@app.get("/callback") # TODO update so error is redirected to front end with error message, probably by sending an error code
async def root(code: str, state: str):
    if (state != app.state): # simple check to see if request is from spotify
        return {"message": "state_mismatch"}
    else:
        app.state = ""
        encoded_credentials = base64.b64encode(creds['spotify_client_id'].encode() + b':' + creds['spotify_client_secret'].encode()).decode("utf-8")
        headers = {
            "Authorization": "Basic " + encoded_credentials,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        payload = {
            'grant_type': 'authorization_code',
            'code': code, #use auth code granted from user to get access token
            'redirect_uri': 'http://localhost:8000/callback'
        }

        access_token_request = requests.post(url="https://accounts.spotify.com/api/token", data=payload, headers=headers)

        if (access_token_request.status_code == 200): #upon token success, store tokens and redirect
            app.access_token = access_token_request.json()["access_token"]
            app.refresh_token = access_token_request.json()["refresh_token"]

            #songCollection(app.access_token)

            return RedirectResponse("http://localhost:3000/dashboard", status_code=303)
        else:
            return {"message": "invalid_token"}

# Endpoint to get current users username and url to profile pic
@app.get("/user-info") # TODO Add some check that there is current user, send error if not
async def root():
    user_headers = {
        "Authorization": "Bearer " + app.access_token,
        "Content-Type": "application/json"
    }
    user_params = {
        "limit": 50
    }
    user_info_response = requests.get("https://api.spotify.com/v1/me", params=user_params, headers=user_headers)
    user_info = user_info_response.json()
    return { "username": user_info['display_name'], "profile_pic": user_info['images'][0]['url'] }

# this is just an example endpoint to show how to query info, this will get the users most listen to songs of the past 6 months
@app.get("/user-top-songs")
async def root():
    user_headers = {
        "Authorization": "Bearer " + app.access_token,
        "Content-Type": "application/json"
    }
    user_params = {
        "limit": 50,
        "time_range": "medium_term"
    }
    user_tracks_response = requests.get("https://api.spotify.com/v1/me/top/tracks", params=user_params, headers=user_headers)
    user_tracks = user_tracks_response.json()
    return { "songs": user_tracks['items'] }

@app.get("/test-mongodb")
async def test_mongodb():
    response: models.TestData = database.test_mongodb(app.database)
    return response

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")