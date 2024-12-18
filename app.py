import os
from flask import Flask, jsonify, request, session, render_template
from dotenv import load_dotenv
from database.get_embeddings import *
import uuid
from flask_cors import CORS
from database.get_property_details import get_property_metadata
from utils.utils import *
from bson import ObjectId
from utils.exceptions import handle_exceptions


# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
# CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "https://property-ai-webapp-frontend.vercel.app/"]}})

app.config.from_pyfile('config.py')  
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')  

# Route for health check to verify the service is running
@app.route('/', methods=['GET'])
def check():
    """API route to check if the service is up and running."""
    return jsonify({"status": "Service is running"}), 200


@app.route('/form', methods=['GET'])
def home():
    return render_template('index.htm')


@handle_exceptions
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
        return jsonify({"properties":full_property_id})
    else:
        print("in ek")
        return properties


# Route to handle chat interaction
@handle_exceptions
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    auth_token = data.get("auth")
    ids = data.get("IP")
    question = data.get("question")

    # Validate the 'question' field
    if not isinstance(question, str) or len(question.strip()) == 0:
        return jsonify({"error": "Invalid 'question' format. Must be a non-empty string."}), 400
    if len(question) > 500:
        return jsonify({"error": "The 'question' field exceeds the maximum allowed length of 500 characters."}), 400

    # Check for 'auth' or fallback to 'ids'
    if not auth_token:  
        if not ids:  
            return jsonify({"error": "Missing required field 'ids' when 'auth' is not provided."}), 400
        auth = {
            "IP":f"{ids}",
            "id":"guest_id",
            "name": "Guest",
            "email": "Guest@gmail.com",
            "gender": "Unknown",
        }
    else:
        try:
            auth = jwt_verify(auth_token)  
        except ValueError as e:
            return jsonify({"error": f"Authentication failed: {str(e)}"}), 401

    try:
        # Generate response
        print(auth)
        response = generate_answer(question, auth)
        answer = response["response"]
        property_ids = response.get("properties", [])
        property_details = get_property_metadata(property_ids) if property_ids else []
        return jsonify({"response": answer, "property_details": property_details})
    except ValueError as e:
        return jsonify({"response": response, "property":[] }), 500


# Route to embed and save collection data
@handle_exceptions
@app.route('/embed', methods=['POST'])
def embed_collection():
    data = request.get_json()
    collection_name = data.get("collection_name")


    if not collection_name:
        return jsonify({"error": "Collection name is required"}), 400
    result = generate_and_save_embeddings(collection_name)

    return jsonify({"message": result})

@handle_exceptions
@app.route('/chat_history', methods=['GET'])
def get_chat_history():
    data = request.args
    ip_address = data.get("IP")
    email = data.get("email")
    
    # Fetch the chat history
    chats = fetch_chat_history(email, ip_address)
    for chat in chats:
            try:
                chat["res"] = json.loads(chat["res"]) 
                if isinstance(chat.get("res"), dict):
                    properties = chat["res"].get("properties", [])
                    if properties:
                        chat["res"]["properties"] = get_property_metadata(properties) if properties else []
            except json.JSONDecodeError:
                chat["res"] = {"error": "Invalid JSON format"}
    return jsonify(chats)

# Run the Flask application on specified host and port
if __name__ == "__main__":
    app.run(debug=True, port=5006, host='0.0.0.0')