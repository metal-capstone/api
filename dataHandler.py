import database
import spotify
import random
import traceback
import asyncio

algorithms = {
    'topItems': {
        'name': 'Top Items',
        'desc': 'Stores the users top artists and tracks, generates recommendations using them with the Spotify API Recommendations',
        'active': True,
        'types': ['artists', 'tracks'],
        'timeRanges': ['short_term', 'medium_term', 'long_term'],
        'itemsLimit': 10,
        'maxRecQueries': 10
    },
    'songCollection': {
        'name': 'Song Collection',
        'desc': 'Collects songs that the user listens to and related songs, picks these songs for recommendations based on audio features',
        'active': True
    }
}

# user data collection method that is called in the background when a new user is made.
# Chooses multiple algorithms to decide what data to collect. Data collection errors are handled here
async def initializeUserData(userID: str, accessToken: str):
    completed: dict[str, bool] = {}
    try:
        if (algorithms['topItems']['active']):
            topItemsAlgo = algorithms['topItems']
            database.createUserSpotifyData(userID, topItemsAlgo['name'], topItemsAlgo['desc'])
            completed[topItemsAlgo['name']] = False
            topItems = await asyncio.gather(
                *[spotify.getUserTopItemsAsync(accessToken, itemType, timeRanges, topItemsAlgo['itemsLimit'], 0) 
                  for itemType in topItemsAlgo['types'] for timeRanges in topItemsAlgo['timeRanges']]
            )
            topItems = [item for items in topItems for item in items]
            split = topItems.__len__() // 2
            database.addUserSpotifyData(userID, topItemsAlgo['name'], {'topArtists': { '$each': topItems[:(split - 1)] }, 'topTracks': { '$each': topItems[split:] }})
            database.setDataStatus(userID, topItemsAlgo['name'], 'ready')
            completed[topItemsAlgo['name']] = True
    except Exception as e:
        traceback.print_exc()
        for algoName in completed:
            if (not completed[algoName]):
                database.setDataStatus(userID, algoName, 'failed', str(e))

def initDataDemo(userID: str, artists):
    database.createUserSpotifyData(userID, 'Top Items', 'Data for the poster pres demo')
    database.addUserSpotifyData(userID, 'Top Items', {'topArtists':  artists })
    database.setDataStatus(userID, 'Top Items', 'ready')


# method that is called when we want to recommend songs to the user, chooses a algorithm to pick out songs
def recommendSongs(userID: str, accessToken: str, location: str, numSongs: int) -> list[dict[str, any]] | None:
    if (algorithms['topItems']['active']):
        topItemsAlgo = algorithms['topItems']
        topItems = database.getUserSpotifyData(userID, topItemsAlgo['name'])
        queries = (topItemsAlgo['maxRecQueries'] if topItemsAlgo['maxRecQueries'] < numSongs else numSongs)
        numSongsPerQuery = numSongs // queries
        step = numSongs % queries
        songURIS: list[dict] = []
        if (location == 'Bar'):
            params = {
                'target_danceability': 0.7,
                'target_energy': 0.7,
                'seed_genres': 'Pop,Hip-Hop',
                'min_popularity': 50
            }
        elif (location == 'Library'):
            params = {
                'target_instrumentalness': 0.9,
                'target_danceability': 0.1,
                'max_loudness': -10.0,
                'seed_genres': 'Lo-Fi,Classical Piano',
                'min_popularity': 10
            }
        else:
            params = {}
        for i in range(queries):
            choice = 'topArtists'#random.choices(['topArtists', 'topTracks'])[0]
            itemURI = random.choices(topItems[choice])[0]
            itemID = itemURI.split(':')[2]
            params['limit'] =  numSongsPerQuery + (1 if (i<step) else 0)
            if (choice == 'topArtists'):
                params['seed_artists'] = itemID
            else:
                params['seed_tracks'] = itemID
            songURIS.extend(spotify.recommendSongs(accessToken, params))
        return songURIS
    return None