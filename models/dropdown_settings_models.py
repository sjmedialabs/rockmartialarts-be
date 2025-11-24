from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DropdownOption(BaseModel):
    """Model for a single dropdown option"""
    value: str = Field(..., description="The value of the option")
    label: str = Field(..., description="The display label for the option")
    is_active: bool = Field(default=True, description="Whether the option is active")
    order: Optional[int] = Field(default=None, description="Sort order")

class DropdownCategoryBase(BaseModel):
    """Base model for dropdown category"""
    category: str = Field(..., description="Category name (e.g., 'countries', 'designations')")
    options: List[DropdownOption] = Field(..., description="List of dropdown options")

class DropdownCategoryCreate(DropdownCategoryBase):
    """Model for creating a dropdown category"""
    pass

class DropdownCategoryUpdate(BaseModel):
    """Model for updating dropdown options"""
    options: List[DropdownOption] = Field(..., description="Updated list of options")

class DropdownCategoryResponse(DropdownCategoryBase):
    """Response model for dropdown category"""
    id: str = Field(..., description="Category ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
