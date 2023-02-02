from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import string
import random
import json
import requests

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

creds = json.load(open('credentials.json')) # load in creds from json file

app.scope = "user-read-private user-read-email user-top-read"
app.state = '' # TODO update api to work with multiple users, this should be per user not global. Still could work with multiple user might be issues if multiple are signing in at the same time

@app.get("/")
async def root():
    return {"message": "api is running"}

@app.get("/spotify-login")
async def root():
    app.state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    authorizeLink = 'https://accounts.spotify.com/authorize?response_type=code&client_id=' + creds['spotify_client_id'] + '&scope=' + app.scope + '&redirect_uri=http://localhost:8000/callback&state=' + app.state
    return RedirectResponse(authorizeLink, status_code=303)

@app.get("/callback")
async def root(code: str, state: str):
    if (state != app.state):
        return {"message": "state_mismatch"}
    else:
        app.state = ""
