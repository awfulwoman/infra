from fastapi import APIRouter, Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from datetime import datetime

from models import Transaction, TransactionCreate, TransactionUpdate, UserInDB
from services import FileStorage, calculate_split, calculate_balances
from routers.auth import get_storage

router = APIRouter(prefix="/api/v1", tags=["transactions"])


async def get_current_user(
    storage: FileStorage = Depends(get_storage),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    session_token: str = Cookie(None),
) -> UserInDB:
    """Get current user from either token or session."""
    # Try session first (for web)
    if session_token:
        user_data = storage.get_user_by_token(session_token)
        if user_data:
            return UserInDB(**user_data)

    # Try Bearer token (for API)
    if credentials:
        user_data = storage.get_user_by_token(credentials.credentials)
        if user_data:
            return UserInDB(**user_data)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def _publish_balance_update(storage: FileStorage, group_id: str):
    """Helper to publish updated balances to MQTT."""
    from main import mqtt_publisher

    if mqtt_publisher and mqtt_publisher.enabled:
        group_data = storage.get_group(group_id)
        if group_data:
            transactions = storage.get_transactions(group_id)
            balances = calculate_balances(transactions, group_data["members"])
            mqtt_publisher.publish_state(group_id, balances)


@router.get("/groups/{group_id}/transactions", response_model=List[Transaction])
async def list_transactions(
    group_id: str,
    current_user: UserInDB = Depends(get_current_user),
    storage: FileStorage = Depends(get_storage),
):
    """List all transactions for a group."""
    group_data = storage.get_group(group_id)
    if not group_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # Check user is a member
    if current_user.id not in group_data.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    transactions = storage.get_transactions(group_id)
    return transactions


@router.post("/groups/{group_id}/transactions", response_model=Transaction, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    group_id: str,
    transaction: TransactionCreate,
    current_user: UserInDB = Depends(get_current_user),
    storage: FileStorage = Depends(get_storage),
):
    """Create a new transaction."""
    group_data = storage.get_group(group_id)
    if not group_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # Check user is a member
    if current_user.id not in group_data.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # Validate payer is a member
    if transaction.payer_id not in group_data.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payer must be a member of the group",
        )

    # Validate payment type
    if transaction.split_type == "payment":
        if not transaction.recipient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="recipient_id required for payment type",
            )
        if transaction.recipient_id not in group_data.get("members", []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recipient must be a member of the group",
            )
        if transaction.recipient_id == transaction.payer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot pay yourself",
            )

    # Calculate split
    split_details = calculate_split(
        transaction.amount,
        group_data["members"],
        transaction.split_type,
        transaction.recipient_id,
    )

    # Create transaction
    new_transaction = Transaction(
        **transaction.model_dump(),
        split_details=split_details,
        created_by=current_user.id,
    )

    tx_dict = new_transaction.model_dump()
    storage.create_transaction(group_id, tx_dict)

    # Update group timestamp
    group_data["updated_at"] = datetime.utcnow().isoformat()
    storage.update_group(group_id, group_data)

    # Publish balance update to MQTT
    _publish_balance_update(storage, group_id)

    return new_transaction


@router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: str,
    transaction_update: TransactionUpdate,
    current_user: UserInDB = Depends(get_current_user),
    storage: FileStorage = Depends(get_storage),
):
    """Update a transaction."""
    # Find transaction across all groups
    groups = storage.get_groups()
    tx_data = None
    group_id = None

    for group in groups:
        tx = storage.get_transaction(group["id"], transaction_id)
        if tx:
            tx_data = tx
            group_id = group["id"]
            break

    if not tx_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Check user is a member of the group
    group_data = storage.get_group(group_id)
    if current_user.id not in group_data.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # Update fields
    if transaction_update.amount is not None:
        tx_data["amount"] = transaction_update.amount
        # Recalculate split
        tx_data["split_details"] = calculate_split(
            transaction_update.amount,
            group_data["members"],
            tx_data["split_type"],
            tx_data.get("recipient_id"),
        )

    if transaction_update.description is not None:
        tx_data["description"] = transaction_update.description

    if transaction_update.payer_id is not None:
        if transaction_update.payer_id not in group_data.get("members", []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payer must be a member of the group",
            )
        tx_data["payer_id"] = transaction_update.payer_id

    tx_data["updated_at"] = datetime.utcnow().isoformat()
    storage.update_transaction(group_id, transaction_id, tx_data)

    # Update group timestamp
    group_data["updated_at"] = datetime.utcnow().isoformat()
    storage.update_group(group_id, group_data)

    # Publish balance update to MQTT
    _publish_balance_update(storage, group_id)

    return Transaction(**tx_data)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    current_user: UserInDB = Depends(get_current_user),
    storage: FileStorage = Depends(get_storage),
):
    """Delete a transaction."""
    # Find transaction across all groups
    groups = storage.get_groups()
    group_id = None

    for group in groups:
        tx = storage.get_transaction(group["id"], transaction_id)
        if tx:
            group_id = group["id"]
            break

    if not group_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Check user is a member of the group
    group_data = storage.get_group(group_id)
    if current_user.id not in group_data.get("members", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group",
        )

    # Delete transaction
    storage.delete_transaction(group_id, transaction_id)

    # Update group timestamp
    group_data["updated_at"] = datetime.utcnow().isoformat()
    storage.update_group(group_id, group_data)

    # Publish balance update to MQTT
    _publish_balance_update(storage, group_id)

    return None
