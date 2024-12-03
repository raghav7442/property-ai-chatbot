import os
import datetime
from pymongo import MongoClient
from openai import OpenAI
from mongoembedding import MongoDBEmbeddings
from get_embeddings import *
import json
import jwt
from prompt import *
# Initialize OpenAI client for LLM
client = OpenAI()
from dotenv import load_dotenv
load_dotenv()

# Initialize embedding handler for property data retrieval
embedding_handler = MongoDBEmbeddings(
    db_name=os.getenv("DB_NAME"), 
    collection_name=os.getenv("COLLECTION_NAME"), 
    mongo_uri=os.getenv("MONGO_URI")
)

# Initialize MongoDB client and specify the database and collection
mongo_client = MongoClient(os.getenv("MONGO_URI"))
db = mongo_client[os.getenv("DB_NAME")]
chat_history_collection = db["chat_history"]
jwt_secret=os.getenv("JWT_SECRET")

def jwt_verify(token):
    if token:
        jwt_token=jwt.decode(jwt=token, key=os.getenv("JWT_SECRET"), algorithms=["HS256"])
        extracted_data={
            "id":jwt_token["user"]["_id"],
            "name":jwt_token["user"]["name"],
            "email":jwt_token["user"]["email"],
            "gender":jwt_token["user"]["gender"]

        }
        return extracted_data
    else:
        return "expected token", 200


def save_message_to_mongo(user_content, ai_content, email, collection,chat_summary):
    """
    Save a message in MongoDB in the following format:
    - Adds the message as a new entry in the chat history.
    - Upserts the document if it doesn’t exist for a given email.
    """
    message = {
        "req": user_content,
        "res": ai_content,
        "timestamp": datetime.datetime.utcnow()
    }
    collection.update_one(
        {"email": email},
       {
            "$push": {"history": message},
            "$set": {"summary": chat_summary}
        },
        upsert=True
    )


# def save_message_to_mongo(user_content, ai_content, email, collection, chat_summary, ip_address, name):
#     """
#     Save a message in MongoDB in the following format:
#     - Adds the message as a new entry in the chat history.
#     - Upserts the document if it doesn’t exist for a given email.
#     - Includes additional fields: IP address, email, and name.
#     """
#     message = {
#         "req": user_content,
#         "res": ai_content,
#         "timestamp": datetime.datetime.utcnow()
#     }
#     collection.update_one(
#         {"email": email},
#         {
#             "$set": {
#                 "email": email,
#                 "ip_address": ip_address,
#                 "name": name,
#                 "summary": chat_summary
#             },
#             "$push": {"history": message}
#         },
#         upsert=True
#     )



def fetch_chat_history(email=None, ip_address=None, collection=None):
    """
    Find a chat document by email or IP address.
    
    Args:
        email (str): The email address of the user.
        ip_address (str): The IP address of the user.
        collection: The MongoDB collection object.
    
    Returns:
        list: A list of chat documents that match the query.
    """
    query = {}
    
    # Build query based on available parameters
    if email and ip_address:
        query = {"$or": [{"email": email}, {"ip_address": ip_address}]}
    elif email:
        query = {"email": email}
    elif ip_address:
        query = {"ip_address": ip_address}
    else:
        raise ValueError("At least one of email or ip_address must be provided.")

    # Execute the query
    chats = collection.find(query)
    return list(chats)  # Convert the cursor to a list




def fetch_chat_history(email):
    """
    Retrieve the last 'limit' messages from MongoDB for a given email and session_id.
    - This enables the LLM to maintain continuity in the conversation.
    """
    record = chat_history_collection.find_one({"email": email})
    if record:
        session_chat = record.get("history", [])
        # Return only the last 'limit' number of messages for brevity in memory
        return session_chat[:]
    return []

def create_summary(email):
    chat_history=fetch_chat_history(email)
    memory_context = "\n".join([f"User: {msg['req']}\nAssistant: {msg['res']}" for msg in chat_history])
    prompt=f"""you have to create a very short user driven chatsummary respected to user what user wnat to say in this history
    here is chat context   {memory_context} 
    """
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": memory_context}
        ]
    )
    assistant_response = completion.choices[0].message.content
    return assistant_response



