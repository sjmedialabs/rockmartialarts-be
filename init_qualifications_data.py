#!/usr/bin/env python3
import asyncio
import sys
from datetime import datetime

sys.path.insert(0, '/www/wwwroot/Marshalats-be')

async def init_qualifications():
    from pymongo import MongoClient
    from config import MONGODB_URL, DB_NAME
    
    client = MongoClient(MONGODB_URL)
    db = client[DB_NAME]
    collection = db['dropdown_options']
    
    # Qualifications
    qualifications = [
        {"value": "High School", "label": "High School", "is_active": True, "order": 1},
        {"value": "Intermediate", "label": "Intermediate/12th", "is_active": True, "order": 2},
        {"value": "Diploma", "label": "Diploma", "is_active": True, "order": 3},
        {"value": "Graduation", "label": "Graduation/Bachelor's", "is_active": True, "order": 4},
        {"value": "Post Graduation", "label": "Post Graduation/Master's", "is_active": True, "order": 5},
        {"value": "Doctorate", "label": "Doctorate/PhD", "is_active": True, "order": 6},
    ]
    
    # Delete existing qualifications
    collection.delete_many({"category": "qualifications"})
    
    # Insert qualifications
    for qual in qualifications:
        collection.insert_one({
            "category": "qualifications",
            **qual
        })
    
    print(f"✅ Added {len(qualifications)} qualifications")
    
    # Passing Years (current year back to 50 years)
    current_year = datetime.now().year
    years = []
    for i in range(51):  # 0 to 50 years back
        year = current_year - i
        years.append({
            "value": str(year),
            "label": str(year),
            "is_active": True,
            "order": i + 1
        })
    
    # Delete existing years
    collection.delete_many({"category": "passing_years"})
    
    # Insert years
    for year in years:
        collection.insert_one({
            "category": "passing_years",
            **year
        })
    
    print(f"✅ Added {len(years)} passing years")
    client.close()

if __name__ == "__main__":
    asyncio.run(init_qualifications())
