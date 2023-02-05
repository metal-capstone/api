# Spotify Chatbot api

## Create container
```
docker build -t spotify-chatbot-api-image .
```

## Run container
```
docker run -p 8000:8000 -d spotify-chatbot-api-image
```

## Run api without docker
```
uvicorn main:app --reload
```

## Debug the api
1. Open the api folder in VSCode.
2. Select the Run and Debug tab on the left bar.
3. Choose `Python: Start and attach to API`.
4. Press the green play button next to it.