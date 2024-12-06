# def save_message_to_mongo(user_content, ai_content, email, collection,chat_summary):
#     """
#     Save a message in MongoDB in the following format:
#     - Adds the message as a new entry in the chat history.
#     - Upserts the document if it doesn’t exist for a given email.
#     """
#     message = {
#         "req": user_content,
#         "res": ai_content,
#         "timestamp": datetime.datetime.utcnow()
#     }
#     collection.update_one(
#         {"email": email},
#        {
#             "$push": {"history": message},
#             "$set": {"summary": chat_summary}
#         },
#         upsert=True
#     )


# def fetch_chat_history(email):
#     """
#     Retrieve the last 'limit' messages from MongoDB for a given email and session_id.
#     - This enables the LLM to maintain continuity in the conversation.
#     """
#     record = chat_history_collection.find_one({"email": email})
#     if record:
#         session_chat = record.get("history", [])
#         # Return only the last 'limit' number of messages for brevity in memory
#         return session_chat[:]
#     return []




# def jwt_verify(token):
#     """
#     verify the jwt token if tkon given, it will extract the details from the token
#     """
#     if token:
#         jwt_token=jwt.decode(jwt=token, key=os.getenv("JWT_SECRET"), algorithms=["HS256"])
#         extracted_data={
#             "IP":None,
#             "id":jwt_token["user"]["_id"],
#             "name":jwt_token["user"]["name"],
#             "email":jwt_token["user"]["email"],
#             "gender":jwt_token["user"]["gender"]

#         }
#         return extracted_data
#     else:
#         return "expected token", 200




# -------------fetch chat history----------------------------------
# def fetch_chat_history(email=None, ip_address=None):
#     """
#     Find a chat document by email or IP address.
    
#     Args:
#         email (str): The email address of the user.
#         ip_address (str): The IP address of the user.
#         collection: The MongoDB collection object.
    
#     Returns:
#         list: A list of chat documents that match the query.
#     """
#     query = {}
    
#     # Build query based on available parameters
#     if email and ip_address:
#         query = {"$or": [{"email": email}, {"ip_address": ip_address}]}
#     elif email:
#         query = {"email": email}
#     elif ip_address:
#         query = {"ip_address": ip_address}
#     else:
#         raise ValueError("At least one of email or ip_address must be provided.")

#     # Execute the query
#     chats = chat_history_collection.find_one(query)
#     if chats:
#         session_chat = chats.get("history", [])

#         return session_chat[:]
#     return []












# @app.route('/chat_history',methods=['POST'])
# def get_chat_history():
#     data = request.get_json()
#     ip_address = data.get("IP")
#     email = data.get("email")
    
#     # Assuming fetch_chat_history returns the chat history as a list of dicts
#     chats = fetch_chat_history(email, ip_address)
#     for chat in chats:
#         if isinstance(chat.get("res"), str):
#             try:
#                 chat["res"] = json.loads(chat["res"]) 
#             except json.JSONDecodeError:
#                 chat["res"] = {"error": "Invalid JSON format"}  
    
#     return jsonify(chats)
