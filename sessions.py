from fastapi import WebSocket
import spotify
import database

class SessionManager:
    def __init__(self):
        self.active_sessions: dict[str] = {}

    def startSession(self, session_id, access_token, refresh_token, background_tasks):
        try:
            user_id, username = spotify.getSessionUserInfo(access_token)
            if (database.user_exists(user_id)):
                database.update_session(user_id, session_id)
            else:
                database.create_user(user_id, username, refresh_token, session_id)
            self.active_sessions[session_id] = {'access_token': access_token, 'spotify_id': user_id}
        except Exception as e:
            print(e)

    def linkSession(self, session_id: str, websocket: WebSocket):
        if (session_id in self.active_sessions):
            self.active_sessions[session_id]['websocket'] = websocket
            return True
        else:
            try:
                if (database.valid_session(session_id)):
                    refresh_token, user_id = database.get_resume_session_data(session_id)
                    access_token = spotify.getAccessToken(refresh_token)
                    self.active_sessions[session_id] = {'access_token': access_token, 'spotify_id': user_id, 'websocket': websocket}
                    return True
                else:
                    print('Error resuming session')
                    return False
            except Exception as e:
                print(e)
                return False
            
    def validSession(self, session_id: str):
        return session_id in self.active_sessions

    def disconnectSession(self, session_id: str):
        self.active_sessions.pop(session_id)

    def getAccessToken(self, session_id: str):
        return self.active_sessions[session_id]['access_token']

    