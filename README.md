# Spotify Chatbot api

## Other required setup

Download the `credentials.json` from the google drive and put it in the `/api` folder.

## Create container

```docker
docker build -t spotify-chatbot-api-image .
```

## Run container

```docker
docker run -p 8000:8000 -d spotify-chatbot-api-image
```

## Run api without docker

```cmd
uvicorn main:app --reload
```

## Debug the api

1. Open the api folder in VSCode.
2. Select the Run and Debug tab on the left bar.
3. Choose `Python: Start and attach to API`.
4. Press the green play button next to it.


## Set up database connection
Create a `secrets.json` file in the api folder. Add the contents below to this file.
```json
{
    "mongodb-database-url": "<mongodb_database_url>",
    "mongodb-cluster-name": "<mongodb_cluster_name>"
}
```
Update the fields with correct database secret info.
