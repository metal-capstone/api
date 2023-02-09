import json

secrets_json = json.load(open("secrets.json"))
MONGODB_DATABASE_URL = secrets_json["mongodb-database-url"]
MONGODB_CLUSTER_NAME = secrets_json["mongodb-cluster-name"]
del secrets_json

def test_mongodb(db):
    response = db["test-collection"].find_one({"message": "MongoDB connection is working"})
    return response

def get_user(db, account_id: str):
    user = db["User"].find_one({"account_id": account_id})
    return user

def get_account(db, account_id: str):
    account = db["Account"].find_one({"account_id": account_id})
    return account
