import os
from flask import Flask, jsonify, request, session
from dotenv import load_dotenv
from get_embeddings import *
import uuid
from flask_cors import CORS
from get_property_details import get_property_metadata
from utils import *
from bson import ObjectId


# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
CORS(app)  
app.config.from_pyfile('config.py')  
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')  



# Route for health check to verify the service is running
@app.route('/', methods=['GET'])
def check():
    """API route to check if the service is up and running."""
    return jsonify({"status": "Service is running"}), 200


@app.route("/afford", methods=['POST'])
def affordablity_analysis():
    data = request.json

        # Validate input parameters
    max_price = data.get("max_price")
    min_price = data.get("min_price")
    property_area = data.get("property_area")
    location = data.get("location")


    query=f'can i get the properties with in max price {max_price}, min price {min_price} property area {property_area} '

    properties=(affordable(query,location))
    ids=properties["properties"]
    # print(properties[0][0])
    if len(ids)>0:
        print("inside if")
        full_property_id=get_property_metadata(ids) if ids else []
        
        
    # print(full_property_id)
        return full_property_id
    else:
        print("in ek")
        return properties


# Route to handle chat interaction
@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chat route for user interaction.
    - Accepts JSON input with 'email' and 'question'.
    - Generates a response considering the conversation history and property data.
    - Returns the generated response as JSON.
    """
    # Extract data from incoming JSON request
    data = request.json
    auth_token=data.get("auth")
    print(data)
    question = data.get("question")
    
    # Validate 'question' parameter
    if not isinstance(question, str) or len(question.strip()) == 0:
      return jsonify({"error": "Invalid 'question' format. Must be a non-empty string."}), 400
    if len(question) > 500:
        return jsonify({"error": "The 'question' field exceeds the maximum allowed length of 500 characters."}), 400


    try:
        auth = jwt_verify(auth_token)
    except ValueError as e:
         return jsonify({"error": f"Authentication failed: {str(e)}"}), 401
    
    # Handle guest users (if no email is provided)
    if not auth_token or not auth_token.get("email") or auth_token =="" or auth_token ==None: 
        if "guest_session" not in session:
            session["guest_session"] = str(uuid.uuid4())  
        auth = {
            "email": f"guest_{session['guest_session']}",
            "name": "Guest",
            "gender": "Unknown",  
        }

    # Generate response from LLM with memory and property context
    response = generate_answer(question, auth)
    answer = response["response"]
    # print(answer)
    property_ids = response["properties"]
    # print(property_ids)
    property = get_property_metadata(property_ids) if property_ids else []

    return jsonify({"response": answer, "property_details": property})


# Route to embed and save collection data
@app.route('/embed', methods=['POST'])
def embed_collection():
    # Get the collection name from the request JSON
    data = request.get_json()
    collection_name = data.get("collection_name")

    # Validate collection name
    if not collection_name:
        return jsonify({"error": "Collection name is required"}), 400

    # Generate and save embeddings for the specified collection
    result = generate_and_save_embeddings(collection_name)
    
    # Return success message with result
    return jsonify({"message": result})


# Run the Flask application on specified host and port
if __name__ == "__main__":
    app.run(debug=True, port=5006, host='0.0.0.0')