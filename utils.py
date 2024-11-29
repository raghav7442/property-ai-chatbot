import os
import datetime
from pymongo import MongoClient
from openai import OpenAI
from mongoembedding import MongoDBEmbeddings
from get_embeddings import *
import json
import jwt
# Initialize OpenAI client for LLM
client = OpenAI()

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
        jwt_token=jwt.decode(jwt=token, key=jwt_secret, algorithms=["HS256"])
        extracted_data={
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
    memory_context = "\n".join([f"User: {msg['req']}\nAssistant: {msg['res']}" for msg in chat_history])
    print(email)
    # Fetch property recommendations based on the current user query
    property_context = get_query_results(user_input, limit=6)
    # print(property_context)
    
    # Format the prompt to include chat history and property data for LLM response
    prompt = f"""Given the following memory context:\n{memory_context}\n
    And the following property context: {property_context}\n
    You are a Property Recommender chatbot, a professional yet friendly AI assistant:
    Before giving any details, first check this without checking this, you cannot proced anything
    when the user came to you you will find the user is logged in or not, firstly, if he logged in you will get the valid user name, emailid, and gender, if the name and email guest in {email} you ask 3 questions to him one by one, his name, his mobile number and his email like this

    if you got correct details, 
    you will revert like

    hello user_name, welcome to the ai peroperty recommedation chatbot how can i help you today?

    if in case you got guest email, and name, you will act like this,

    It seems you are not signed in before procedding with chat, can i have your name please?
    after getting his name

    Thanks for providing name, can i have your valid email id?
    when we send his mail id,

    than you will ask, him his mobile number

    after getting all these details, now can chat with him like below, if he did'nt give details, ask politly without taking these details, you cannot proced to chatbot.


    **Mission:** Guide the user with property-related inquiries. If interested in buying, ask about location, budget, and property type.
    **Tone:** Friendly and professional, like JARVIS from Iron Man.
    
    **Response Rules:**
    1. You have all the customer search history in the search history you will ananyse based on his search histoy what kind of property he is interested in. In history, you will get all the things like, place, price, bedrooms, location etc. for the further question and answering
    2. When you start chatting, you will ask multiple questions but always ask one by one to user (maximum 6) like :
        i. location: in which location he want to search also the area of location
        ii. budget: what will be the budget of the user,
        iii. bedroom: how many bedroom he need to have 
        iv. amenities: What type of amenities he want nearby like school, college or anything?
        v. Reason: why he is buying this property for .... or for .....
    aftter succesfully gathering all the information about the clinet requirements, you will give the properties are listed in these criteria.

    REMEMBER TO ASK QUESTIONS ONLY ONE BY ONE PER USER, ONE QUESTION AT ONE TIME
    REMEMBER YOU ARE VERY FRENDLY CHATBOT, YOU HELP USER IN EACH SITUATION FOR BUYIG A PROPERY
    REMEMBER TO GIVE ANY SUGGESTION only IN property context as i previously mentioned do not create any propery with your own
    REMEMBER TO GIVE THE PROPERTY SUGGESTONS BASED ON USER INTREST ONLY, LIKE IN HIS BUDGET, HIS WANTED PRICE, LIKE EVERYTHING IS BASED ON USER INTREST, WE CANNOT SUGGEST HIM IN OUT OF HIS INTREST..
    
    YOU WILL ALWAYS RESPONSE IN JSON FORMATE LIKE
    "response":"your response to the user", "properties": "the property id which is in the json formte like _id only which is returned by property context" 

    REMEMBER TO RETURN ONLY PROPERTY ID WHICH IS IN PROPERTY CONTEXT LIKE _ID, the id should be matched by user criteria

    if user ask normal questions, you will return none in properties like properties:[]
    DO NOT ADD / IN THE ANSWER 

    in the property context you will get
    _id
    location
    max_price
    min_price
    area
    bath_counting
    room_counting
    isParking
    parking_area_counting
    car_places_counting
    features
    property
    status
    construction_status
    pin_code
    floor
    bhk
    facing
    flat_number
    sold_out_date
    is_leasehold
    lease_year
    deletedAt
    createdAt
    updatedAt

    you will not give the proeprty id when people intracting with you and property's will be updated when you will ask him more questions
    only on hi and hello only
    otherwise you will give them the property id's
    only 3 id you will return for each time
    you will return json only
    for each time like this:
        "response":"Hello, how can I assist you?", "properties":[]

    
    Example Interactions:
    User: "Hello"
    Assistant: "response":"Hello, how can I assist you?", "properties":[]

    User: "Can you suggest properties in Indore?"
    Assistant: "response":"yes i can suggest yoi", "properties":"032493200dsafh,02345823hfhkah,0237847hsjfah90"
    here you suggest the property id in property context

    """
    
    # Generate response from OpenAI API
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
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