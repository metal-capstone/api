from models import WebSocketMessage, MessageTypes, CommandDetail
from sessions import SessionManager
from dataHandler import recommendSongs

import database
import spotify

import weighting

import httpx
import traceback

# Message handler, get message and session info, sends response if needed. Processes commands before sending to chatbot.
# Handle message level errors here.
async def handleMessage(requestMessage: WebSocketMessage, sessionID: str, sessions: SessionManager):
    webSocket = sessions.getWebSocket(sessionID)
    try:
        # If the message is a command, handle it and break from function
        if (requestMessage['type'] != MessageTypes.MESSAGE):
            response = handleCommand(requestMessage['detail'], sessionID, sessions)
            if (response):
                await webSocket.send_json(response)
            return None
    
        # send to chatbot
        headers, data = {'Content-Type': 'text/plain'}, {'message': requestMessage['detail'], 'sender': sessionID}
        chatbotResponse = httpx.post(url='http://setup-rasa-1:5005/webhooks/rest/webhook', json=data, headers=headers).json()

        # error and break from function if empty response
        if (not chatbotResponse):
            await webSocket.send_json(WebSocketMessage(type=MessageTypes.ERROR, detail='Chatbot sent empty message.'))
            return None

        # handle chatbot response, should always have a response
        response = handleAction(chatbotResponse[0]['text'], sessionID, sessions)
        await webSocket.send_json(response)
        
    # Handles message level errors
    except Exception as e:
        traceback.print_exc()
        await webSocket.send_json(WebSocketMessage(type=MessageTypes.ERROR, detail=f"Failed to process message ({requestMessage}). Error: ({e})"))
        
# Action handler, perform certain actions based on chatbot response, always returns a response
def handleAction(text: str, session_id: str, sessions: SessionManager) -> WebSocketMessage:
    match text:
        case 'Start Music Action':
            songs = recommendSongs(sessions.getUserID(session_id), sessions.getAccessToken(session_id), 10)
            songURIs = [song['uri'] for song in songs]
            songNames = [song['name'] for song in songs]
            spotify.playSong(sessions.getAccessToken(session_id), songURIs)
            return WebSocketMessage(type=MessageTypes.MESSAGE, detail=songNames)

        case 'Make A Playlist':
            userID = sessions.getUserID(session_id)
            messageText = weighting.weightSongs(userID, sessions.getAccessToken(session_id))['txt']
            return WebSocketMessage(type=MessageTypes.MESSAGE, detail=messageText)

        # no action for text, send plain chatbot message
        case _:
            return WebSocketMessage(type=MessageTypes.MESSAGE, detail=text)

# Command Handler, performs direct actions from user, returns response if needed
# Commands: !session {param}, !user {param}
# Params: empty: echo id, delete: clear db item and log out, token: (user only) clears access token and gets another
def handleCommand(data: CommandDetail, session_id: str, sessions: SessionManager) -> WebSocketMessage | None:
    match data['command']:
        case 'logout':
            # invalidate session, remove from db
            database.clearSession(session_id)
            sessions.disconnectSession(session_id)
            return None
    
        case '!session':
            if (not data['params']): # no params
                return WebSocketMessage(type=MessageTypes.INFO, detail=f"Session ID: {session_id}")
            elif (data['params'][0] == 'delete'):
                database.clearSession(session_id)
                sessions.disconnectSession(session_id)
                return WebSocketMessage(type=MessageTypes.INFO, detail=f"Session ({session_id}) successfully cleared from db. Logging out")
            else:
                return WebSocketMessage(type=MessageTypes.ERROR, detail=f"Error: Unknown session command ({data['message'][0]})")

        case '!user': # dev commands, need a way to check if user can call these
            user_id = sessions.getUserID(session_id)
            if (not data['params']): # no params
                return WebSocketMessage(type=MessageTypes.INFO, detail=f"User ID: {user_id}")
            elif (data['params'][0] == 'token'):
                # update users access token, without sending new token to client
                refresh_token = database.getRefreshToken(user_id)
                access_token = spotify.getAccessToken(refresh_token)
                sessions.updateAccessToken(session_id, access_token)
                return WebSocketMessage(type=MessageTypes.INFO, detail=f"User ID: {user_id}: access_token updated.")
            elif (data['params'][0] == 'delete'):
                database.clearUser(user_id)
                database.clearUserSpotifyData(user_id)
                sessions.disconnectSession(session_id)
                return WebSocketMessage(type=MessageTypes.INFO, detail=f"User ({user_id}) successfully cleared from db. Logging out")
            else:
                return WebSocketMessage(type=MessageTypes.ERROR, detail=f"Error: Unknown user command ({data['message'][0]})")

        case _: # unsupported message type
            return WebSocketMessage(type=MessageTypes.ERROR, detail=f"Error processing message, unsupported message type. ({data['type']})")