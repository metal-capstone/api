import googlemaps

import requests

apikey = "AIzaSyD-nWYRnGB-nDJligN9nv4xibrB5tzmHDQ"

payload = {}
headers = {}
geoloc = requests.post(
    "https://www.googleapis.com/geolocation/v1/geolocate?key=AIzaSyD-nWYRnGB-nDJligN9nv4xibrB5tzmHDQ").json()

lat = geoloc["location"]["lat"]
lng = geoloc["location"]["lng"]

addressData = requests.get("https://maps.googleapis.com/maps/api/geocode/json?latlng=" +
                           str(lat) + "," + str(lng) + "&key=AIzaSyD-nWYRnGB-nDJligN9nv4xibrB5tzmHDQ").json()
address = addressData["results"][0]["formatted_address"]
# placeID = addressData["results"][0]["place_id"]
placeID = "ChIJKwAD-riOOIgRca8ZNY_mJkk"


placeDetails = requests.get(
    "https://maps.googleapis.com/maps/api/place/details/json?place_id=" + placeID + "&fields=types&key=AIzaSyD-nWYRnGB-nDJligN9nv4xibrB5tzmHDQ")

print(placeDetails.json())
