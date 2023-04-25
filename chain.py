import json
import httpx
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
# from langchain.tools import BaseTool
from langchain.llms import OpenAI
from langchain import LLMMathChain, SerpAPIWrapper
from langchain.prompts import PromptTemplate
import spotify
import messageHandler

credentials_json = json.load(open("credentials.json"))
OPENAI_SECRET_KEY = credentials_json["openai_secret_key"]
del credentials_json

def search_spotify_for_artist(artist_name, access_token):
        userHeader = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json'
        }
        
        params = {
            'q': artist_name,
            'type': 'artist',
            'limit': 1,
        }
        res = httpx.get("https://api.spotify.com/v1/search", params=params, headers=userHeader).json()
        
        id = ''
        name = ''
                
        if len(res['artists']['items']) == 0:
            return None
        else:
            id = res['artists']['items'][0]['id']
            name = res['artists']['items'][0]['name']
            return id

# Takes a string with 0-n artist names. Returns an array of artist IDs
# This is the function for demo mode
def getArtistIds(query, access_token):
        llm = OpenAI(temperature=0.05, openai_api_key=OPENAI_SECRET_KEY)
        artist_names = llm.generate([
            f"""Extract music artists names from a sentence: {query}. With this extracted info, return a comma separated list of artist names from the input.
             If there are no artist names in the answer provided should be the word 'empty' with nothing else. Provide the answer as just the list with no preamble.
            """
        ])
        artist_names = artist_names.generations[0][0].text # Pull out response
        artist_names = artist_names.replace('\n', '')
        artist_names = artist_names.lower()
        if artist_names == 'empty':
            return []
        else:
            answer = []
            artist_names = artist_names.split(',')
            for artist in artist_names:
                artist_id = search_spotify_for_artist(artist, access_token)
                if artist_id is not None:
                    answer.append(artist_id)
        # artist_names = artist_names.replace('answer: ', '') # Remove the assignment at the front of the response
            return answer
        # search_params = json.loads(search_params) # Parse the response into an object
        # self.search_spotify(search_params)
        # return search_params

def getResponse(query):
    print(query)

