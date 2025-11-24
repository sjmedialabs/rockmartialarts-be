from pymongo import MongoClient
from datetime import datetime

MONGO_URL = "mongodb+srv://rockmartialarts:rockmartialarts123@rockmartialarts.e3zwlzg.mongodb.net/marshalats?retryWrites=true&w=majority"

client = MongoClient(MONGO_URL)
db = client['marshalats']
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

collection.delete_many({"category": "qualifications"})
for qual in qualifications:
    collection.insert_one({"category": "qualifications", **qual})
print(f"✅ Added {len(qualifications)} qualifications")

# Passing Years
current_year = datetime.now().year
years = []
for i in range(51):
    year = current_year - i
    years.append({"value": str(year), "label": str(year), "is_active": True, "order": i + 1})

collection.delete_many({"category": "passing_years"})
for year in years:
    collection.insert_one({"category": "passing_years", **year})
print(f"✅ Added {len(years)} passing years")

client.close()
print("🎉 Done!")
