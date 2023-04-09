from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

import requests
import secrets

import database
import models
import spotify
import sessions

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

app.states = {}  # dict for all states, stores the related session id
app.sessions = sessions.SessionManager()  # dict for all active sessions, stores the access_token

@app.on_event('startup')
def startup_db_client():
    database.test_mongodb()

@app.on_event('shutdown')
def shutdown_db_client():
    database.close_client()

@app.get('/')
async def root():
    return {'message': 'api is running'}

# Endpoint that generates the authorization url for the user
@app.get('/spotify-login')
async def root():
    # random state to check if callback request is legitimate, and for identifying user in future callbacks
    state = secrets.token_urlsafe(16)
    session_id = secrets.token_urlsafe(16)
    app.states[state] = session_id
    authorizeLink = spotify.getAuthLink(state)
    return {'auth_url': authorizeLink, 'session_id': session_id}

# Endpoint for the callback from the spotify login, updates access token and redirect user to dashboard when successful.
# code is the key to get users auth tokens, if it fails you get error instead. If it fails remove state from states
@app.get('/callback')
async def root(state: str, background_tasks: BackgroundTasks, code: str | None = None, error: str | None = None):
    if (state not in app.states):  # simple check to see if request is from spotify
        return RedirectResponse('http://localhost:3000/?error=state_mismatch', status_code=303)
    elif (error is not None): # Check if theres an error from spotify
        app.states.pop(state)
        return RedirectResponse(f"http://localhost:3000/?error=spotify_{error}", status_code=303)
    else:
        try:
            headers, payload = spotify.accessTokenRequestInfo(code)
            access_token_request = requests.post(url='https://accounts.spotify.com/api/token', data=payload, headers=headers)

            # upon token success, store tokens and redirect
            if (access_token_request.status_code == 200):
                access_tokens = access_token_request.json()
                session_id = app.states[state]
                app.states.pop(state)
                
                app.sessions.startSession(session_id, access_tokens['access_token'], access_tokens['refresh_token'], background_tasks)

                return RedirectResponse('http://localhost:3000/dashboard', status_code=303)
            else:
                app.states.pop(state)
                return RedirectResponse('http://localhost:3000/?error=invalid_token', status_code=303)
        except requests.exceptions.RequestException:
            app.states.pop(state)
            return RedirectResponse('http://localhost:3000/?error=spotify_accounts_error', status_code=303)

@app.get('/test-mongodb')
async def test_mongodb():
    response: models.TestData = database.test_mongodb(app.database)
    return response

# This is the main websocket endpoint, the user provides their state and connects to the backend if its found
@app.websocket('/{session_id}/ws')
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    if (app.sessions.linkSession(session_id, websocket)):
        await websocket.send_json({'type': 'log-status', 'loggedIn': True})
        await websocket.send_json(spotify.getUserInfo(app.sessions.getAccessToken(session_id)))
        await websocket.send_json({'type': 'spotify-token', 'token': app.sessions.getAccessToken(session_id)}) # Send token for web player
        try: # Try until disconnection
            while app.sessions.validSession(session_id): # Main loop to wait for user message and then handle it
                data = await websocket.receive_json() # Get message

                # Command handler, check if message is a command before sending it to chatbot
                if (data['type'] == 'logout'):
                    database.clear_session(session_id)
                    app.sessions.disconnectSession(session_id)
                elif (data['type'] == '!session'):
                    await websocket.send_json({'type': 'message', 'message': f"Session ID: {session_id}"})
                elif (data['type'] == 'message'): # Not a command, send to chatbot
                    try: # Try to request chatbot, will fail if it is not running
                        headers, payload = {'Content-Type': 'text/plain'}, {'message': data['message'], 'sender': session_id}
                        chatbot_response = requests.post(url='http://setup-rasa-1:5005/webhooks/rest/webhook', json=payload, headers=headers)

                        if (chatbot_response.status_code == 200 and chatbot_response.json()): # Parse message if request is valid and message is not empty
                            text_response = chatbot_response.json()[0]['text']
                            # Action handler, perform certain actions based on chatbot response
                            if (text_response == 'Start Music Action'):
                                response = spotify.getRecSong(app.sessions.getAccessToken(session_id))
                            else:
                                response = {'type': 'message', 'message': text_response}
                            
                        else:
                            response = {'type': 'error', 'error': f"Error receiving message: {chatbot_response.status_code}"}
                    except requests.exceptions.RequestException as error:
                        response = {'type': 'error', 'error': f"Error sending chatbot request. ({error})"}
                        
                    # Send the user the final response
                    await websocket.send_json(response)
            await websocket.send_json({'type': 'log-status', 'loggedIn': False})
            await websocket.send_json({'type': 'message', 'message': 'Logged Out'})
        except WebSocketDisconnect:
            app.sessions.disconnectSession(session_id)
    else:
        await websocket.send_json({'type': 'log-status', 'loggedIn': False})
        await websocket.send_json({'type': 'message', 'message': 'Unable to link to a session'})
