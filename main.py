from fastapi import BackgroundTasks, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from models import TestData, WebSocketMessage, LogOutMessage
from sessions import SessionManager
from messageHandler import handleMessage
from dataHandler import initializeUserData

import secrets
import traceback

import database
import spotify
import util

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

# app.add_middleware(
#     util.DelayMiddleware,
#     delayMin=3,
#     delayRange=2
# )

states = set()  # set for all active states, stored only temporarily until spotify callback
sessions = SessionManager()

@app.on_event('startup')
def startupDBClient():
    database.testMongodb()

@app.on_event('shutdown')
def shutdownDBClient():
    database.closeClient()

@app.get('/')
async def root():
    return {'message': 'api is running'}

# Endpoint that generates the authorization url and state, redirects the user
@app.get('/spotify-login')
async def root(request: Request) -> RedirectResponse:
    try:
        # random state to check if callback request is legitimate upon return
        state = secrets.token_urlsafe(16)
        states.add(state)
        authorizeLink = spotify.generateAuthLink(state, (False)) #'sessionID' not in request.cookies
        return RedirectResponse(url=authorizeLink)
    except Exception as e:
        return RedirectResponse(f"http://localhost:3000/?error={e}", status_code=303)

# Endpoint for the callback from the spotify login, stores tokens, starts session, and redirects to dashboard when successful.
# code is the key to get users auth tokens, if it fails you get error instead. Generates users session id cookie and removes state.
@app.get('/callback')
async def root(state: str, backgroundTasks: BackgroundTasks, code: str | None = None, error: str | None = None) -> RedirectResponse:
    # Guard checks for any spotify errors or unknown callbacks, sends them back to login
    if (error):
        return RedirectResponse(f"http://localhost:3000/?error=spotify_{error}", status_code=303)
    if (state not in states):
        return RedirectResponse('http://localhost:3000/?error=state_mismatch', status_code=303)
    
    try:
        # Callback successful, delete state and get access tokens and user info
        states.discard(state)
        accessToken, refreshToken = spotify.getAuthTokens(code)
        userID, username = spotify.getSessionUserInfo(accessToken)
        # Generate a new session id to be used to identify browser in the future
        sessionID = secrets.token_urlsafe(16)
        # check db for user and create them if needed, init user data also
        if (database.userExists(userID)):
            database.updateSession(userID, sessionID)
        else:
            database.createUser(userID, username, refreshToken, sessionID)
            #backgroundTasks.add_task(initializeUserData, userID, accessToken)
        
        # finally redirect user back to dashboard with session id as cookie
        response = RedirectResponse('http://localhost:3000/dashboard', status_code=303)
        response.set_cookie(key='sessionID', value=sessionID)
        return response
    
    except Exception as e:
        return RedirectResponse(f"http://localhost:3000/?error={e}", status_code=303)

@app.get('/test-mongodb')
async def test_mongodb():
    response: TestData = database.testMongodb()
    return response

# Websocket endpoint that is the main communication between client and api, grabs session id from cookies and logs user in.
# Handle session level errors here.
@app.websocket('/ws')
async def websocket_endpoint(webSocket: WebSocket):
    try:
        sessionID = webSocket.cookies['sessionID']
        # Attempt to start session with session manager
        await sessions.startSession(sessionID, webSocket)
        await sessions.startDemo(sessionID)
        # Constant check to only accept messages if session is valid. Wont enter if session never started
        while sessions.validSession(sessionID):
            requestMessage: WebSocketMessage = await webSocket.receive_json() # Get message

            # handle message commands and actions
            await handleMessage(requestMessage, sessionID, sessions)

        await webSocket.send_json(LogOutMessage)

    except WebSocketDisconnect: # user disconnect
        sessions.disconnectSession(sessionID)
    except Exception as e: # handle all other errors
        traceback.print_exc()
        sessions.disconnectSession(sessionID)
