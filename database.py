from pymongo import MongoClient
import json
import models

credentials = json.load(open('credentials.json'))
MONGODB_DATABASE_URL = credentials['mongodb-database-url']
MONGODB_CLIENT = MongoClient(MONGODB_DATABASE_URL)
TEST_CLUSTER = MONGODB_CLIENT['test-database']
USER_DATA_CLUSTER = MONGODB_CLIENT['UserData']
PLACES_CLUSTER = MONGODB_CLIENT['PlaceClusters']
SPOTIFY_DATA_CLUSTER = MONGODB_CLIENT['SpotifyData']
SONG_COLLECTION_CLUSTER = MONGODB_CLIENT['UsersSpotifyData']
del credentials

def closeClient():
    MONGODB_CLIENT.close()

def testMongodb() -> models.TestData:
    response = TEST_CLUSTER['test-collection'].find_one({'message': 'MongoDB connection is working'})
    testData: models.TestData = models.TestData(**response)
    return testData

def createUser(userID: str, username: str, refreshToken: str, sessionID: str):
    newUser = {
        '_id': userID,
        'username': username,
        'refreshToken': refreshToken,
        'sessionID': sessionID,
        'dataReady': False
    }

    USER_DATA_CLUSTER['Users'].insert_one(newUser)

def userExists(userID: str) -> bool:
    numUsers = USER_DATA_CLUSTER['Users'].count_documents({'_id': userID}, limit = 1)
    return numUsers != 0

def clearUser(userID: str):
    USER_DATA_CLUSTER['Users'].delete_one({'_id': userID})

def validSession(sessionID: str) -> bool:
    numUsers = USER_DATA_CLUSTER['Users'].count_documents({'sessionID': sessionID}, limit = 1)
    return numUsers != 0
    
def getSessionData(sessionID: str) -> tuple[str, str]:
    user = USER_DATA_CLUSTER['Users'].find_one({'sessionID': sessionID})
    return user['refreshToken'], user['_id']

def updateSession(userID: str, sessionID: str):
    USER_DATA_CLUSTER['Users'].update_one({'_id': userID}, { '$set': { 'sessionID': sessionID } })

def clearSession(sessionID: str):
    USER_DATA_CLUSTER['Users'].update_one({'sessionID': sessionID}, { '$unset': { 'sessionID': 1 } })

def getRefreshToken(userID: str) -> str:
    user = USER_DATA_CLUSTER['Users'].find_one({'_id': userID})
    return user['refreshToken']

def getDataReady(userID: str) -> bool:
    user = USER_DATA_CLUSTER['Users'].find_one({'_id': userID})
    return user['dataReady']

def setDataReady(userID: str, ready: bool):
    USER_DATA_CLUSTER['Users'].update_one({'_id': userID}, { '$set': { 'dataReady': ready } })

def createUserSpotifyData(userID: str, dataName: str):
    newSpotifyData = {
        'userID': userID,
        'name': dataName
    }

    USER_DATA_CLUSTER['SpotifyData'].insert_one(newSpotifyData)

def clearUserSpotifyData(userID: str):
    USER_DATA_CLUSTER['SpotifyData'].delete_many({'userID': userID})

def addUserSpotifyData(userID: str, dataName: str, data: dict[str, any]):
    USER_DATA_CLUSTER['SpotifyData'].update_one({'userID': userID, 'name': dataName}, {'$push': data})

def getUserSpotifyData(userID: str, dataName: str) -> dict[str, any]:
    userSpotifyData = USER_DATA_CLUSTER['SpotifyData'].find_one({'userID': userID, 'name': dataName})
    return userSpotifyData

def getPlaceData(placeType: str) -> dict[str, any]:
    placeValues = PLACES_CLUSTER['PlaceType'].find_one({'Place': placeType})
    return placeValues

def getUserSongs(songQuery):
    userFav = SONG_COLLECTION_CLUSTER['FavSongs']
    userRel = SONG_COLLECTION_CLUSTER['RelatedSongs']
    relSongs = list(userRel.find(songQuery).limit(30))
    favSongs = list(userFav.find(songQuery).limit(75-len(relSongs)))
    return favSongs, relSongs

# Only add track if it doesn't exists
def addTrack(trackData):
    if (SPOTIFY_DATA_CLUSTER['Tracks'].count_documents({'_id': trackData['_id']}, limit=1) == 0):
        SPOTIFY_DATA_CLUSTER['Tracks'].insert(trackData)

def getTrackData(trackID: str) -> dict[str, any]:
    trackData = SPOTIFY_DATA_CLUSTER['Tracks'].find_one({'_id': trackID})
    return trackData