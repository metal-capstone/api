import requests

def getUserInfo(access_token):
    user_headers = {
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json"
    }
    user_params = {
        "limit": 50
    }
    user_info_response = requests.get("https://api.spotify.com/v1/me", params=user_params, headers=user_headers)
    user_info = user_info_response.json()
    return { "type":"user-info", "username": user_info['display_name'], "profile_pic": user_info['images'][0]['url'] }