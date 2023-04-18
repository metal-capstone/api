from pydantic import BaseModel
from typing import TypedDict
from fastapi import WebSocket

class TestData(BaseModel):
    message: str

class Session(TypedDict):
    accessToken: str
    userID: str
    webSocket: WebSocket

class MessageTypes(dict):
    INFO = 0
    MESSAGE = 1
    COMMAND = 2
    DATA = 3
    ERROR = 4

class WebSocketMessage(TypedDict):
    type: int
    detail: str | dict[str, any]

class CommandDetail(TypedDict):
    command: str
    params: list[str] | None

LoginMessage = WebSocketMessage(
    type = MessageTypes.DATA,
    detail = {
        'message': 'User successfully logged in.',
        'logStatus': True
    }
)

LogOutMessage = WebSocketMessage(
    type = MessageTypes.DATA,
    detail = {
        'message': 'User successfully logged out.',
        'logStatus': False
    }
)

SessionNotFoundMessage = WebSocketMessage(
    type = MessageTypes.INFO,
    detail = 'Session was not found, user is not logged in.'
)

BaseDataMessage = WebSocketMessage(
    type = MessageTypes.DATA,
    detail = {
        'message': 'No data in message.'
    }
)