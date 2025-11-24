from fastapi import HTTPException, status
from typing import List, Dict, Any
from datetime import datetime
from utils.database import get_db, serialize_doc
from models.dropdown_settings_models import (
    DropdownOption,
    DropdownCategoryCreate,
    DropdownCategoryUpdate,
    DropdownCategoryResponse
)

class DropdownSettingsController:
    """Controller for managing dropdown settings"""
    
    COLLECTION_NAME = "dropdown_settings"
    
    VALID_CATEGORIES = [
        "countries",
        "designations",
        "specializations",
        "experience_ranges",
        "genders",
        "emergency_relations",
        "banks",
        "locations",
        "difficulty_levels",
        "course_durations",
        "qualifications",
        "passing_years"
    ]
    
    DEFAULT_OPTIONS = {
        "countries": [
            {"value": "India", "label": "India", "is_active": True, "order": 1},
            {"value": "USA", "label": "USA", "is_active": True, "order": 2},
            {"value": "UK", "label": "UK", "is_active": True, "order": 3},
            {"value": "Canada", "label": "Canada", "is_active": True, "order": 4},
            {"value": "Australia", "label": "Australia", "is_active": True, "order": 5},
        ],
        "designations": [
            {"value": "Senior Coach", "label": "Senior Coach", "is_active": True, "order": 1},
            {"value": "Coach Instructor", "label": "Coach Instructor", "is_active": True, "order": 2},
            {"value": "Senior Instructor", "label": "Senior Instructor", "is_active": True, "order": 3},
            {"value": "Instructor", "label": "Instructor", "is_active": True, "order": 4},
            {"value": "Assistant Instructor", "label": "Assistant Instructor", "is_active": True, "order": 5},
            {"value": "Head Coach", "label": "Head Coach", "is_active": True, "order": 6},
            {"value": "Coach", "label": "Coach", "is_active": True, "order": 7},
            {"value": "Assistant Coach", "label": "Assistant Coach", "is_active": True, "order": 8},
        ],
        "specializations": [
            {"value": "Taekwondo", "label": "Taekwondo", "is_active": True, "order": 1},
            {"value": "Karate", "label": "Karate", "is_active": True, "order": 2},
            {"value": "Kung Fu", "label": "Kung Fu", "is_active": True, "order": 3},
            {"value": "Kick Boxing", "label": "Kick Boxing", "is_active": True, "order": 4},
            {"value": "Self Defense", "label": "Self Defense", "is_active": True, "order": 5},
            {"value": "Mixed Martial Arts", "label": "Mixed Martial Arts", "is_active": True, "order": 6},
            {"value": "Judo", "label": "Judo", "is_active": True, "order": 7},
            {"value": "Jiu-Jitsu", "label": "Jiu-Jitsu", "is_active": True, "order": 8},
            {"value": "Muay Thai", "label": "Muay Thai", "is_active": True, "order": 9},
            {"value": "Boxing", "label": "Boxing", "is_active": True, "order": 10},
            {"value": "Kuchipudi Dance", "label": "Kuchipudi Dance", "is_active": True, "order": 11},
            {"value": "Bharatanatyam", "label": "Bharatanatyam", "is_active": True, "order": 12},
            {"value": "Gymnastics", "label": "Gymnastics", "is_active": True, "order": 13},
            {"value": "Yoga", "label": "Yoga", "is_active": True, "order": 14},
        ],
        "experience_ranges": [
            {"value": "0-1 years", "label": "0-1 years", "is_active": True, "order": 1},
            {"value": "1-3 years", "label": "1-3 years", "is_active": True, "order": 2},
            {"value": "3-5 years", "label": "3-5 years", "is_active": True, "order": 3},
            {"value": "5-10 years", "label": "5-10 years", "is_active": True, "order": 4},
            {"value": "10+ years", "label": "10+ years", "is_active": True, "order": 5},
        ],
        "genders": [
            {"value": "male", "label": "Male", "is_active": True, "order": 1},
            {"value": "female", "label": "Female", "is_active": True, "order": 2},
            {"value": "other", "label": "Other", "is_active": True, "order": 3},
        ],
        "emergency_relations": [
            {"value": "spouse", "label": "Spouse", "is_active": True, "order": 1},
            {"value": "parent", "label": "Parent", "is_active": True, "order": 2},
            {"value": "sibling", "label": "Sibling", "is_active": True, "order": 3},
            {"value": "friend", "label": "Friend", "is_active": True, "order": 4},
            {"value": "other", "label": "Other", "is_active": True, "order": 5},
        ],
        "banks": [
            {"value": "State Bank of India", "label": "State Bank of India", "is_active": True, "order": 1},
            {"value": "HDFC Bank", "label": "HDFC Bank", "is_active": True, "order": 2},
            {"value": "ICICI Bank", "label": "ICICI Bank", "is_active": True, "order": 3},
            {"value": "Axis Bank", "label": "Axis Bank", "is_active": True, "order": 4},
            {"value": "Punjab National Bank", "label": "Punjab National Bank", "is_active": True, "order": 5},
            {"value": "Bank of Baroda", "label": "Bank of Baroda", "is_active": True, "order": 6},
            {"value": "Canara Bank", "label": "Canara Bank", "is_active": True, "order": 7},
            {"value": "Union Bank of India", "label": "Union Bank of India", "is_active": True, "order": 8},
            {"value": "Yes Bank", "label": "Yes Bank", "is_active": True, "order": 9},
        ],
        "locations": [
            {"value": "Hyderabad", "label": "Hyderabad", "is_active": True, "order": 1},
            {"value": "Mumbai", "label": "Mumbai", "is_active": True, "order": 2},
            {"value": "Delhi", "label": "Delhi", "is_active": True, "order": 3},
            {"value": "Bangalore", "label": "Bangalore", "is_active": True, "order": 4},
            {"value": "Chennai", "label": "Chennai", "is_active": True, "order": 5},
            {"value": "Kolkata", "label": "Kolkata", "is_active": True, "order": 6},
            {"value": "Pune", "label": "Pune", "is_active": True, "order": 7},
        ],
        "difficulty_levels": [
            {"value": "Beginner", "label": "Beginner", "is_active": True, "order": 1},
            {"value": "Intermediate", "label": "Intermediate", "is_active": True, "order": 2},
            {"value": "Advanced", "label": "Advanced", "is_active": True, "order": 3},
            {"value": "Expert", "label": "Expert", "is_active": True, "order": 4},
        ],
        "course_durations": [
            {"value": "1 month", "label": "1 month", "is_active": True, "order": 1},
            {"value": "2 months", "label": "2 months", "is_active": True, "order": 2},
            {"value": "3 months", "label": "3 months", "is_active": True, "order": 3},
            {"value": "6 months", "label": "6 months", "is_active": True, "order": 4},
            {"value": "1 year", "label": "1 year", "is_active": True, "order": 5},
            {"value": "2 years", "label": "2 years", "is_active": True, "order": 6},
        ],
        "qualifications": [
            {"value": "High School", "label": "High School", "is_active": True, "order": 1},
            {"value": "Bachelor's Degree", "label": "Bachelor's Degree", "is_active": True, "order": 2},
            {"value": "Master's Degree", "label": "Master's Degree", "is_active": True, "order": 3},
            {"value": "PhD", "label": "PhD", "is_active": True, "order": 4},
            {"value": "Diploma", "label": "Diploma", "is_active": True, "order": 5},
            {"value": "Certificate", "label": "Certificate", "is_active": True, "order": 6},
        ],
        "passing_years": [
            {"value": "2024", "label": "2024", "is_active": True, "order": 1},
            {"value": "2023", "label": "2023", "is_active": True, "order": 2},
            {"value": "2022", "label": "2022", "is_active": True, "order": 3},
            {"value": "2021", "label": "2021", "is_active": True, "order": 4},
            {"value": "2020", "label": "2020", "is_active": True, "order": 5},
            {"value": "2019", "label": "2019", "is_active": True, "order": 6},
            {"value": "2018", "label": "2018", "is_active": True, "order": 7},
            {"value": "2017", "label": "2017", "is_active": True, "order": 8},
            {"value": "2016", "label": "2016", "is_active": True, "order": 9},
            {"value": "2015", "label": "2015", "is_active": True, "order": 10},
        ],
    }
    
    @classmethod
    def _validate_category(cls, category: str):
        """Validate if category is allowed"""
        if category not in cls.VALID_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category. Must be one of: {', '.join(cls.VALID_CATEGORIES)}"
            )
    
    @classmethod
    async def get_all_categories(cls, current_user: dict) -> List[Dict[str, Any]]:
        """Get all dropdown categories"""
        db = get_db()
        collection = db[cls.COLLECTION_NAME]
        
        categories = await collection.find().to_list(length=100)
        return [serialize_doc(cat) for cat in categories]
    
    @classmethod
    async def get_category_options(cls, category: str) -> List[Dict[str, Any]]:
        """Get options for a specific category (public endpoint)"""
        cls._validate_category(category)
        
        db = get_db()
        collection = db[cls.COLLECTION_NAME]
        
        doc = await collection.find_one({"category": category})
        
        if doc:
            return doc.get("options", [])
        else:
            # Return default options if not found
            return cls.DEFAULT_OPTIONS.get(category, [])
    
    @classmethod
    async def update_category_options(
        cls,
        category: str,
        update_data: DropdownCategoryUpdate,
        current_user: dict
    ) -> Dict[str, Any]:
        """Update options for a category"""
        cls._validate_category(category)
        
        db = get_db()
        collection = db[cls.COLLECTION_NAME]
        
        # Convert options to dict
        options_data = [opt.dict() for opt in update_data.options]
        
        # Update or insert
        now = datetime.utcnow()
        result = await collection.find_one_and_update(
            {"category": category},
            {
                "$set": {
                    "options": options_data,
                    "updated_at": now
                },
                "$setOnInsert": {
                    "category": category,
                    "created_at": now
                }
            },
            upsert=True,
            return_document=True
        )
        
        return serialize_doc(result)
    
    @classmethod
    async def add_option(
        cls,
        category: str,
        option: DropdownOption,
        current_user: dict
    ) -> Dict[str, Any]:
        """Add a single option to a category"""
        cls._validate_category(category)
        
        db = get_db()
        collection = db[cls.COLLECTION_NAME]
        
        # Check if option value already exists
        doc = await collection.find_one({
            "category": category,
            "options.value": option.value
        })
        
        if doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Option with value '{option.value}' already exists"
            )
        
        # Add option
        now = datetime.utcnow()
        result = await collection.find_one_and_update(
            {"category": category},
            {
                "$push": {"options": option.dict()},
                "$set": {"updated_at": now},
                "$setOnInsert": {
                    "category": category,
                    "created_at": now
                }
            },
            upsert=True,
            return_document=True
        )
        
        return serialize_doc(result)
    
    @classmethod
    async def delete_option(
        cls,
        category: str,
        value: str,
        current_user: dict
    ) -> Dict[str, str]:
        """Delete an option from a category"""
        cls._validate_category(category)
        
        db = get_db()
        collection = db[cls.COLLECTION_NAME]
        
        # Remove the option
        result = await collection.update_one(
            {"category": category},
            {
                "$pull": {"options": {"value": value}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Option with value '{value}' not found in category '{category}'"
            )
        
        return {"message": f"Option '{value}' deleted successfully"}
    
    @classmethod
    async def reset_category(
        cls,
        category: str,
        current_user: dict
    ) -> Dict[str, Any]:
        """Reset a category to default options"""
        cls._validate_category(category)
        
        db = get_db()
        collection = db[cls.COLLECTION_NAME]
        
        default_options = cls.DEFAULT_OPTIONS.get(category, [])
        now = datetime.utcnow()
        
        result = await collection.find_one_and_update(
            {"category": category},
            {
                "$set": {
                    "options": default_options,
                    "updated_at": now
                },
                "$setOnInsert": {
                    "category": category,
                    "created_at": now
                }
            },
            upsert=True,
            return_document=True
        )
        
        return serialize_doc(result)
