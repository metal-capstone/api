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
    }
}

# user data collection method that is called in the background when a new user is made.
# Chooses multiple algorithms to decide what data to collect. Data collection errors are handled here
async def initializeUserData(userID: str, accessToken: str):
    completed: dict[str, bool] = {}
    try:
        if (algorithms['topItems']['active']):
            topItemsAlgo = algorithms['topItems']
            completed[topItemsAlgo['name']] = False
            database.createUserSpotifyData(userID, topItemsAlgo['name'], topItemsAlgo['desc'])
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

# method that is called when we want to recommend songs to the user, chooses a algorithm to pick out songs
def recommendSongs(userID: str, accessToken: str, numSongs: int) -> list[dict[str, any]] | None:
    if (algorithms['topItems']['active']):
        topItemsAlgo = algorithms['topItems']
        topItems = database.getUserSpotifyData(userID, topItemsAlgo['name'])
        queries = (topItemsAlgo['maxRecQueries'] if topItemsAlgo['maxRecQueries'] < numSongs else numSongs)
        numSongsPerQuery = numSongs // queries
        step = numSongs % queries
        songURIS: list[dict] = []
        for i in range(queries):
            choice = random.choices(['topArtists', 'topTracks'])[0]
            itemURI = random.choices(topItems[choice])[0]
            itemID = itemURI.split(':')[2]
            params = {
                'limit': numSongsPerQuery + (1 if (i<step) else 0)
            }
            if (choice == 'topArtists'):
                params['seed_artists'] = itemID
            else:
                params['seed_tracks'] = itemID
            songURIS.extend(spotify.recommendSongs(accessToken, params))
        return songURIS
    return None