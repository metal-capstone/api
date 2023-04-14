import httpx
import json

def getUsersArtists(user_headers):
    users_top_artists = {}
    users_top_related_artists = {}
    prefixLength = len('spotify:artist:')

    #get the users top 30 artists
    time_range = ["short_term", "medium_term", "long_term"]
    for t in time_range:
        user_params = {
            "limit": 10,
            "time_range": t
        }
        json_response = httpx.get("https://api.spotify.com/v1/me/top/artists", params=user_params, headers=user_headers).json()
        top_artists_data = json_response['items']
        for data in top_artists_data:
            uri = data['uri'][prefixLength:]
            name = data['name']
            if uri not in users_top_artists:
                users_top_artists[uri] = name
    
    #Get the artists that the user follows (max of 30)
    user_params = {
        "type": 'artist',
        "limit": 30
    }
    json_response = httpx.get("https://api.spotify.com/v1/me/following", params=user_params, headers=user_headers).json()
    
    top_artists_data = json_response['artists']['items']
    for data in top_artists_data:
        uri = data['uri'][prefixLength:]
        name = data['name']
        if uri not in users_top_artists:
            users_top_artists[uri] = name

    #Get 2 artists related to each of the users top 10 artists
    n = 10
    for idx, (uri, name) in enumerate(users_top_artists.items()):
        if idx == n: break
        user_params = {
            "id": uri
        }
        json_response = httpx.get("https://api.spotify.com/v1/artists/"+uri+"/related-artists", params=user_params, headers=user_headers).json()

        count = 0
        top_related_artists_data = json_response['artists']
        for data in top_related_artists_data:
            uri = data['uri'][prefixLength:]
            name = data['name']
            #popularity = data['popularity']
            if uri not in users_top_related_artists:
                users_top_related_artists[uri] = name
                count += 1
            if count == 2:
                break
                
    return users_top_artists, users_top_related_artists
    

def getUsersSongs(user_headers, users_top_artists, users_top_related_artists):
    users_saved_songs = {}
    users_artists_top_songs = {}
    users_related_artists_top_songs = {}
    prefixLength = len('spotify:track:')

    #Get all the songs the user saved
    json_response = httpx.get("https://api.spotify.com/v1/me/tracks", headers=user_headers).json()
    total = json_response['total']
    limit = 50
    offset = 0

    while offset < total:
        user_params = {
            "limit": limit,
            "offset": offset
        }
        json_response = httpx.get("https://api.spotify.com/v1/me/tracks", params=user_params, headers=user_headers).json()
        
        saved_songs_data = json_response['items']
        for data in saved_songs_data:
            uri = data['track']['uri'][prefixLength:]
            name = data['track']['name']
            if uri not in users_saved_songs:
                users_saved_songs[uri] = name

        offset += limit

    #Get the top 10 songs of each artist in users_top_artists list
    for id in users_top_artists.keys():
        user_params = {
            "id": id,
            "market": "US"
        }
        json_response = httpx.get("https://api.spotify.com/v1/artists/"+id+"/top-tracks", params=user_params, headers=user_headers).json()
        top_songs_artists_data = json_response['tracks']
        count = 0

        for data in top_songs_artists_data:
            if count < 10:
                uri = data['uri'][prefixLength:]
                name = data['name']
                if uri not in users_saved_songs:
                    users_artists_top_songs[uri] = name
                count+=1
            else:
                break

    #Get the top 10 songs of each artist in users_top_related_artists list
    for id in users_top_related_artists.keys():
        user_params = {
            "id": id,
            "market": "US"
        }
        json_response = httpx.get("https://api.spotify.com/v1/artists/"+id+"/top-tracks", params=user_params, headers=user_headers).json()
        
        top_songs_related_artists_data = json_response['tracks']
        count = 0
        for data in top_songs_related_artists_data:
            if count < 10:
                uri = data['uri'][prefixLength:]
                name = data['name']
                if uri not in users_saved_songs:
                    users_related_artists_top_songs[uri] = name
                count+=1
            else:
                break

    return users_saved_songs, users_artists_top_songs, users_related_artists_top_songs

#takes 23 seconds uptill this point
            
def getAudioFeatures(user_headers, users_related_artists_top_songs):
    prefixLength = len('spotify:track:')
    songs_list = list(users_related_artists_top_songs)
    total = len(songs_list)
    start = 0
    end = 100
    count = 0
    while start < total:
        songs_sublist = songs_list[start:end]
        songs_str = ",".join(songs_sublist)
        user_params = {
            "ids": songs_str
            }
        json_response = httpx.get("https://api.spotify.com/v1/audio-features", params=user_params, headers=user_headers).json()
        audio_features_data = json_response['audio_features']
        
        for data in audio_features_data:
            if data is not None:
                uri = data['uri'][prefixLength:]
                print(uri)
                acousticness = data['acousticness']
                danceability = data['danceability']
                liveness = data['liveness']
                valence = data['valence']
                energy = data['energy']
                print("Acousticness: " + str(acousticness))
                print("Danceability: " + str(danceability))
                print("Liveness: " + str(liveness))
                print("Valence: " + str(valence))
                print("Energy: " + str(energy))

        start += 100
        end += 100    
    print(total)

def songCollection(token):
    user_headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
    }

    users_top_artists, users_top_related_artists = getUsersArtists(user_headers)
    users_saved_songs, users_artists_top_songs, users_related_artists_top_songs = getUsersSongs(user_headers, users_top_artists, users_top_related_artists)
    #features_saved_songs = getAudioFeatures(user_headers, users_related_artists_top_songs)

    print("These are the users top 30 artists:")
    print(users_top_artists)
    print("These are the top songs of those 30 artists:")
    print(users_artists_top_songs)
    print("These are the audio features for those songs:")
    getAudioFeatures(user_headers, users_artists_top_songs)
'''

    print("These are artists related to the users top 30 artists:")
    print(users_top_related_artists)
    print()



    print("These are the top songs of those related artists:")
    print(users_related_artists_top_songs)

    print("These are the users saved songs:")
    print(users_saved_songs)'''
