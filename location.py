import requests
import json

credentials_json = json.load(open("credentials.json"))
apiKey = credentials_json["maps_key"]


def getPlace():
    apiKey = credentials_json["maps_key"]
    # Get user's geolocation
    geoloc = requests.post(
        "https://www.googleapis.com/geolocation/v1/geolocate?key="+apiKey).json()
    # print(geoloc)

    lat = geoloc["location"]["lat"]
    lng = geoloc["location"]["lng"]

    # Reverse gerolocation to get address
    addressData = requests.get("https://maps.googleapis.com/maps/api/geocode/json?latlng=" +
                               str(lat) + "," + str(lng) + "&key="+apiKey).json()
    address = addressData["results"][0]["formatted_address"]

    # Get placeID from user's address
    # placeID = addressData["results"][0]["place_id"]

    # Hardcoded Out-R-Inn Place ID
    placeID = "ChIJRX1tQ7uOOIgRO9wNKF-naaE"

    # Hardcoded Ohio Stadium Place ID
    #placeID = "ChIJVX_yAZSOOIgRpZhJFs2DSUs"

    # Hardcoded Thompson Library Place ID
    # placeID = "ChIJP74-z5eOOIgRBVNFuzx7O7U"

    # Get place type from user's place type
    placeDetails = requests.get(
        "https://maps.googleapis.com/maps/api/place/details/json?place_id=" + placeID + "&fields=types&key="+apiKey).json()

    placeType = placeDetails['result']['types'][0]

    return placeType
