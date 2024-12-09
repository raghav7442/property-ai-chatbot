# from pymongo import MongoClient
# from bson.objectid import ObjectId
# from dotenv import load_dotenv
# load_dotenv()
# import os
# import json
# DB_NAME = os.getenv("DB_NAME")
# COLLECTION_NAME = os.getenv("COLLECTION_NAME")
# MONGO_URI = os.getenv("MONGO_URI")

# mongo_client = MongoClient(MONGO_URI)
# db = mongo_client[DB_NAME]
# collection = db["usersearchhistories"]
# # def user_activity():
# #     results = collection.find({'user_id': ObjectId('672c5c6e454ad4aa7e715873')})
# #     # documents=[]
# #     for document in results:
# #         print(document)
#     # return document
# def user_activity():
#     results = collection.find({'user_id': ObjectId('672c5c6e454ad4aa7e715873')})
#     search_texts = [document.get('search_text') for document in results]
#     return search_texts



# def user_search_history(user_id: str = None, ip_address: str = None) -> list:
#     """
#     Fetches the search history for a given user.
    
#     Args:
#         email (str): User's email address.
#         ip_address (str): User's IP address.

    
#     Returns:
#         list: Chat history.
    
#     Raises:
#         ValueError: If neither email nor IP address is provided.
#     """
#     if not user_id and not ip_address:
#         raise ValueError("At least one of email or ip_address must be provided.")

#     query = {"$or": [{"user_id": user_id}, {"ip_address": ip_address}]} if user_id and ip_address else \
#             {"user_id": user_id} if user_id else {"ip_address": ip_address}

#     try:
#         search = collection.find(query)
#         for document in se:
#              print(document)
#         # return search.get("search_text", []) if search else []
#     except Exception as e:
#         raise Exception(f"Failed to fetch chat history: {e}")


# # user_id=ObjectId('672c5c6e454ad4aa7e715873')
# # ip=None
# # user_search_history(user_id, ip)

# user_activity()