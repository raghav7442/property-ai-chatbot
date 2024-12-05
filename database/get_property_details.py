from bson import ObjectId, json_util
from pymongo import MongoClient
import os
import logging
import json
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

# Function to normalize ObjectId to string
def normalize_objectids(data):
    if isinstance(data, list):
        return [normalize_objectids(item) for item in data]
    elif isinstance(data, dict):
        return {key: str(value) if isinstance(value, ObjectId) else normalize_objectids(value) for key, value in data.items()}
    return data

# Function to fetch property metadata for a single meta_id
def get_single_property_metadata(meta_id):
    try:
        if not ObjectId.is_valid(meta_id):
            raise ValueError(f"Invalid meta_id: {meta_id} is not a valid ObjectId.")

        pipeline = [
            {"$match": {"_id": ObjectId(meta_id)}},
            {
                "$lookup": {
                    "from": "images",
                    "let": {"metaId": "$_id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$recordId", "$$metaId"]}}},
                        {"$project": {"embedding": 0, "title": 0, "fileName": 0, "recordType": 0, "recordId": 0}},
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
                        {"$project": {"embedding": 0, "name": 0, "description": 0, "country": 0, "state": 0, "city": 0, "property_type": 0, "deletedAt": 0, "createdAt": 0, "updatedAt": 0, "full_address": 0, "deleted_at": 0}},
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
                        {"$project": {"embedding": 0}}
                    ],
                    "as": "propertyDetails.propertyOwnerDetails",
                }
            },
            {"$unwind": {"path": "$propertyDetails.propertyOwnerDetails", "preserveNullAndEmptyArrays": True}},
            {"$project": {"embedding": 0}},
        ]

        logging.info(f"Executing pipeline for meta_id: {meta_id}")
        result = list(property_metadata_collection.aggregate(pipeline))

        return normalize_objectids(result)

    except ValueError as ve:
        logging.error(f"Validation error: {ve}")
        return {"error": str(ve)}

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return {"error": "An unexpected error occurred. Please check the logs for details."}

# Function to fetch property metadata for multiple meta_ids
def get_property_metadata(meta_ids):
    try:
        if not isinstance(meta_ids, list):
            raise ValueError("meta_ids must be a list of ObjectIds.")

        all_results = []
        for meta_id in meta_ids:
            result = get_single_property_metadata(meta_id)
            if "error" not in result:
                all_results.extend(result)
            else:
                logging.warning(f"Skipping meta_id {meta_id} due to error: {result['error']}")

        logging.info(f"Retrieved metadata for {len(all_results)} records.")
        return all_results

    except ValueError as ve:
        logging.error(f"Validation error: {ve}")
        return {"error": str(ve)}

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return {"error": "An unexpected error occurred. Please check the logs for details."}

# Example usage
# if __name__ == "__main__":
#     meta_ids = ["673b27fe4483cd7d1a3df9fd", "623b27fe4483cd7d1a3df9fa"]
#     result = get_property_metadata(meta_ids)
#     if "error" in result:
#         logging.error(f"Failed to fetch property metadata: {result['error']}")
#     else:
#         logging.info("Property metadata retrieved successfully.")
#         print(json.dumps(result, indent=4))
