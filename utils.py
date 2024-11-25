import os
import datetime
from pymongo import MongoClient
from openai import OpenAI
from mongoembedding import MongoDBEmbeddings
from get_embeddings import *
import json

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


def save_message_to_mongo(user_content, ai_content, email, collection):
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
        {"$push": {f"history": message}},
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
    chat_history = fetch_chat_history(email)
    memory_context = "\n".join([f"User: {msg['req']}\nAssistant: {msg['res']}" for msg in chat_history])
    
    # Fetch property recommendations based on the current user query
    property_context = get_query_results(user_input, limit=6)
    # print(property_context)
    
    # Format the prompt to include chat history and property data for LLM response
    prompt = f"""Given the following memory context:\n{memory_context}\n
    And the following property context: {property_context}\n
    You are a Property Recommender chatbot, a professional yet friendly AI assistant:
    
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
    # print(assistant_response["properties"])
    json_data = json.loads(assistant_response)
    # print(json_data)
    
    # Save the generated answer to MongoDB chat history
    save_message_to_mongo(user_input, assistant_response, email, chat_history_collection)
    return json_data
