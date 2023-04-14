import location
import database
import spotify

def weightSongs(userID, token):

    placeType = location.getPlace()

    placeValues = database.get_place_data(placeType)

    lim = 75

    songQuery = {"danceability": {
        "$gte": (placeValues["danceability"]-0.1), "$lte": (placeValues["danceability"]+.1)}, "energy": {
        "$gte": (placeValues["energy"]-0.1), "$lte": (placeValues["energy"]+.1)}, "valence": {
        "$gte": (placeValues["valence"]-0.1), "$lte": (placeValues["valence"]+.1)}}

    favSongs, relSongs = database.get_user_songs(songQuery)

    lim = 75 - len(relSongs) - len(favSongs)

    user_params = {
        "limit": lim,
        "seed_artists": "",
        "seed_tracks": "",
        "seed_genres": "hip-hop,pop,house,chill,alternative",
        "min_danceability": placeValues["danceability"]-.2,
        "target_danceability": placeValues["danceability"],
        "min_energy": placeValues["energy"]-.2,
        "target_energy": placeValues["energy"],
        "min_valence": placeValues["valence"]-.2,
        "max_danceability": placeValues["danceability"]+.2,
        "max_energy": placeValues["energy"]+.2,
        "max_valence": placeValues["valence"]+.2,
        "target_valence": placeValues["valence"],
    }

    reqSongs = {}
    if (lim > 0):
        reqSongs = spotify.recommendSongs(token, user_params)

    data = {
        'name': placeType,
        'description': "Playlist for " + placeType.capitalize(),
        'public': True
    }

    userID = userID.split(':')[2]

    playlist = spotify.createPlaylist(token, userID, data)

    playIds = []
    for doc in favSongs:
        playIds.append("spotify:track:" + str(doc['_id']))

    for doc in relSongs:
        playIds.append("spotify:track:" + str(doc['_id']))

    for doc in reqSongs:
        playIds.append("spotify:track:" + str(doc['id']))

    uris = {"uris": playIds, "position": 0}

    playlistID = playlist['id']

    playlistURI = playlist['uri']

    spotify.addToPlaylist(token, playlistID, uris)

    spotify.playContext(token, playlistURI)

    return {'txt': str("Playlist Created for " + placeType.capitalize())}
