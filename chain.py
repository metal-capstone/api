import json
import httpx
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
# from langchain.tools import BaseTool
from langchain.llms import OpenAI
from langchain import LLMMathChain, SerpAPIWrapper
from langchain.prompts import PromptTemplate

def search_spotify(search_params):
    access_token = ""
    userHeader = userHeader = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }
    query_string = ""
    if len(search_params['filter']) == 0:
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
        id = res['tracks']['items'][0]['id']
        name = res['tracks']['items'][0]['name']
    print(id, name)

def getSpotifyIds(query):
    spotfy_llm = OpenAI(temperature=0.05, openai_api_key=OPENAI_SECRET_KEY)
    search_params = spotfy_llm.generate([
        f"""Assume you are a tool that extracts artists, albums, and or song names from a sentence. With this extracted info, you will build a JSON object which is used to query Spotify's /search endpoint.

        Here is the documentation for the endpoint:

        query (string):
        Your search query. Should only contain a single song, artist, or album name. If the user requests a song, from a specific artist for example, use the artist name as a filter not the query.
        
        filter (string):
        Leave this blank unless the input explicitly provides information to filter against. Do not You can narrow down your search using a filter. The available filters are album, artist, track. Only use a filter if the input is doing something like requesting a song or album from a specific artist. Example value: "artist:Queen".

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
    search_spotify(search_params)
    return search_params

def getResponse(query):
    print(query)

credentials_json = json.load(open("credentials.json"))
OPENAI_SECRET_KEY = credentials_json["openai_secret_key"]
del credentials_json

class Chain:
    def __init__(self, access_token):
        self.access_token = access_token
        llm = OpenAI(temperature=0.05, openai_api_key=OPENAI_SECRET_KEY)
        tools = [
            Tool(
                name="Spotify ID Extractor",
                func=getSpotifyIds,
                description="Do not use this tool unless the user asks for an exact artist, album, or song in their message Ask questions like What is the song ID of song_name? What is the album ID album_name? or What is the artist ID of artist_name? or What is the song ID of song_name by artist_name? (Do not modify or infer any information about a song, album, or artist In other words, if the user does not provide an artist name, do not auto fill it)"
            ),
            Tool(
                name="Music Playback Controller",
                func=self.interactWithPlayback,
                description="Controls the music player buttons for play, pause, skip, and back. Use this tool when the user wishes to perform one of these actions. For this tool to work you must input one of these words: play, pause, skip, back. If you use this tool, do not use the Spotify ID Extractor as well."
            ),
            Tool(
                name="Respond to user",
                func=getResponse,
                description="A user friendly response creator. Always use this tool at the end when no other tool is needed so that a nice response is made for the user."
            )
        ]
        self.agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

    def interactWithPlayback(self, query):
        print(query)
        userHeader = userHeader = {
            'Authorization': 'Bearer ' + self.access_token,
            'Content-Type': 'application/json'
        }
        if query == 'play':
            res = httpx.put("https://api.spotify.com/v1/me/player/play", headers=userHeader).json()
        elif query == 'pause':
            res = httpx.put("https://api.spotify.com/v1/me/player/pause", headers=userHeader).json()
        elif query == 'skip':
            res = httpx.post("https://api.spotify.com/v1/me/player/next", headers=userHeader).json()
        elif query == 'back':
            res = httpx.post("https://api.spotify.com/v1/me/player/previous", headers=userHeader).json()
        

    def run(self, user_input):
        # user_input = "Play One by U2"
        self.agent.run(f"""You are a DJ that talks to a user and plays music based on what the user requests.
    The user can request music from specific artists, songs, or albums. The user can also make open ended
    request for types of music based on how it sounds. If the user requests something specific, retrieve 
    the necessary spotify IDs with tools. Always use the 'Respond to user tool' before finishing. The user 
    said '{user_input}'""")