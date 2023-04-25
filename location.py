import httpx
import json

credentials_json = json.load(open("credentials.json"))
apiKey = credentials_json["maps_key"]


def getPlace(lat: float, long: float) -> str:
    # Reverse gerolocation to get address
    addressData = httpx.get(f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{long}&key={apiKey}").json()
    placeID = addressData["results"][0]["place_id"]
    #address = addressData["results"][0]["formatted_address"]

    # Get placeID from user's address
    # placeID = addressData["results"][0]["place_id"]

    # Hardcoded Out-R-Inn Place ID
    #placeID = "ChIJRX1tQ7uOOIgRO9wNKF-naaE"

    # Hardcoded Ohio Stadium Place ID
    #placeID = "ChIJVX_yAZSOOIgRpZhJFs2DSUs"

    # Hardcoded Thompson Library Place ID
    #placeID = "ChIJP74-z5eOOIgRBVNFuzx7O7U"

    # Get place type from user's place type
    placeDetails = httpx.get(f"https://maps.googleapis.com/maps/api/place/details/json?place_id={placeID}&fields=types&key={apiKey}").json()

    placeType = placeDetails['result']['types'][0]

    return placeType
