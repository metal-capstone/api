from fastapi import WebSocket, BackgroundTasks
import spotify
import database
import httpx
import asyncio
import random
import weighting

# Object that manages sessions, stores auth, id, and connection data, creates and updates the user in the db
class SessionManager:
    def __init__(self):
        self.active_sessions: dict[str] = {}

    # function for new session ids, checks if associated user exists and then creates/updates in the db,
    # tries to add session to active and returns true if successful, runs background tasks for data collection
    def startSession(self, session_id: str, access_token: str, refresh_token: str, background_tasks: BackgroundTasks):
        try:
            user_id, username = spotify.getSessionUserInfo(access_token)
            if (database.user_exists(user_id)):
                database.update_session(user_id, session_id)
            else:
                database.create_user(user_id, username, refresh_token, session_id)
                background_tasks.add_task(initializeUserData, user_id, access_token)
            self.active_sessions[session_id] = {'access_token': access_token, 'spotify_id': user_id}
            return True
        except Exception as e:
            print(e)
            return False

    # function for linking websockets and sessions, checks db for users last sessions, returns true if socket is linked
    def linkSession(self, session_id: str, websocket: WebSocket):
        if (session_id in self.active_sessions):
            # already active, just link websocket
            self.active_sessions[session_id]['websocket'] = websocket
            return True
        else:
            try:
                # session id not in memory, check db
                if (database.valid_session(session_id)):
                    # if valid, add to active sessions and link websocket
                    refresh_token, user_id = database.get_session_data(session_id)
                    access_token = spotify.getAccessToken(refresh_token)
                    # not active, create new entry for session
                    self.active_sessions[session_id] = {'access_token': access_token, 'spotify_id': user_id, 'websocket': websocket}
                    return True
                else:
                    # not found or crashed, end websocket connection
                    return False
            except Exception as e:
                return False
            
    def validSession(self, session_id: str):
        return session_id in self.active_sessions

    def disconnectSession(self, session_id: str):
        self.active_sessions.pop(session_id)

    def getAccessToken(self, session_id: str):
        return self.active_sessions[session_id]['access_token']
    
    def updateAccessToken(self, session_id: str, access_token: str):
        self.active_sessions[session_id]['access_token'] = access_token
    
    def getUserID(self, session_id: str):
        return self.active_sessions[session_id]['spotify_id']
    
