

# Action handler, perform certain actions based on chatbot response, always returns a response
def handleAction(text: str, session_id: str, sessions: SessionManager) -> WebSocketMessage:
    match text:
        case 'Start Music Action':
            location = sessions.getLocation(session_id)
            songs = recommendSongs(sessions.getUserID(session_id), sessions.getAccessToken(session_id), location, 5)
            songURIs = [song['uri'] for song in songs]
            songNames = [song['name'] for song in songs]
            spotify.playSong(sessions.getAccessToken(session_id), songURIs)
            return WebSocketMessage(type=MessageTypes.MESSAGE, detail=f"Playing Songs based off of your location ({location}) and listening history. Queued 5")

        case 'Make A Playlist':
            location = sessions.getLocation(session_id)
            userID = sessions.getUserID(session_id)
            messageText = weighting.weightSongs(userID, sessions.getAccessToken(session_id), location)['txt']
            return WebSocketMessage(type=MessageTypes.MESSAGE, detail=messageText)

        # no action for text, send plain chatbot message
        case _:
            return WebSocketMessage(type=MessageTypes.MESSAGE, detail=text)