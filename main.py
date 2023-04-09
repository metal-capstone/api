from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

import requests
import secrets

import database
import models
import spotify
import sessions
import util

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

app.states = set()  # set for all active states, stored only temporarily until spotify callback
app.sessions: sessions.SessionManager = sessions.SessionManager()  # object for all active sessions, stores session info

#app.add_middleware(util.ASGIMiddleware, sessions=app.sessions)

@app.on_event('startup')
def startup_db_client():
    database.test_mongodb()

@app.on_event('shutdown')
def shutdown_db_client():
    database.close_client()

@app.get('/')
async def root():
    return {'message': 'api is running'}

# Endpoint that generates the authorization url and state, redirects the user
@app.get('/spotify-login', response_class=RedirectResponse)
async def root() -> RedirectResponse:
    # random state to check if callback request is legitimate, and for identifying user in future callbacks
    state = secrets.token_urlsafe(16)
    app.states.add(state)
    authorizeLink = spotify.getAuthLink(state)
    return RedirectResponse(url=authorizeLink)

# Endpoint for the callback from the spotify login, stores tokens, starts session, and redirects to dashboard when successful.
# code is the key to get users auth tokens, if it fails you get error instead. Generates users session id cookie and removes state.
@app.get('/callback', response_class=RedirectResponse)
async def root(state: str, background_tasks: BackgroundTasks, code: str | None = None, error: str | None = None):
    if (state not in app.states):  # Check if request is from spotify
        response = RedirectResponse('http://localhost:3000/?error=state_mismatch', status_code=303)
    elif (error is not None): # Check if theres an error from spotify
        response = RedirectResponse(f"http://localhost:3000/?error=spotify_{error}", status_code=303)
    else:
        try:
            # get tokens from spotify
            headers, payload = spotify.accessTokenRequestInfo(code)
            access_token_request = requests.post(url='https://accounts.spotify.com/api/token', data=payload, headers=headers)

            # upon token success, start session and store tokens
            if (access_token_request.status_code == 200):
                access_tokens = access_token_request.json()
                session_id = secrets.token_urlsafe(16)
                # start session and initialize background tasks
                createdSession = app.sessions.startSession(session_id, access_tokens['access_token'], access_tokens['refresh_token'], background_tasks)
                # redirect to dash and give user the session id if created successfully
                if (createdSession):
                    response = RedirectResponse('http://localhost:3000/dashboard', status_code=303)
                    response.set_cookie(key='session_id', value=session_id)
                else:
                    response = RedirectResponse('http://localhost:3000/?error=session_creation_error', status_code=303)
            else:
                # redirect users to error links for errors
                response = RedirectResponse('http://localhost:3000/?error=invalid_token', status_code=303)
        except requests.exceptions.RequestException:
            response = RedirectResponse('http://localhost:3000/?error=spotify_accounts_error', status_code=303)
    
    # remove state and return final response
    app.states.discard(state)
    return response

@app.get('/test-mongodb')
async def test_mongodb():
    response: models.TestData = database.test_mongodb()
    return response

# This is the main websocket endpoint, the user provides their session id and connects to the backend if its found
@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    # open connection, load session id, check session manager for valid session, and accept or deny connection
    await websocket.accept()
    session_id = websocket.cookies['session_id']
    if (app.sessions.linkSession(session_id, websocket)):
        # session linked, accept connection, send over initial info
        await websocket.send_json({'type': 'log-status', 'loggedIn': True})
        await websocket.send_json(spotify.getUserInfo(app.sessions.getAccessToken(session_id)))
        await websocket.send_json({'type': 'spotify-token', 'token': app.sessions.getAccessToken(session_id)})
        try: # Try until disconnection
            # wait for users message until session is invalid
            while app.sessions.validSession(session_id):
                data = await websocket.receive_json() # Get message

                response = sessions.handleMessage(data, session_id, app.sessions)
                if (response):
                    await websocket.send_json(response)
                
            # set user as logged out after the session closes
            await websocket.send_json({'type': 'log-status', 'loggedIn': False})
            await websocket.send_json({'type': 'message', 'message': 'Logged Out'})
        except WebSocketDisconnect: # user disconnect
            app.sessions.disconnectSession(session_id)
    else:
        # session not valid, confirm the user status and deny connection
        await websocket.send_json({'type': 'log-status', 'loggedIn': False})
        await websocket.send_json({'type': 'message', 'message': 'Unable to link to a session'})
