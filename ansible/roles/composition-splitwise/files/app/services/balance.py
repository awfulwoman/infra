from typing import Dict, List


def calculate_split(amount: float, members: List[str], split_type: str = "equal", recipient_id: str = None, custom_splits: Dict[str, float] = None) -> Dict[str, float]:
    """Calculate how an expense should be split among members.

    Args:
        amount: Total amount to split
        members: List of member IDs
        split_type: Type of split ("equal", "percentage", "custom", or "payment")
        recipient_id: For payment type, the person receiving the payment
        custom_splits: For percentage/custom types, dict of member_id to percentage/amount

    Returns:
        Dictionary mapping member_id to their share amount
    """
    if split_type == "payment":
        # Payment: only the recipient "owes" the full amount
        # This offsets the payer's balance by +amount and recipient's by -amount
        if not recipient_id:
            raise ValueError("recipient_id required for payment type")
        if recipient_id not in members:
            raise ValueError("Recipient must be a member of the group")
        return {recipient_id: amount}

    if split_type == "percentage":
        if not custom_splits:
            raise ValueError("custom_splits required for percentage type")

        # Validate percentages sum to 100
        total_percentage = sum(custom_splits.values())
        if abs(total_percentage - 100.0) > 0.01:
            raise ValueError(f"Percentages must sum to 100, got {total_percentage}")

        # Calculate amounts from percentages
        split_details = {}
        total_assigned = 0.0
        member_list = list(custom_splits.keys())

        for i, (member_id, percentage) in enumerate(custom_splits.items()):
            if member_id not in members:
                raise ValueError(f"Member {member_id} not in group")

            if i == len(member_list) - 1:
                # Last member gets remainder to handle rounding
                split_details[member_id] = round(amount - total_assigned, 2)
            else:
                share = round(amount * percentage / 100, 2)
                split_details[member_id] = share
                total_assigned += share

        return split_details

    if split_type == "custom":
        if not custom_splits:
            raise ValueError("custom_splits required for custom type")

        # Validate amounts sum to total
        total_custom = sum(custom_splits.values())
        if abs(total_custom - amount) > 0.01:
            raise ValueError(f"Custom amounts must sum to {amount}, got {total_custom}")

        # Validate all members exist
        for member_id in custom_splits:
            if member_id not in members:
                raise ValueError(f"Member {member_id} not in group")

        # Round to 2 decimal places
        return {k: round(v, 2) for k, v in custom_splits.items()}

    if split_type == "equal":
        if not members:
            raise ValueError("Cannot split among zero members")

        num_members = len(members)
        share_per_person = amount / num_members

        # Handle rounding: give extra pennies to first members
        split_details = {}
        total_assigned = 0.0

        for i, member_id in enumerate(members):
            if i == num_members - 1:
                # Last member gets remainder to ensure sum equals total
                split_details[member_id] = round(amount - total_assigned, 2)
            else:
                share = round(share_per_person, 2)
                split_details[member_id] = share
                total_assigned += share

        return split_details

    raise ValueError(f"Unsupported split type: {split_type}")


def calculate_balances(transactions: List[Dict], members: List[str]) -> Dict[str, float]:
    """Calculate net balance for each member in a group.

    A positive balance means the person is owed money.
    A negative balance means the person owes money.

    Args:
        transactions: List of transaction dictionaries
        members: List of member IDs in the group

    Returns:
        Dictionary mapping member_id to their net balance
    """
    balances = {member_id: 0.0 for member_id in members}

    for tx in transactions:
        payer_id = tx["payer_id"]
        split_details = tx.get("split_details", {})

        # Payer gets credited with the full amount
        if payer_id in balances:
            balances[payer_id] += tx["amount"]

        # Each member (including payer) gets debited their share
        for member_id, share in split_details.items():
            if member_id in balances:
                balances[member_id] -= share

    # Round to 2 decimal places
    return {member_id: round(balance, 2) for member_id, balance in balances.items()}
