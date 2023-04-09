from fastapi import WebSocket
import spotify
import database
import requests

# Object that manages sessions, stores auth, id, and connection data, creates and updates the user in the db
class SessionManager:
    def __init__(self):
        self.active_sessions: dict[str] = {}

    # function for new session ids, checks if associated user exists and then creates/updates in the db,
    # tries to add session to active and returns true if successful, runs background tasks for data collection
    def startSession(self, session_id, access_token, refresh_token, background_tasks):
        try:
            user_id, username = spotify.getSessionUserInfo(access_token)
            if (database.user_exists(user_id)):
                database.update_session(user_id, session_id)
            else:
                database.create_user(user_id, username, refresh_token, session_id)
            self.active_sessions[session_id] = {'access_token': access_token, 'spotify_id': user_id}
            return True
        except Exception as e:
            print(e)
            return False

    # function for linking websockets and sessions, checks db for users last sessions, returns true if socket is linked
    def linkSession(self, session_id: str, websocket: WebSocket):
        if (session_id in self.active_sessions):
            self.active_sessions[session_id]['websocket'] = websocket
            return True
        else:
            try:
                # session id not in memory, check db
                if (database.valid_session(session_id)):
                    # if valid, add to active sessions and link websocket
                    refresh_token, user_id = database.get_session_data(session_id)
                    access_token = spotify.getAccessToken(refresh_token)
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
    
    def getUserID(self, session_id: str):
        return self.active_sessions[session_id]['spotify_id']
    
# Message handler, get message and session info, return response if needed. Processes commands before sending to chatbot
# Commands: !session {param}, !user {param}
# Params: empty: echo id, delete: clear db item and log out
def handleMessage(data: dict[str], session_id: str, sessions: SessionManager):
    response: dict[str] = {} # final response message to be returned
    # switch commands or chatbot message depending on message type
    match data['type']:
        case 'logout':
            # invalidate session, remove from db
            database.clear_session(session_id)
            sessions.disconnectSession(session_id)
    
        case '!session':
            if (not data['message']):
                response = {'type': 'message', 'message': f"Session ID: {session_id}"}
            elif (data['message'][0] == 'delete'):
                try:
                    database.clear_session(session_id)
                    sessions.disconnectSession(session_id)
                    response = {'type': 'message', 'message': f"Session ({session_id}) successfully cleared from db. Logging out"}
                except Exception as e:
                    response = {'type': 'error', 'error': f"Error: Failed to clear Session ({session_id}) from db. ({e})"}

        case '!user': # dev commands, need a way to check if user can call these
            user_id = sessions.getUserID(session_id)
            if (not data['message']):
                response = {'type': 'message', 'message': f"User ID: {user_id}"}
            elif (data['message'][0] == 'delete'):
                # deletes linked user from db and ends session
                try:
                    database.clear_user(user_id)
                    sessions.disconnectSession(session_id)
                    response = {'type': 'message', 'message': f"User ({user_id}) successfully cleared from db. Logging out"}
                except Exception as e:
                    response = {'type': 'error', 'error': f"Error: Failed to clear User ({user_id}) from db. ({e})"}
            else:
                response = {'type': 'error', 'error': f"Error: Unknown user command ({data['message'][0]})"}
        
        case 'message': # send to chatbot
            try: # Try to request chatbot, will fail if it is not running
                headers, payload = {'Content-Type': 'text/plain'}, {'message': data['message'], 'sender': session_id}
                chatbot_response = requests.post(url='http://setup-rasa-1:5005/webhooks/rest/webhook', json=payload, headers=headers)
                # Parse message if request is valid and message is not empty
                if (chatbot_response.status_code == 200 and chatbot_response.json()):
                    text_response = chatbot_response.json()[0]['text']
                    # handle chatbot response
                    response = handleAction(text_response, session_id, sessions)
                else: # empty message most likely
                    response = {'type': 'error', 'error': f"Error receiving message: {chatbot_response.status_code}"}
            except requests.exceptions.RequestException as error:
                response = {'type': 'error', 'error': f"Error sending chatbot request. ({error})"}
        
        case _: # unsupported message type
            response = {'type': 'error', 'error': f"Error processing message, unsupported message type. ({data['type']})"}
    
    return response
        
# Action handler, perform certain actions based on chatbot response
def handleAction(text: str, session_id: str, sessions: SessionManager):
    response: dict[str] = {} # final response message to be returned
    match text:
        case 'Start Music Action':
            response = spotify.getRecSong(sessions.getAccessToken(session_id))

        # no action for text, send plain chatbot message
        case _:
            response = {'type': 'message', 'message': text}

    return response

    