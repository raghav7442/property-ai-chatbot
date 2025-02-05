from bson import ObjectId, json_util
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

# Function to fetch property metadata for multiple meta_ids
def get_property_metadata(meta_ids):
    try:
        if not isinstance(meta_ids, list) or not all(ObjectId.is_valid(meta_id) for meta_id in meta_ids):
            raise ValueError("meta_ids must be a list of valid ObjectIds.")

        pipeline = [
            {"$match": {"_id": {"$in": [ObjectId(meta_id) for meta_id in meta_ids]}}},
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
                        {
                            "$project": {
                                "_id": 1,
                                "title": 1,
                                "address": 1,
                                "property_owner": 1,
                                "longitude": 1,
                                "latitude": 1,
                                "pin_code": 1,
                                "project_developer": 1,
                                "parking_area_counting": 1,
                                "car_places_counting": 1,
                                "construction_status": 1,
                                "is_leasehold": 1,
                                "lease_year": 1,
                                "is_feature_property": 1,
                                "blocks": 1,
                                "unit_mix_breakdown": 1,
                                "schematic": 1,
                            }
                        }
                    ],
                    "as": "propertyDetails",
                }
            },
             
            {"$unwind": {"path": "$propertyDetails", "preserveNullAndEmptyArrays": True}},
              {
                "$lookup": {
                    "from": "images",
                    "localField": "propertyDetails._id",
                    "foreignField": "recordId",  
                    "as": "propertyDetails.images",
                }
            },
            {
                "$lookup": {
                    "from": "propertyowners",
                    "localField": "propertyDetails.property_owner",
                    "foreignField": "_id",
                    "pipeline": [
                        {
                            "$project": {
                                "_id": 0,
                                "fname": 1,
                                "lname": 1,
                                "email": 1,
                                "description": 1,
                                "country": 1,
                                "state": 1,
                                "city": 1,
                                "pin_code": 1,
                                "mobile": 1,
                                "gender": 1,
                            }
                        }
                    ],
                    "as": "propertyDetails.property_owner",
                }
            },
            {"$unwind": {"path": "$propertyDetails.property_owner", "preserveNullAndEmptyArrays": True}},
            {"$project": {"embedding": 0}},
        ]

        logging.info("Executing aggregation pipeline for multiple meta_ids.")
        results = list(property_metadata_collection.aggregate(pipeline))

        # Group by property_id and format the results
        grouped_properties = {}
        for item in results:
            property_details = item.get("propertyDetails", {})
            if property_details:
                property_id = str(property_details["_id"])
                if property_id not in grouped_properties:
                    grouped_properties[property_id] = {
                        "property_id": property_id,
                        "details": {
                            "title": property_details.get("title"),
                            "address": property_details.get("address"),
                            "property_owner": property_details.get("property_owner"),
                            "location": {
                                "longitude": property_details.get("longitude"),
                                "latitude": property_details.get("latitude"),
                                "coordinates": [
                                    property_details.get("longitude"),
                                    property_details.get("latitude"),
                                ],
                                "type": "Point",
                            },
                            "pin_code": property_details.get("pin_code"),
                            "project_developer": property_details.get("project_developer"),
                            "parking_area_counting": property_details.get("parking_area_counting"),
                            "car_places_counting": property_details.get("car_places_counting"),
                            "construction_status": property_details.get("construction_status"),
                            "is_leasehold": property_details.get("is_leasehold"),
                            "lease_year": property_details.get("lease_year"),
                            "is_feature_property": property_details.get("is_feature_property"),
                            "blocks": property_details.get("blocks"),
                            "unit_mix_breakdown": property_details.get("unit_mix_breakdown"),
                            "schematic": property_details.get("schematic"),
                        },
                        "meta_data": [],
                    }
                # Append metadata to the property
                item["_id"] = str(item["_id"])
                grouped_properties[property_id]["meta_data"].append(item)

        logging.info(f"Retrieved metadata for {len(grouped_properties)} properties.")
        return {"properties": list(grouped_properties.values())}

    except ValueError as ve:
        logging.error(f"Validation error: {ve}")
        return {"error": str(ve)}

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return {"error": "An unexpected error occurred. Please check the logs for details."}

# Example usage
if __name__ == "__main__":
    meta_ids = ["678e5e0cda8481dd0faa68a1", "678e40d8536510ee622e30ec"]
    result = get_property_metadata(meta_ids)
    if "error" in result:
        logging.error(f"Failed to fetch property metadata: {result['error']}")
    else:
        logging.info("Property metadata retrieved successfully.")
        print(json_util.dumps(result, indent=4))
