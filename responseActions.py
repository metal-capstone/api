# Just coppied imports from main some may be able to be removed
from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

import string
import random
import requests

import database
import models
import spotify

from songCollection import *
from location import *