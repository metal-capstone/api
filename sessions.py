from fastapi import WebSocket
from models import Session, LoginMessage, SessionNotFoundMessage, BaseDataMessage, MessageTypes, WebSocketMessage
import spotify
import database
import dataHandler
import chain

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
        self.activeSessions[sessionID] = Session(accessToken=accessToken, userID=userID, webSocket=webSocket, location='N/A')
        await self.initSessionData(sessionID)
    
    # called after starting a session, send over relevant data to start a session client side
    async def initSessionData(self, sessionID: str):
        webSocket = self.getWebSocket(sessionID)
        username, profilePic = spotify.getUserInfo(self.getAccessToken(sessionID))
        username = "Demo User"
        profilePic = None
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

    async def startDemo(self, sessionID: str):
        webSocket = self.getWebSocket(sessionID)
        await webSocket.send_json({"type": MessageTypes.MESSAGE, "detail": "Hello! I am Spotify Chatbot, could you give me the names of some of the artists you listen to?"})
        requestMessage: WebSocketMessage = await webSocket.receive_json() # Get message
        while (requestMessage['type'] != MessageTypes.MESSAGE):
            requestMessage: WebSocketMessage = await webSocket.receive_json() # Get message
        artists = chain.getArtistIds(requestMessage['detail'], self.getAccessToken(sessionID))
        dataHandler.initDataDemo(self.getUserID(sessionID), artists)
        await webSocket.send_json({"type": MessageTypes.MESSAGE, "detail": "Awesome I will take note of that. What location would you like to be at? (Only Bar and Library are supported)"})
        requestMessage: WebSocketMessage = await webSocket.receive_json() # Get message
        while (requestMessage['detail'] != 'Bar' and requestMessage['detail'] != 'bar' and requestMessage['detail'] != 'Library' and requestMessage['detail'] != 'library'):
            await webSocket.send_json({"type": MessageTypes.MESSAGE, "detail": "Sorry I didn't understand that, Only Bar and Library are supported locations for the demo. Please try again."})
            requestMessage: WebSocketMessage = await webSocket.receive_json() # Get message
        self.setLocation(sessionID, requestMessage['detail'].title())
        await webSocket.send_json({"type": MessageTypes.MESSAGE, "detail": f"Okay I will act like you are at a {requestMessage['detail'].title()} for your recommendations. You can now ask me for recommendations by saying \"Play new music\" or \"Make me a playlist\", to play music from any artist, album, or song, ask \"Play music from the artist x\" or \"Play the song x by x\"."})
            
    def validSession(self, sessionID: str) -> bool:
        return sessionID in self.activeSessions

    def disconnectSession(self, sessionID: str):
        user_id = self.getUserID(sessionID)
        database.clearUser(user_id)
        database.clearUserSpotifyData(user_id)
        self.disconnectSession(sessionID)
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
    
    def setLocation(self, sessionID: str, location: str):
        self.activeSessions[sessionID]['location'] = location

    def getLocation(self, sessionID: str) -> str:
        return self.activeSessions[sessionID]['location']
