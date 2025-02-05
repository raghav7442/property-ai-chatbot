from pymongo import MongoClient
import pandas as pd
from openai import OpenAI
import os
import threading

# MongoDB connection setup
def get_mongo_collection(collection_name):
    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    db = mongo_client[os.getenv("DB_NAME")]
    return db[collection_name]

# Generate embeddings for a given text
def generate_embedding(text):
    client = OpenAI()
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Process each document row by row
def generate_and_save_embeddings(collection_name):
    collection = get_mongo_collection(collection_name)
    cursor = collection.find()  # Fetch documents from MongoDB
    threads=[]
    updated_count = 0  # Counter for updated rows

    for document in cursor:
        threading.Thread(target=generate_embedding, args=(document,)).start()
        # Combine fields for embedding generation
        text = f"{document.get('name', '')} {document.get('description', '')}"
        
        # Generate embedding for the current document
        embedding = generate_embedding(text)
        
        # Update the document in MongoDB
        collection.update_one(
            {'_id': document['_id']},
            {"$set": {"embedding": embedding}}
        )
        
        updated_count += 1
        print(f"Updated document ID: {document['_id']}")

    return f"Embedding generation complete. Total documents updated: {updated_count}"
