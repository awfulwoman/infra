from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime

from models import Group, GroupCreate, GroupResponse, UserInDB
from services import FileStorage, calculate_balances
from routers.auth import get_current_user_from_token, get_storage

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


@router.get("", response_model=List[Group])
async def list_groups(
    current_user: UserInDB = Depends(get_current_user_from_token),
    storage: FileStorage = Depends(get_storage),
):
    """List all groups."""
    groups = storage.get_groups()
    # Filter to groups where user is a member
    user_groups = [g for g in groups if current_user.id in g.get("members", [])]
    return user_groups


@router.post("", response_model=Group, status_code=status.HTTP_201_CREATED)
async def create_group(
    group: GroupCreate,
    current_user: UserInDB = Depends(get_current_user_from_token),
    storage: FileStorage = Depends(get_storage),
):
    """Create a new group."""
    # Ensure current user is in members list
    if current_user.id not in group.members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Creator must be a member of the group",
        )

    # Validate all members exist
    for member_id in group.members:
        user_data = storage.get_user_by_id(member_id)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {member_id} not found",
            )

    new_group = Group(**group.model_dump())
    group_dict = new_group.model_dump()
    storage.create_group(group_dict)

    # Publish MQTT discovery
    from main import mqtt_publisher

    if mqtt_publisher and mqtt_publisher.enabled:
        members_map = {}
        for member_id in new_group.members:
            user_data = storage.get_user_by_id(member_id)
            if user_data:
                members_map[member_id] = user_data["display_name"]

        mqtt_publisher.publish_discovery(
            group_id=new_group.id,
            group_name=new_group.name,
            members=members_map,
            currency="GBP",
        )

        # Publish initial zero balances
        zero_balances = {member_id: 0.0 for member_id in new_group.members}
        mqtt_publisher.publish_state(new_group.id, zero_balances)

    return new_group


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user: UserInDB = Depends(get_current_user_from_token),
    storage: FileStorage = Depends(get_storage),
):
    """Get group details with calculated balances."""
    group_data = storage.get_group(group_id)
    if not group_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    group = Group(**group_data)

    # Check user is a member
    if current_user.id not in group.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # Calculate balances
    transactions = storage.get_transactions(group_id)
    balances = calculate_balances(transactions, group.members)

    return GroupResponse(**group.model_dump(), balances=balances)
