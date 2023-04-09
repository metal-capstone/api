from fastapi.responses import JSONResponse
import sessions
import database
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# https://stackoverflow.com/a/73659723
class ASGIMiddleware:
    def __init__(self, app, sessions: sessions.SessionManager):
        self.app = app
        self.sessions = sessions

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (scope['type'] == 'websocket'):
            cookies = scope['headers'][10][1].decode('ascii').split('; ')
            session = [not cookie.startswith('session_id') or cookie for cookie in cookies]
            if (session[0]):
                session_id = session[1].split('=')[1]
                if (self.sessions.validSession(session_id) or database.valid_session(session_id)):
                    return await self.app(scope, receive, send)
                return JSONResponse(content={"message": "session not found"}, status_code=404)
        return await self.app(scope, receive, send)