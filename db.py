# import pymongo
from pymongo import MongoClient

# def connect_to_mongo():
#     import pymongo
#     client = pymongo.MongoClient("mongodb://localhost:27017")
#     db = client["database"] #this bracket syntax is better if the dot syntax doesn't work
#     print("success, bitch")
#     return db


class DatabaseManager:
    DATABASE_NAME = "database_name"
    COLLECTION_NAME = "my_collection"
    CONNECTION_STRING = "mongodb://localhost:27017"

    def __init__(self):
        self.client = MongoClient(DatabaseManager.CONNECTION_STRING)
        self.db = self.client[DatabaseManager.DATABASE_NAME]
        self.collection = self.db[DatabaseManager.COLLECTION_NAME]

    def add_document(self, document):
        self.collection.insert_one(document)

    def find_document(self, query):
        return self.collection.find_one(query)

    def update_document(self, key, value, upsert):
        return self.collection.update_one(key, value, upsert)
