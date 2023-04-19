import json
import httpx
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.tools import BaseTool
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

credentials_json = json.load(open("credentials.json"))
OPENAI_SECRET_KEY = credentials_json["openai_secret_key"]
del credentials_json

llm = OpenAI(temperature=0.05, openai_api_key=OPENAI_SECRET_KEY)
# search = SerpAPIWrapper(serpapi_api_key="AIzaSyCDavyaCu-z4s04yZ7cTysNuBUzgDD988c")
llm_math_chain = LLMMathChain(llm=llm, verbose=True)
tools = [
    Tool(
        name="Spotify ID Extractor",
        func=getSpotifyIds,
        description="Ask questions like What is the song ID of song_name? What is the album ID album_name? or What is the artist ID of artist_name? or What is the song ID of song_name by artist_name? (Do not modify or infer any information about a song, album, or artist In other words, if the user does not provide an artist name, do not auto fill it)"
    ),
    Tool(
        name="Calculator",
        func=llm_math_chain.run,
        description="useful for when you need to answer questions about math"
    )
]

agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)

user_input = "Play One by U2"
agent.run(f"""You are a DJ that talks to a user and plays music based on what the user requests.
The user can request music from specific artists, songs, or albums. The user can also make open ended
request for types of music based on how it sounds. If the user requests something specific, retrieve 
the necessary spotify IDs with tools. Make sure to use the tool exactly as described. The user said '{user_input}'""")