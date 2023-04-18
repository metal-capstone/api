import database
import asyncio
import spotify
import random
import traceback

initializeTypes = {'topItems': True }

# user data collection method that is called in the background when a new user is made.
# Chooses multiple algorithms to decide what data to collect. Data collection errors are handled here
async def initializeUserData(userID: str, accessToken: str):
    try:
        if (initializeTypes['topItems']):
            database.createUserSpotifyData(userID, 'Top Items')
            params = {
                'types': ['artists', 'tracks'],
                'timeRanges': ['short_term', 'medium_term', 'long_term'],
                'limit': 10
            }
            topItems = await asyncio.gather(
                *[spotify.getUserTopItemsAsync(accessToken, itemType, timeRanges, params['limit'], 0) 
                  for itemType in params['types'] for timeRanges in params['timeRanges']]
            )
            topItems = [item for items in topItems for item in items]
            split = topItems.__len__() // 2
            database.addUserSpotifyData(userID, 'Top Items', {'topArtists': { '$each': topItems[:(split - 1)] }, 'topTracks': { '$each': topItems[split:] }})
        database.setDataReady(userID, True)
    except Exception as e:
        traceback.print_exc()

# method that is called when we want to recommend songs to the user, chooses a algorithm to pick out songs
def recommendSongs(userID: str, accessToken: str, numSongs: int):
    topItems = database.getUserSpotifyData(userID, 'Top Items')
    choice = random.choices(['topArtists', 'topTracks'])[0]
    songURI = random.choices(topItems[choice])[0]
    songID = songURI.split(':')[2]
    params = {
        'limit': numSongs
    }
    if (choice == 'topArtists'):
        params['seed_artists'] = songID
    else:
        params['seed_tracks'] = songID
    return spotify.recommendSongs(accessToken, params)