# Message handler, get message and session info, return response if needed. Processes commands before sending to chatbot
# Commands: !session {param}, !user {param}
# Params: empty: echo id, delete: clear db item and log out
def handleMessage(data: dict[str], session_id: str, sessions: SessionManager):
    response: dict[str] = {} # final response message to be returned
    # switch for commands or chatbot message depending on message type
    match data['type']:
        case 'logout':
            # invalidate session, remove from db
            database.clear_session(session_id)
            sessions.disconnectSession(session_id)
    
        case '!session':
            if (not data['message']): # no params
                response = {'type': 'message', 'message': f"Session ID: {session_id}"}
            elif (data['message'][0] == 'delete'):
                try:
                    database.clear_session(session_id)
                    sessions.disconnectSession(session_id)
                    response = {'type': 'message', 'message': f"Session ({session_id}) successfully cleared from db. Logging out"}
                except Exception as e:
                    response = {'type': 'error', 'error': f"Error: Failed to clear Session ({session_id}) from db. ({e})"}
            else:
                response = {'type': 'error', 'error': f"Error: Unknown session command ({data['message'][0]})"}

        case '!user': # dev commands, need a way to check if user can call these
            user_id = sessions.getUserID(session_id)
            if (not data['message']): # no params
                response = {'type': 'message', 'message': f"User ID: {user_id}"}
            elif (data['message'][0] == 'token'):
                # update users access token, without sending new token to client
                try:
                    refresh_token = database.get_refresh_token(user_id)
                    access_token = spotify.getAccessToken(refresh_token)
                    sessions.updateAccessToken(session_id, access_token)
                    response = {'type': 'message', 'message': f"User ID: {user_id}: access_token updated."}
                except Exception as e:
                    response = {'type': 'error', 'error': f"User ID: {user_id}: Failed to update access_token. ({e})"}
            elif (data['message'][0] == 'delete'):
                # deletes linked user from db and ends session
                try:
                    database.clear_user(user_id)
                    database.clear_user_spotify_data(user_id)
                    sessions.disconnectSession(session_id)
                    response = {'type': 'message', 'message': f"User ({user_id}) successfully cleared from db. Logging out"}
                except Exception as e:
                    response = {'type': 'error', 'error': f"Error: Failed to clear User ({user_id}) from db. ({e})"}
            else:
                response = {'type': 'error', 'error': f"Error: Unknown user command ({data['message'][0]})"}
        
        case 'message': # send to chatbot
            try: # Try to request chatbot, will fail if it is not running
                headers, payload = {'Content-Type': 'text/plain'}, {'message': data['message'], 'sender': session_id}
                chatbot_response = httpx.post(url='http://setup-rasa-1:5005/webhooks/rest/webhook', json=payload, headers=headers)
                # Parse message if request is valid and message is not empty
                if (chatbot_response.status_code == 200 and chatbot_response.json()):
                    text_response = chatbot_response.json()[0]['text']
                    # handle chatbot response
                    response = handleAction(text_response, session_id, sessions)
                else: # empty message most likely
                    response = {'type': 'error', 'error': f"Error receiving message: {chatbot_response.status_code}"}
            except httpx.RequestError as error:
                response = {'type': 'error', 'error': f"Error sending chatbot request. ({error})"}
        
        case _: # unsupported message type
            response = {'type': 'error', 'error': f"Error processing message, unsupported message type. ({data['type']})"}
    
    return response
        
# Action handler, perform certain actions based on chatbot response
def handleAction(text: str, session_id: str, sessions: SessionManager):
    response: dict[str] = {} # final response message to be returned
    match text:
        case 'Start Music Action':
            songs = recommendSongs(sessions.getUserID(session_id), sessions.getAccessToken(session_id), 1)
            spotify.playSong(sessions.getAccessToken(session_id), list(songs.keys()))
            response = {'type': 'message', 'message': list(songs.values())}

        case 'Make A Playlist':
            userID = sessions.getUserID(session_id)
            response = {'type': 'message', 'message': weighting.weightSongs(userID, sessions.getAccessToken(session_id))['txt']}

        # no action for text, send plain chatbot message
        case _:
            response = {'type': 'message', 'message': text}

    return response

initializeTypes = {'top_items': True }

async def initializeUserData(user_id: str, access_token: str):
    try:
        if (initializeTypes['top_items']):
            database.create_spotify_data(user_id, 'Top Items')
            params = {
                'types': ['artists', 'tracks'],
                'time_ranges': ['short_term', 'medium_term', 'long_term'],
                'limit': 10
            }
            top_items = await asyncio.gather(
                *[spotify.getUserTopItemsAsync(access_token, item_type, time_range, params['limit'], 0) 
                  for item_type in params['types'] for time_range in params['time_ranges']]
            )
            top_items = [item for items in top_items for item in items]
            split = top_items.__len__() // 2
            database.add_spotify_data(user_id, 'Top Items', {'top_artists': { '$each': top_items[:(split - 1)] }, 'top_tracks': { '$each': top_items[split:] }})
        database.set_data_ready(user_id, True)
    except Exception as e:
        print(e)

def recommendSongs(user_id: str, access_token: str, num_songs: int):
    top_items = database.get_spotify_data(user_id, 'Top Items')
    choice = random.choices(['top_artists', 'top_tracks'])[0]
    songURI = random.choices(top_items[choice])[0]
    songID = songURI.split(':')[2]
    params = {
        'limit': num_songs
    }
    if (choice == 'top_artists'):
        params['seed_artists'] = songID
    else:
        params['seed_tracks'] = songID
    return spotify.recommendSongs(access_token, params)
