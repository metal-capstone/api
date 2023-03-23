import pymongo
import certifi

def favSongs(collectionFavSongs, features_saved_songs, features_top_songs):
    collectionFavSongs.insert_many(features_saved_songs)
    collectionFavSongs.insert_many(features_top_songs)

def relatedSongs(collectionRelatedSongs, features_related_top_songs):
    collectionRelatedSongs.insert_many(features_related_top_songs)

def databasePopulation(features_saved_songs, features_top_songs, features_related_top_songs):

    dbClient = pymongo.MongoClient(
    "mongodb+srv://metal-user:djKjLBF62wmcu0gl@spotify-chatbot-cluster.pnezn7m.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=certifi.where())

    dbSpotifyData = dbClient["UsersSpotifyData"]
    collectionFavSongs = dbSpotifyData["FavSongs"]
    collectionRelatedSongs = dbSpotifyData["RelatedSongs"]

    favSongs(collectionFavSongs, features_saved_songs, features_top_songs)
    relatedSongs(collectionRelatedSongs, features_related_top_songs)