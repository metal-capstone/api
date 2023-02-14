import json
import models

credentials_json = json.load(open("credentials.json"))
MONGODB_DATABASE_URL = credentials_json["mongodb-database-url"]
MONGODB_CLUSTER_NAME = credentials_json["mongodb-cluster-name"]
del credentials_json

def test_mongodb(db) -> models.TestData:
    response = db["test-collection"].find_one({"message": "MongoDB connection is working"})
    test_data: models.TestData = models.TestData(**response)
    return test_data

def get_user(db, account_id: str):
    user = db["User"].find_one({"account_id": account_id})
    return user

def get_account(db, account_id: str):
    account = db["Account"].find_one({"account_id": account_id})
    return account
