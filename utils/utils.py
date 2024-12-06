import os
import datetime
from pymongo import MongoClient
from openai import OpenAI
from database.mongoembedding import MongoDBEmbeddings
from database.get_embeddings import *
import json
import jwt
from utils.exceptions import handle_exceptions
from utils.prompt import *
# Initialize OpenAI client for LLM
from dotenv import load_dotenv



load_dotenv()
client = OpenAI()

load_dotenv()
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
MONGO_URI = os.getenv("MONGO_URI")
INDEX_NAME = os.getenv("INDEX_NAME")
JWT_SECRET = os.getenv("JWT_SECRET")

# Initialize clients
openai_client = OpenAI()
embedding_handler = MongoDBEmbeddings(
    db_name=DB_NAME,
    collection_name=COLLECTION_NAME,
    mongo_uri=MONGO_URI
)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
chat_history_collection = db["chat_history_NG"]

if not all([DB_NAME, COLLECTION_NAME, MONGO_URI, INDEX_NAME, JWT_SECRET]):
    raise ValueError("Missing required environment variables.")

@handle_exceptions
def jwt_verify(token: str) -> dict:
    """
    Verifies the JWT token and extracts user details.
    Args:
        token (str): The JWT token to verify
    Returns:
        dict: Extracted user details from the token.
    Raises:
        ValueError: If the token is invalid or missing.
    """
    try:
        if not token:
            raise ValueError("Token is required.")
        
        jwt_token = jwt.decode(jwt=token, key=JWT_SECRET, algorithms=["HS256"])
        return {
            "IP":None,
            "id": jwt_token["user"]["_id"],
            "name": jwt_token["user"]["name"],
            "email": jwt_token["user"]["email"],
            "gender": jwt_token["user"]["gender"]
        }
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token.")



@handle_exceptions
def save_message_to_mongo( user_content: str,ai_content: str,email: str,collection,chat_summary: str,ip_address: str,name: str, user_id: str) -> None:
    """
    Save a chat message in MongoDB.
    Raises:
        Exception: If the database operation fails.
    """
    message = {
        "req": user_content,
        "res": ai_content,
        "timestamp": datetime.datetime.utcnow()
    }
    try:
        collection.update_one(
            {"email": email},
            {
                "$set": {
                    "email": email,
                    "ip_address": ip_address,
                    "user_id":user_id,
                    "name": name,
                    "summary": chat_summary
                },
                "$push": {"history": message}
            },
            upsert=True
        )
    except Exception as e:
        raise Exception(f"Failed to save message to MongoDB: {e}")



@handle_exceptions
# def fetch_chat_history(email: str = None, ip_address: str = None) -> list:
#     """
#     Fetches the chat history for a given user.
    
#     Args:
#         email (str): User's email address.
#         ip_address (str): User's IP address.
    
#     Returns:
#         list: Chat history.
    
#     Raises:
#         ValueError: If neither email nor IP address is provided.
#     """
#     if not email and not ip_address:
#         raise ValueError("At least one of email or ip_address must be provided.")

#     query = {"$or": [{"email": email}, {"ip_address": ip_address}]} if email and ip_address else \
#             {"email": email} if email else {"ip_address": ip_address}

#     try:
#         chats = chat_history_collection.find_one(query)
#         return chats.get("history", []) if chats else []
#     except Exception as e:
#         raise Exception(f"Failed to fetch chat history: {e}")


