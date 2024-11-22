from bson import ObjectId
from pymongo import MongoClient
import os

# Connect to the MongoDB client
client = MongoClient(os.getenv("MONGO_URI"))  
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
                    {"$match": {"$expr": {"$eq": ["$recordId", "$$metaId"]}}}
                ],
                "as": "images",
            }
        },
        {
            "$lookup": {
                "from": "properties",
                "localField": "property",
                "foreignField": "_id",
                "as": "propertyDetails",
            }
        },
        {"$unwind": {"path": "$propertyDetails", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "propertyowners",
                "localField": "propertyDetails.property_owner",
                "foreignField": "_id",
                "as": "propertyDetails.propertyOwnerDetails",
            }
        },
        {
            "$unwind": {
                "path": "$propertyDetails.propertyOwnerDetails",
                "preserveNullAndEmptyArrays": True,
            }
        },
    ]
    
    # Execute the aggregation pipeline
    result = list(property_metadata_collection.aggregate(pipeline))
    return result

# Replace with the actual meta_id
meta_id = "your_meta_id_here"
result = get_property_metadata(meta_id)
print(result)