class Chain:
    def __init__(self, access_token,sessionID, sessions):
        self.access_token = access_token
        self.sessionID = sessionID
        self.sessions = sessions
        llm = OpenAI(temperature=0.05, openai_api_key=OPENAI_SECRET_KEY)
        tools = [
            Tool(
                name="Spotify ID Extractor",
                func=self.getSpotifyIds,
                description="Do not infer any additional information beyond what the user has explicitly requested. Only use this tool if the user asks for a specific artist, album, or song in their message Ask this tool questions like What is the song ID of song_name? What is the album ID album_name? or What is the artist ID of artist_name? or What is the song ID of song_name by artist_name? (Do not modify or infer any information about a song, album, or artist In other words, if the user does not provide an artist name, do not auto fill it)"
            ),
            Tool(
                name="Music Playback Controller",
                func=self.interactWithPlayback,
                description="Controls the music player buttons for play, pause, skip, and back. Use this tool when the user wishes to perform one of these actions. For this tool to work you must input one of these words: play, pause, skip, back. If you use this tool, do not use the Spotify ID Extractor as well."
            ),
            Tool(
                name="Play new music",
                func=self.playMusic,
                description="Use this tool when the user says something like refresh or shuffle the music."
            ),
            Tool(
                name="Make a playlist",
                func=self.makePlaylist,
                description="Use this tool when the user expresses interest in making a new playlist. The user should say something along the lines of 'I want to create a new playlist'."
            )
        ]
        self.agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

    def playMusic(self, query):
        messageHandler.handleAction('Start Music Action', self.sessionID, self.sessions)
    
    def makePlaylist(self, query):
        messageHandler.handleAction('Make A Playlist', self.sessionID, self.sessions)

    def interactWithPlayback(self, query):
        print(query)
        userHeader = userHeader = {
            'Authorization': 'Bearer ' + self.access_token,
            'Content-Type': 'application/json'
        }
        if query == 'play':
            httpx.put("https://api.spotify.com/v1/me/player/play",headers=userHeader)
        elif query == 'pause':
            httpx.put("https://api.spotify.com/v1/me/player/pause", headers=userHeader)
        elif query == 'skip':
            httpx.post("https://api.spotify.com/v1/me/player/next", headers=userHeader)
        elif query == 'back':
            httpx.post("https://api.spotify.com/v1/me/player/previous", headers=userHeader)
        
    def search_spotify(self, search_params):
        access_token = self.access_token
        userHeader = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json'
        }
        query_string = ""
        if len(search_params['filter']) == 0:
            query_string = search_params['query']
        elif not ":" in search_params['filter']:
            query_string = search_params['query']
        else:
            query_string = f"{search_params['query']} {search_params['filter']}"
        
        query_type = search_params['type']
        
        params = {
            'q': query_string,
            'type': query_type,
            'limit': 1,
        }
        res = httpx.get("https://api.spotify.com/v1/search", params=params, headers=userHeader).json()
        
        id = ''
        name = ''
        if query_type == 'track':
            if len(res['tracks']['items']) == 0:
                return "Could not find the track"
            else:
                id = res['tracks']['items'][0]['id']
                name = res['tracks']['items'][0]['name']
                spotify.playSong(access_token,[f"spotify:track:{id}"])
                return f"Playing track {name}"
                
        elif query_type == 'artist':
            if len(res['artists']['items']) == 0:
                return "Could not find the artist"
            else:
                id = res['artists']['items'][0]['id']
                name = res['artists']['items'][0]['name']
                spotify.playContext(access_token,f"spotify:artist:{id}")
                return f"Playing {name}'s music"
    
        elif query_type == 'album':
            if len(res['albums']['items']) == 0:
                return "Could not find the album"
            else:
                id = res['albums']['items'][0]['id']
                name = res['albums']['items'][0]['name']
                # context = 
                spotify.playContext(access_token,f"spotify:album:{id}")
                # httpx.put("https://api.spotify.com/v1/me/player/play", json={'context_uri': [f"spotify:album:{id}"]}, headers=userHeader)
                return f"Playing the album {name}"

    def getSpotifyIds(self, query):
        spotfy_llm = OpenAI(temperature=0.05, openai_api_key=OPENAI_SECRET_KEY)
        search_params = spotfy_llm.generate([
            f"""Assume you are a tool that extracts artists, albums, and or song names from a sentence. With this extracted info, you will build a JSON object which is used to query Spotify's /search endpoint.

            Here is the documentation for the endpoint:

            query (string):
            Your search query. Should only contain a single song, artist, or album name. If the user requests a song, from a specific artist for example, use the artist name as a filter not the query.
            
            filter (string):
            Leave filter as an empty string in search_params unless the user has explicitly provided with an artist's name along with a song or album name. The available filters are album, artist, track
            Example values for filter could be: "artist:Queen", "", "artist: David Bowie"

            type (string): Search result includes hits from the specified item type. Allowed values: "album", "artist", or "track".

            input = "{query}"

            search_params = {{
            "query": "",
            "filter": "",
            "type": ""
            }}

            Fill in the answer.
            """
        ])
        search_params = search_params.generations[0][0].text # Pull out response
        search_params = search_params.replace('search_params = ', '') # Remove the assignment at the front of the response
        search_params = json.loads(search_params) # Parse the response into an object
        self.search_spotify(search_params)
        return search_params


    def run(self, user_input):
        # user_input = "Play One by U2"
        res = self.agent.run(f"""You are a DJ that talks to a user and plays music based on what the user requests.
    The user can request music from specific artists, songs, or albums. The user can also make open ended
    request for types of music based on how it sounds. If the user requests something specific, retrieve 
    the necessary spotify IDs with tools. You can also press play pause skip and back on the user's music 
    player the Music Player Controller tool. You don't need to use the Music Player Controller if you have used 
    the Spotify ID Extractor. Always respond to the user before finishing. The user may also talk to you without making music related requests. Talk to the user as well if they are making conversation. The user 
    said '{user_input}'""")
        return res
    

# access_token = 'BQBZoH6iG8f-QWX6T-mYbtIKSqkDPaWKzLgCLCux1vcL6F4TL_ZEmyuVEKN2tIv6NvInMiXgVgiBmXiMBNBIYwsxAng7wWxLiTpeN3jQCqeGAQlXpqXUMXsvaS5UoWsx4MewDCcKttt1qBJK_9Mu8cHtngqtROMNurCcAAFXcxw4E6QSf17LDX3V4EB-NVhtq406PV5Wf9Of0EeGG81XXg4uJWPQySnV2Xpolt_FLcBOPC_KWxtPRPrRzTFvwNIGmM0XgymCUYJfSTsxMBY7bKCS11QulTrmgRvQeRYBH73NDA'
# agent_chain = Chain(access_token)
# res = agent_chain.run('play baby sasuke')