def fetch_chat_history(email, ip_address):
    # Dummy implementation for demonstration
    return [
        {
            "req": "can you suggest me some properties in mumba",
            "res": {
                "properties": [],
                "response": "Welcome back! I see you are logged in, Govind. Could you share which specific location in Mumbai you’re interested in?"
            },
            "timestamp": "Thu, 05 Dec 2024 10:57:53 GMT"
        },
        {
            "req": "hi",
            "res": {
                "properties": [],
                "response": "Hello, Govind! How can I assist you today with your property search in Mumbai?"
            },
            "timestamp": "Thu, 05 Dec 2024 13:25:40 GMT"
        },
        {
            "req": "no i want to search properties somewhere else",
            "res": {
                "properties": ["674f0636d5a12524f74c23f9"],
                "response": "Sure, Govind! Could you please specify the location where you're interested in searching for properties?"
            },
            "timestamp": "Thu, 05 Dec 2024 13:26:05 GMT"
        },
        {
            "req": "can you suggest me some properties in mumba",
            "res": {
                "properties": [],
                "response": "Welcome back! I see you are logged in, Govind. Could you share which specific location in Mumbai you’re interested in?"
            },
            "timestamp": "Thu, 05 Dec 2024 13:31:07 GMT"
        },
        {
            "req": "hi kya hal hai?",
            "res": {
                "properties": [],
                "response": "Namaste, Govind! I'm here to help you with property searches. How can I assist you today?"
            },
            "timestamp": "Thu, 05 Dec 2024 13:35:12 GMT"
        }
    ]



@handle_exceptions
def create_summary(email):
    chat_history=fetch_chat_history(email)
    memory_context = "\n".join([f"User: {msg['req']}\nAssistant: {msg['res']}" for msg in chat_history])
    prompt=f"""You need to create a very short, user-driven chat summary based on what the user wants to say in this history. For example, the user's name is [name], his email is [email], ad mobile number is [number] he/she want to search for properties in Mumbai, their budget is [budget], and he/she are particularly interested in buying a property in that area. Based on the chat context, you will gather all the user's information, interests, and habits, and create a user summary denoted by 'res' in the chat context. The summary will reflect the user's details, behavior, buying interests, and any concerns related to their purchase.
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


@handle_exceptions
def get_query_results(user_input: str, limit: int) -> list:
    """
    Fetches property recommendations using vector search.
    Raises:
        Exception: If the database operation fails.
    """
    try:
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
                    "_id": 1,"location": 1,"max_price": 1,"min_price": 1,"area": 1,"bath_counting":1,
                    "room_counting": 1,"isParking": 1,"parking_area_counting": 1,
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
    except Exception as e:
        raise Exception(f"Error in fetching query results: {e}")


@handle_exceptions
def generate_answer(user_input, user_details):
    """
    Generate an AI answer for the user input.
    - Fetches recent chat history from MongoDB to provide context.
    - Retrieves property data based on the user query using embeddings.
    - Combines memory and property context to create a prompt for the LLM.
    """
    
    email=user_details["email"]
    ip=user_details["IP"]
    user_name=user_details["name"]
    user_id=user_details["id"]
    chat_history = fetch_chat_history(email, ip)
    memory_context = "\n".join([f"User: {msg['req']}\nAssistant: {msg['res']}" for msg in chat_history])
    property_context = get_query_results(user_input, limit=6)
    print(f"email:{email}, ipaddress:{ip}, users name:{user_name}")
    prompt_user=f"""
    logging context={user_details}
    memorycontext={memory_context}
    property context={property_context}

    logging context to check the user signed in or not
    for signin or login here is the guildliens
    GUIDLIENS FOR LOGGING CHECK
    {logging}
    IMPORTANT: If usr is signed in do not ask questions for signing like email, name, mobile number
    after checking the user's logging status you will start the conversation witht the user, here is the detaild flow of the conversation, you have to be static as it is,
    {task}

    for the conversation refference here are some basic examples to intract with the user,
    {sample_conversations}

    REMEMBER IF YOU DO NOT GET ANY PROPERTIES IN THE PROPERTY CONTEXT, YOU WILL ANSWER I HAVE NOT FOUND ANY PROPERTY LISTED HERE, DO YOU WANT TO SEE ANY OTHER LOCATION IN THE SAME BUDGET?
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
        # raise ValueError(f"Invalid JSON format in response: {assistant_response}")
        return(f"responsee:{assistant_response}, properties:[]")
    except Exception as e:
        return  (f"responsee:{assistant_response}, properties:[]")
    
    # Save the generated answer to MongoDB chat history
    summary=create_summary(email)
    save_message_to_mongo(user_input,assistant_response,email,chat_history_collection,summary,ip,user_name,user_id)
    return json_data



@handle_exceptions
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