from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

import string
import random
import requests

import database
import models
import spotify

from songCollection import *
from location import *

app = FastAPI()

origins = [
    'http://localhost',
    'http://localhost:3000',
    'http://localhost:5005',
    'http://localhost:5055'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.states = {}  # dict of tokens for all logged in users, theres definitely a better way to do this but it works for now

@app.on_event('startup')
def startup_db_client():
    app.mongodb_client = MongoClient(database.MONGODB_DATABASE_URL)
    app.database = app.mongodb_client[database.MONGODB_CLUSTER_NAME]

    database.test_mongodb(app.database)

@app.on_event('shutdown')
def shutdown_db_client():
    app.mongodb_client.close()

@app.get('/')
async def root():
    return {'message': 'api is running'}

# Endpoint that generates the authorization url for the user
@app.get('/spotify-login')
async def root():
    # random state to check if callback request is legitimate, and for identifying user in future callbacks
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    app.states[state] = ['', '']
    authorizeLink = spotify.getAuthLink(state)
    return {'auth_url': authorizeLink, 'state': state}

# Endpoint for the callback from the spotify login, updates access token and redirect user to dashboard when successful.
@app.get('/callback')
async def root(code: str, state: str, background_tasks: BackgroundTasks):
    if (state not in app.states):  # simple check to see if request is from spotify
        return RedirectResponse('http://localhost:3000/?error=state_mismatch', status_code=303)
    else:
        headers, payload = spotify.accessTokenRequestInfo(code)
        access_token_request = requests.post(url='https://accounts.spotify.com/api/token', data=payload, headers=headers)

        # upon token success, store tokens and redirect
        if (access_token_request.status_code == 200):
            app.states[state][0] = access_token_request.json()['access_token']
            app.states[state][1] = access_token_request.json()['refresh_token']

            #background_tasks.add_task(songCollection, app.states[state][0])

            return RedirectResponse('http://localhost:3000/dashboard', status_code=303)
        else:
            return RedirectResponse('http://localhost:3000/?error=invalid_token', status_code=303)

@app.get('/test-mongodb')
async def test_mongodb():
    response: models.TestData = database.test_mongodb(app.database)
    return response

# Simple endpoint to check if a state is valid for a session, 404 if not found
@app.get('/{state}/session-valid')
async def root(state: str, response: Response):
    if (state in app.states):
        return { 'message': 'session-valid' }
    else:
        response.status_code = 404
        return { 'error': 'session not found' }
    
# Endpoint to end a session, removes state from list of states
@app.post('/{state}/session-logout')
async def root(state: str):
    if (state in app.states):
        app.states.pop(state)
        return { "message": "Logout Successful"}

# This is the main websocket endpoint, the user provides their state and connects to the backend if its found
@app.websocket('/{state}/ws')
async def websocket_endpoint(websocket: WebSocket, state: str):
    if (state in app.states):
        await websocket.accept()
        await websocket.send_json(spotify.getUserInfo(app.states[state][0]))
        await websocket.send_json({'type': 'spotify-token', 'token': app.states[state][0]}) # Send token for web player
        try: # Try until disconnection
            while True: # Main loop to wait for user and then handle it
                data = await websocket.receive_text() # Get message

                # Command handler, check if message is a command before sending it to chatbot
                if (data.startswith('!state')):
                    await websocket.send_json({'type': 'message', 'message': f"State: {state}"})
                else: # Not a command, send to chatbot
                    try: # Try to request chatbot, will fail if it is not running
                        headers = { 'Content-Type': 'text/plain' }
                        payload = {'message': data, 'sender': state}
                        chatbot_response = requests.post(url='http://setup-rasa-1:5005/webhooks/rest/webhook', json=payload, headers=headers)

                        if (chatbot_response.status_code == 200 and chatbot_response.json()): # Parse message if request is valid and message is not empty
                            response = chatbot_response.json()[0]['text']

                            # Action handler, perform certain actions based on chatbot response
                            if (response == 'Start Music Action'):
                                response = spotify.getRecSong(app.states[state][0])['song']
                            
                        else:
                            response = f"Error receiving message: {chatbot_response.status_code}"
                    except:
                        response = 'Error sending chatbot request. Wait until the rasa server has started'

                    # Send the user the final response
                    await websocket.send_json({'type': 'message', 'message': response})
        except WebSocketDisconnect:
            print('User Disconnected')
    else:
        print('Session not found')
