from bson import ObjectId
from pymongo import MongoClient
import os
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

# Connect to the MongoDB client
uri = os.getenv("MONGO_URI")
client = MongoClient(uri)
db = client[os.getenv("DB_NAME")]

# Replace 'your_collection_name' with the collection you are querying
property_metadata_collection = db[os.getenv("COLLECTION_NAME")]

# Function to fetch property metadata
def get_property_metadata(meta_id):
    pipeline = [
    {"$match": {"_id": ObjectId(meta_id)}},
    {
        "$lookup": {
            "from": "images",
            "let": {"metaId": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$eq": ["$recordId", "$$metaId"]}}},
                {"$project": {"embedding": 0}},  # Exclude "embedding" from "images"
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
                {"$project": {"embedding": 0}}  # Exclude "embedding" from "properties"
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
    result = list(property_metadata_collection.aggregate(pipeline))
    return result

# Replace with the actual meta_id
# meta_id = "672a1e1b32fed2aad5917913"
# result = get_property_metadata(meta_id)
# print(result)
# filtered_data = [{k: v for k, v in item.items() if k != "embedding"} for item in result]
