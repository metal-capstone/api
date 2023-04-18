from fastapi import WebSocket
from models import Session, LoginMessage, SessionNotFoundMessage, BaseDataMessage
import spotify
import database

# Object that tracks all current sessions, stores each session in a Session object with needed data
class SessionManager:
    activeSessions: dict[str, Session]
    def __init__(self):
        self.activeSessions = {}

    # Attempt to start a session, send correct messages based on success
    async def startSession(self, sessionID: str, webSocket: WebSocket):
        # Accept and store websocket if successful
        await webSocket.accept()
        # If this is not a valid session id, break from method
        if (not database.validSession(sessionID)):
            await webSocket.send_json(SessionNotFoundMessage)
            return None
        
        # if valid, send login confirmation, add to active sessions, and link websocket
        await webSocket.send_json(LoginMessage)
        # always get a new access token upon login
        refreshToken, userID = database.getSessionData(sessionID)
        accessToken = spotify.getAccessToken(refreshToken)
        self.activeSessions[sessionID] = Session(accessToken=accessToken, userID=userID, webSocket=webSocket)
        await self.initSessionData(sessionID)
    
    # called after starting a session, send over relevant data to start a session client side
    async def initSessionData(self, sessionID: str):
        webSocket = self.getWebSocket(sessionID)
        username, profilePic = spotify.getUserInfo(self.getAccessToken(sessionID))
        accessToken = self.getAccessToken(sessionID)
        initDataMessage = BaseDataMessage
        if (profilePic):
            initDataMessage['detail'] = {
                'message': 'Initial session data (username, profile pic, token).',
                'username': username,
                'profilePic': profilePic,
                'token': accessToken
            }
        else:
            initDataMessage['detail'] = {
                'message': 'Initial session data, no profile pic (username, token).',
                'username': username,
                'token': accessToken
            }
        await webSocket.send_json(initDataMessage)
            
    def validSession(self, sessionID: str) -> bool:
        return sessionID in self.activeSessions

    def disconnectSession(self, sessionID: str):
        if (self.validSession(sessionID)):
            self.activeSessions.pop(sessionID)

    def getAccessToken(self, sessionID: str) -> str:
        return self.activeSessions[sessionID]['accessToken']
    
    def updateAccessToken(self, sessionID: str, access_token: str):
        self.activeSessions[sessionID]['accessToken'] = access_token
    
    def getUserID(self, sessionID: str) -> str:
        return self.activeSessions[sessionID]['userID']
    
    def getWebSocket(self, sessionID: str) -> WebSocket:
        return self.activeSessions[sessionID]['webSocket']