def get_query_results(user_input, limit):
    """
    Fetches relevant property recommendations from MongoDB based on the user input.
    - Generates an embedding for the user input to use in vector search.
    - Runs a MongoDB aggregate pipeline with vector search for relevant results.
    """
    query_embedding = embedding_handler.generate_embedding(user_input)
    pipeline = [
        {
            "$vectorSearch": {
                "index": os.getenv('INDEX_NAME'),
                "queryVector": query_embedding,
                "path": "embedding",
                "exact": True,
                "limit": limit
            }
        },
        {
            "$project": {
                "_id": 1,
                "location": 1,
                "max_price": 1,
                "min_price": 1,
                "area": 1,
                "bath_counting": 1,
                "room_counting": 1,
                "isParking": 1,
                "parking_area_counting": 1,
                "car_places_counting": 1,
                "features": 1,
                "property": 1,
                "status": 1,
                "construction_status": 1,
                "pin_code": 1,
                "floor": 1,
                "bhk": 1,
                "facing": 1,
                "flat_number": 1,
                "sold_out_date": 1,
                "is_leasehold": 1,
                "lease_year": 1,
                "deletedAt": 1,
                "createdAt": 1,
                "updatedAt": 1,
                "text":1
                
            }
        }
    ]
    collection = embedding_handler.db[embedding_handler.get_collection_name()]
    results = collection.aggregate(pipeline)
    return list(results)



def generate_answer(user_input, email):
    """
    Generate an AI answer for the user input.
    - Fetches recent chat history from MongoDB to provide context.
    - Retrieves property data based on the user query using embeddings.
    - Combines memory and property context to create a prompt for the LLM.
    """
    
    # Fetch previous chat history for context
    chat_history = fetch_chat_history(email["email"])
    # chat_history = fetch_chat_history(email["email"],email["id"],chat_history_collection)
    memory_context = "\n".join([f"User: {msg['req']}\nAssistant: {msg['res']}" for msg in chat_history])
    print(email)
    # Fetch property recommendations based on the current user query
    property_context = get_query_results(user_input, limit=6)
    # print(property_context)
    
  
    prompt_user=f"""
    logging context={email}
    memorycontext={memory_context}
    property context={property_context}

    logging context to check the user signed in or not
    for signin or login here is the guildliens
    GUIDLIENS FOR LOGGING CHECK
    {logging}

    after checking the user's logging status you will start the conversation witht the user, here is the detaild flow of the conversation, you have to be static as it is,
    {task}

    for the conversation refference here are some basic examples to intract with the user,
    {sample_conversations}

    REMEMBER, you have to very strict with the guidliens,
    WHEN EVER FOR EACH CONVERSATION YOUR RESPONSE SYNTAX WILL BE AS IT IS, IT CANNOT BE CHANGES BY IN ANY CONDITION
    for example,
    response:the ai generated response, properties:[proprtyids1, proprtyids2, proprtyids3]
    """



    # Generate response from OpenAI API
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt_user},
            {"role": "user", "content": user_input}
        ]
    )
    assistant_response = completion.choices[0].message.content
    print("Raw Assistant Response:", repr(assistant_response))
    
    try:
        # Check if response is already in JSON format
        if assistant_response.strip().startswith('{') and assistant_response.strip().endswith('}'):
            # Parse as JSON directly
            json_data = json.loads(assistant_response.strip())
        else:
            # Add braces to make it JSON compatible
            fixed_response = f'{{{assistant_response.strip()}}}'
            json_data = json.loads(fixed_response)
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        raise ValueError(f"Invalid JSON format in response: {assistant_response}")
    
    # Save the generated answer to MongoDB chat history
    summary=create_summary(email["email"])
    # save_message_to_mongo(user_content=user_input, ai_content=assistant_response,email= email["email"], collection=chat_history_collection,chat_summary=summary,ip_address=email["id"], name=email["name"])
    save_message_to_mongo(user_input, assistant_response, email["email"], chat_history_collection,chat_summary=summary)
    return json_data




def affordable(query, location):

    if not location or "latitude" not in location or "longitude" not in location:
        return{"error": "Invalid location data"}, 400

    # Extract latitude and longitude
    latitude = location["latitude"]
    longitude = location["longitude"]

    # Convert range to radians
    range_in_radians = 25 / 6378.1 
    loc = {
        "location": {
            "$geoWithin": {
                "$centerSphere": [[longitude, latitude], range_in_radians]
            }
        }
    }

    # Fetch matching locations
    results = list(embedding_handler.collection.find(loc, {"_id": 0, "embedding":0}))
    # print(results)


    property_context=get_query_results(query, limit=6)
    prompt=f"""
You are an affordability analysis tool. Your job is to analyze and return relevant property IDs based on the following contexts:

- **Property Context:** {property_context}
- **Location Context:** {results}

Requirements:
1. Always return the property IDs as an array.
2. Respond only with plain JSON format (no Markdown or additional formatting).
3. If no properties match, provide at least 2-3 alternative property IDs from the location context.

Example response:
{{"properties": ["id1", "id2", "id3"]}}

remember to give only the reponse based on both context, do not create any response with your own
"""
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query}
        ]
    )
    assistant_response = completion.choices[0].message.content

    try:
        # Clean up Markdown formatting if present
        if assistant_response.startswith("```") and assistant_response.endswith("```"):
            assistant_response = assistant_response.strip("```").strip()

        # Parse JSON
        json_data = json.loads(assistant_response.strip())
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e}")
        raise ValueError(f"Invalid JSON format in response: {assistant_response}")
    
    return json_data