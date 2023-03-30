from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import string
import random
import json
import requests
import base64
from pymongo import MongoClient
import database
import models

from songCollection import *
from spotify import *
from location import *

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5005",
    "http://localhost:5055"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebsocketRequest(BaseModel):
    websocket: WebSocket
    state: str

    class Config:
        arbitrary_types_allowed = True


# load in credentials from json file
credentials = json.load(open('credentials.json'))

# This is the scope for what info we request access to on spotify, make sure to add more to it if you need more data
app.scope = "user-read-private user-read-email user-top-read user-follow-read user-library-read user-read-playback-state user-modify-playback-state"
app.states = {}  # dict of tokens for all logged in users, theres definitely a better way to do this but it works for now


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
    # random state to check if callback request is legitimate, and for identifying user in future callbacks
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    app.states[state] = ['', '']
    # builds auth url from credentials and scope
    authorizeLink = 'https://accounts.spotify.com/authorize?response_type=code&client_id=' + \
        credentials['spotify_client_id'] + '&scope=' + app.scope + \
        '&redirect_uri=http://localhost:8000/callback&state=' + state
    return {"auth_url": authorizeLink, "state": state}

# Endpoint for the callback from the spotify login, updates access token and redirect user to dashboard when successful.


# TODO update so error is redirected to front end with error message, probably by sending an error code
@app.get("/callback")
async def root(code: str, state: str, background_tasks: BackgroundTasks):
    if (state not in app.states):  # simple check to see if request is from spotify
        return {"message": "state_mismatch"}
    else:
        encoded_credentials = base64.b64encode(credentials['spotify_client_id'].encode(
        ) + b':' + credentials['spotify_client_secret'].encode()).decode("utf-8")
        headers = {
            "Authorization": "Basic " + encoded_credentials,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        payload = {
            'grant_type': 'authorization_code',
            'code': code,  # use auth code granted from user to get access token
            'redirect_uri': 'http://localhost:8000/callback'
        }

        access_token_request = requests.post(
            url="https://accounts.spotify.com/api/token", data=payload, headers=headers)

        # upon token success, store tokens and redirect
        if (access_token_request.status_code == 200):
            app.states[state][0] = access_token_request.json()["access_token"]
            app.states[state][1] = access_token_request.json()["refresh_token"]

            #background_tasks.add_task(songCollection, app.states[state][0])

            return RedirectResponse("http://localhost:3000/dashboard", status_code=303)
        else:
            return {"message": "invalid_token"}


@app.get("/test-mongodb")
async def test_mongodb():
    response: models.TestData = database.test_mongodb(app.database)
    return response


@app.websocket("/{state}/ws")
async def websocket_endpoint(websocket: WebSocket, state: str):
    await websocket.accept()
    await websocket.send_json(getUserInfo(app.states[state][0]))
    await websocket.send_json({"type": "spotify-token", "token": app.states[state][0]})
    try:
        while True:
            data = await websocket.receive_text()
            if (data.startswith('!state')):
                await websocket.send_json({"type": "message", "message": f"State: {state}"})
            else:
                headers = { 'Content-Type': 'text/plain' }
                payload = {'message': data, 'sender': state}
                try:
                    chatbot_response = requests.post(url="http://setup-rasa-1:5005/webhooks/rest/webhook", json=payload, headers=headers)
                    if (chatbot_response.status_code == 200 and chatbot_response.json()):
                        response = chatbot_response.json()[0]['text']
                        if (response == 'Start Music Action'):
                            response = getRecSong(app.states[state][0])['song']
                    else:
                        response = "Error" + chatbot_response.status_code
                except:
                    response = "Error sending chatbot request. Wait until the rasa server has started"
                await websocket.send_json({"type": "message", "message": response})
    except WebSocketDisconnect:
        print('User Disconnected')
