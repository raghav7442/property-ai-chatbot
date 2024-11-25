from bson import ObjectId
from pymongo import MongoClient
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Validate environment variables
required_env_vars = ["MONGO_URI", "DB_NAME", "COLLECTION_NAME"]
for var in required_env_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")

# Connect to the MongoDB client
uri = os.getenv("MONGO_URI")
client = MongoClient(uri)
db = client[os.getenv("DB_NAME")]

# Replace 'your_collection_name' with the collection you are querying
property_metadata_collection = db[os.getenv("COLLECTION_NAME")]

# Function to fetch property metadata
def get_property_metadata(meta_id):
    try:
        # Validate meta_id
        if not ObjectId.is_valid(meta_id):
            raise ValueError("Invalid meta_id: Must be a valid ObjectId.")

        # Define the aggregation pipeline
        pipeline = [
            {"$match": {"_id": ObjectId(meta_id)}},
            {
                "$lookup": {
                    "from": "images",
                    "let": {"metaId": "$_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$recordId", "$$metaId"]}}},
                        {"$project": {"embedding": 0, "title": 0, "fileName": 0, "recordType": 0, "recordId": 0}},  # Exclude "embedding" from "images"
                    ],
                    "as": "images",
                }
            },
            {
                "$lookup": {
                    "from": "properties",
                    "localField": "property",
                    "foreignField": "_id",
                    "pipeline": [
                        {"$project": {"embedding": 0, "name": 0, "description": 0, "country": 0, "state": 0, "city": 0, "property_type": 0, "deletedAt": 0, "createdAt": 0, "updatedAt": 0, "full_address": 0, "deleted_at": 0}},  # Exclude "embedding" from "properties"
                    ],
                    "as": "propertyDetails",
                }
            },
            {"$unwind": {"path": "$propertyDetails", "preserveNullAndEmptyArrays": True}},
            {
                "$lookup": {
                    "from": "propertyowners",
                    "localField": "propertyDetails.property_owner",
                    "foreignField": "_id",
                    "pipeline": [
                        {"$project": {"embedding": 0}}  # Exclude "embedding" from "propertyowners"
                    ],
                    "as": "propertyDetails.propertyOwnerDetails",
                }
            },
            {"$unwind": {"path": "$propertyDetails.propertyOwnerDetails", "preserveNullAndEmptyArrays": True}},
            # Exclude "embedding" from the main collection
            {
                "$project": {
                    "embedding": 0,  # Exclude "embedding" field from the root document
                }
            },
        ]

        # Execute the aggregation pipeline
        logging.info(f"Executing pipeline for meta_id: {meta_id}")
        result = list(property_metadata_collection.aggregate(pipeline))
        logging.info(f"Pipeline executed successfully. Retrieved {len(result)} records.")
        return result

    except ValueError as ve:
        logging.error(f"Validation error: {ve}")
        return {"error": str(ve)}

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return {"error": "An unexpected error occurred. Please check the logs for details."}

# Example usage
if __name__ == "__main__":
    # Replace with the actual meta_id
    meta_id = "673b27fe4483cd7d1a3df9fd"
    result = get_property_metadata(meta_id)
    if "error" in result:
        logging.error(f"Failed to fetch property metadata: {result['error']}")
    else:
        # Process the result if needed
        logging.info("Property metadata retrieved successfully.")
        print(result)
