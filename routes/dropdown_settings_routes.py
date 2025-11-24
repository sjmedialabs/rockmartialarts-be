from fastapi import APIRouter, Depends, status
from typing import List
from controllers.dropdown_settings_controller import DropdownSettingsController
from models.dropdown_settings_models import (
    DropdownOption,
    DropdownCategoryUpdate
)
from models.user_models import UserRole
from utils.unified_auth import require_role_unified

router = APIRouter()

@router.get("", response_model=List[dict])
async def get_all_dropdown_categories(
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN]))
):
    """
    Get all dropdown categories
    
    - **Requires**: Super Admin authentication
    - **Returns**: List of all dropdown categories with their options
    """
    return await DropdownSettingsController.get_all_categories(current_user)

@router.get("/{category}", response_model=List[dict])
async def get_category_options(category: str):
    """
    Get options for a specific dropdown category (public endpoint)
    
    - **category**: Category name (e.g., 'countries', 'designations')
    - **Returns**: List of dropdown options for the category
    """
    return await DropdownSettingsController.get_category_options(category)

@router.put("/{category}", response_model=dict)
async def update_category_options(
    category: str,
    update_data: DropdownCategoryUpdate,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN]))
):
    """
    Update all options for a dropdown category
    
    - **Requires**: Super Admin authentication
    - **category**: Category name
    - **Body**: List of dropdown options
    - **Returns**: Updated category with options
    """
    return await DropdownSettingsController.update_category_options(
        category, update_data, current_user
    )

@router.post("/{category}/options", response_model=dict)
async def add_category_option(
    category: str,
    option: DropdownOption,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN]))
):
    """
    Add a single option to a dropdown category
    
    - **Requires**: Super Admin authentication
    - **category**: Category name
    - **Body**: Dropdown option to add
    - **Returns**: Updated category with new option
    """
    return await DropdownSettingsController.add_option(
        category, option, current_user
    )

@router.delete("/{category}/options/{value}", response_model=dict)
async def delete_category_option(
    category: str,
    value: str,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN]))
):
    """
    Delete an option from a dropdown category
    
    - **Requires**: Super Admin authentication
    - **category**: Category name
    - **value**: Option value to delete
    - **Returns**: Success message
    """
    return await DropdownSettingsController.delete_option(
        category, value, current_user
    )

@router.post("/{category}/reset", response_model=dict)
async def reset_category_to_defaults(
    category: str,
    current_user: dict = Depends(require_role_unified([UserRole.SUPER_ADMIN]))
):
    """
    Reset a dropdown category to default options
    
    - **Requires**: Super Admin authentication
    - **category**: Category name
    - **Returns**: Category with default options restored
    """
    return await DropdownSettingsController.reset_category(category, current_user)
