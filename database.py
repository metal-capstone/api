from pymongo import MongoClient
import json
import models

credentials_json = json.load(open("credentials.json"))
MONGODB_DATABASE_URL = credentials_json["mongodb-database-url"]
MONGODB_TEST_CLUSTER_NAME = credentials_json["mongodb-cluster-name"]
MONGODB_CLIENT = MongoClient(MONGODB_DATABASE_URL)
TEST_CLUSTER = MONGODB_CLIENT[MONGODB_TEST_CLUSTER_NAME]
USER_DATA_CLUSTER = MONGODB_CLIENT['UserData']
del credentials_json

def close_client():
    MONGODB_CLIENT.close()

def test_mongodb() -> models.TestData:
    response = TEST_CLUSTER["test-collection"].find_one({"message": "MongoDB connection is working"})
    test_data: models.TestData = models.TestData(**response)
    return test_data

def create_user(id, username, refresh_token, session_id):
    new_user = {
        '_id': id,
        'username': username,
        'refresh_token': refresh_token,
        'session_id': session_id
    }

    USER_DATA_CLUSTER['Users'].insert_one(new_user)

def user_exists(id):
    num_users = USER_DATA_CLUSTER['Users'].count_documents({'_id': id}, limit = 1)
    return num_users != 0

def clear_user(id):
    USER_DATA_CLUSTER['Users'].delete_one({'_id': id})

def valid_session(session_id):
    num_users = USER_DATA_CLUSTER['Users'].count_documents({'session_id': session_id}, limit = 1)
    return num_users != 0
    
def get_session_data(session_id):
    user = USER_DATA_CLUSTER['Users'].find_one({'session_id': session_id})
    return user['refresh_token'], user['_id']

def update_session(id, session_id):
    USER_DATA_CLUSTER['Users'].update_one({'_id': id}, { '$set': { 'session_id': session_id } })

def clear_session(session_id):
    USER_DATA_CLUSTER['Users'].update_one({'session_id': session_id}, { '$unset': { 'session_id': 1 } })
