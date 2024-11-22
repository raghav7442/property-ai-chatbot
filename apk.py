import os
from flask import Flask, jsonify, request, session
from dotenv import load_dotenv
from get_embeddings import *
import uuid
from flask_cors import CORS
from get_property_details import get_property_metadata
from utils import *


# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests
app.config.from_pyfile('config.py')  # Load configuration from a separate file
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')  # Set secret key from environment variable


# Route for health check to verify the service is running
@app.route('/', methods=['GET'])
def check():
    """API route to check if the service is up and running."""
    return jsonify({"status": "Service is running"}), 200


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
    email = data.get("email")
    question = data.get("question")
    
    # Validate 'question' parameter
    if not question:
        return jsonify({"error": "The 'question' field is required."}), 400

    # Handle guest users (if no email is provided)
    if not email or email == "" or email is None:
        if 'guest_session' not in session:
            session['guest_session'] = str(uuid.uuid4())  # Generate a unique session ID for the guest
        email = f"guest_{session['guest_session']}"

    # Generate response from LLM with memory and property context
    response = generate_answer(question, email)
    answer = response["response"]
    property_ids = response["properties"]
    properties_details = []

    # Fetch property details based on the property IDs
    for property_id in property_ids:
        detail = get_property_metadata(property_id)  # Fetch property details
        properties_details.append(detail)

    # Return response including answer and property details
    return jsonify({"response": answer, "property_details": properties_details})


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
    app.run(debug=True, port=5005, host='0.0.0.0')