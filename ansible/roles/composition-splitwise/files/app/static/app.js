// Registration form handler
document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    const errorMessage = document.getElementById('error-message');

    if (password !== confirmPassword) {
        errorMessage.textContent = 'Passwords do not match';
        errorMessage.style.display = 'block';
        return;
    }

    const formData = {
        username: document.getElementById('username').value,
        display_name: document.getElementById('display_name').value,
        password: password,
    };

    try {
        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData),
        });

        if (response.ok) {
            window.location.href = '/login';
        } else {
            const error = await response.json();
            errorMessage.textContent = error.detail || 'Registration failed';
            errorMessage.style.display = 'block';
        }
    } catch (error) {
        errorMessage.textContent = 'Network error. Please try again.';
        errorMessage.style.display = 'block';
    }
});

// Create group modal
function showCreateGroupModal() {
    document.getElementById('createGroupModal').style.display = 'flex';
}

function hideCreateGroupModal() {
    document.getElementById('createGroupModal').style.display = 'none';
}

document.getElementById('createGroupForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('group_name').value;
    const checkboxes = document.querySelectorAll('input[name="members"]:checked');
    const members = Array.from(checkboxes).map((cb) => cb.value);
    const errorMessage = document.getElementById('group-error-message');

    if (members.length < 2) {
        errorMessage.textContent = 'Group must have at least 2 members';
        errorMessage.style.display = 'block';
        return;
    }

    const formData = { name, members };

    try {
        const response = await fetch('/api/v1/groups', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(formData),
        });

        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            errorMessage.textContent = error.detail || 'Failed to create group';
            errorMessage.style.display = 'block';
        }
    } catch (error) {
        errorMessage.textContent = 'Network error. Please try again.';
        errorMessage.style.display = 'block';
    }
});

// Add transaction modal
function showAddTransactionModal() {
    document.getElementById('addTransactionModal').style.display = 'flex';
}

function hideAddTransactionModal() {
    document.getElementById('addTransactionModal').style.display = 'none';
}

function toggleCustomSplit() {
    const splitType = document.getElementById('split_type').value;
    const container = document.getElementById('custom_splits_container');
    const splitUnit = document.querySelectorAll('.split-unit');

    if (splitType === 'equal') {
        container.style.display = 'none';
    } else {
        container.style.display = 'block';
        // Update unit labels
        splitUnit.forEach(unit => {
            unit.textContent = splitType === 'percentage' ? '%' : '€';
        });
    }
}

// Record payment modal
function showRecordPaymentModal() {
    document.getElementById('recordPaymentModal').style.display = 'flex';
}

function hideRecordPaymentModal() {
    document.getElementById('recordPaymentModal').style.display = 'none';
}

document.getElementById('addTransactionForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const splitType = document.getElementById('split_type').value;
    const formData = {
        group_id: GROUP_ID,
        description: document.getElementById('description').value,
        amount: parseFloat(document.getElementById('amount').value),
        payer_id: document.getElementById('payer_id').value,
        currency: 'EUR',
        split_type: splitType,
    };

    // Collect custom splits if not equal
    if (splitType !== 'equal') {
        const customSplits = {};
        const splitInputs = document.querySelectorAll('.split-input');
        splitInputs.forEach(input => {
            const memberId = input.id.replace('split_', '');
            const value = parseFloat(input.value) || 0;
            if (value > 0) {
                customSplits[memberId] = value;
            }
        });
        formData.custom_splits = customSplits;
    }

    const errorMessage = document.getElementById('transaction-error-message');

    try {
        const response = await fetch(`/api/v1/groups/${GROUP_ID}/transactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(formData),
        });

        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            errorMessage.textContent = error.detail || 'Failed to add transaction';
            errorMessage.style.display = 'block';
        }
    } catch (error) {
        errorMessage.textContent = 'Network error. Please try again.';
        errorMessage.style.display = 'block';
    }
});

document.getElementById('recordPaymentForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const payerId = document.getElementById('payment_payer').value;
    const recipientId = document.getElementById('payment_recipient').value;

    if (payerId === recipientId) {
        const errorMessage = document.getElementById('payment-error-message');
        errorMessage.textContent = 'Cannot pay yourself';
        errorMessage.style.display = 'block';
        return;
    }

    const description = document.getElementById('payment_description').value || 'Payment';

    const formData = {
        group_id: GROUP_ID,
        description: description,
        amount: parseFloat(document.getElementById('payment_amount').value),
        payer_id: payerId,
        recipient_id: recipientId,
        currency: 'EUR',
        split_type: 'payment',
    };

    const errorMessage = document.getElementById('payment-error-message');

    try {
        const response = await fetch(`/api/v1/groups/${GROUP_ID}/transactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(formData),
        });

        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            errorMessage.textContent = error.detail || 'Failed to record payment';
            errorMessage.style.display = 'block';
        }
    } catch (error) {
        errorMessage.textContent = 'Network error. Please try again.';
        errorMessage.style.display = 'block';
    }
});

// Edit transaction modal
function showEditTransactionModal() {
    document.getElementById('editTransactionModal').style.display = 'flex';
}

function hideEditTransactionModal() {
    document.getElementById('editTransactionModal').style.display = 'none';
}

function toggleEditCustomSplit() {
    const splitType = document.getElementById('edit_split_type').value;
    const container = document.getElementById('edit_custom_splits_container');
    const splitUnit = container.querySelectorAll('.split-unit');

    if (splitType === 'equal') {
        container.style.display = 'none';
    } else {
        container.style.display = 'block';
        // Update unit labels
        splitUnit.forEach(unit => {
            unit.textContent = splitType === 'percentage' ? '%' : '€';
        });
    }
}

function editTransaction(transactionId, description, amount, payerId, splitType, splitDetails) {
    document.getElementById('edit_transaction_id').value = transactionId;
    document.getElementById('edit_description').value = description;
    document.getElementById('edit_amount').value = amount;
    document.getElementById('edit_payer_id').value = payerId;
    document.getElementById('edit_split_type').value = splitType || 'equal';

    // Clear all split inputs first
    document.querySelectorAll('.edit-split-input').forEach(input => {
        input.value = 0;
    });

    // Populate split details if custom/percentage
    if (splitType && splitType !== 'equal' && splitType !== 'payment' && splitDetails) {
        const splits = typeof splitDetails === 'string' ? JSON.parse(splitDetails) : splitDetails;
        Object.entries(splits).forEach(([memberId, splitAmount]) => {
            const input = document.getElementById(`edit_split_${memberId}`);
            if (input) {
                if (splitType === 'percentage') {
                    // Convert amount back to percentage
                    const percentage = (splitAmount / amount) * 100;
                    input.value = percentage.toFixed(2);
                } else {
                    // Custom amounts - use as-is
                    input.value = splitAmount;
                }
            }
        });
    }

    toggleEditCustomSplit();
    showEditTransactionModal();
}

document.getElementById('editTransactionForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const transactionId = document.getElementById('edit_transaction_id').value;
    const splitType = document.getElementById('edit_split_type').value;
    const formData = {
        description: document.getElementById('edit_description').value,
        amount: parseFloat(document.getElementById('edit_amount').value),
        payer_id: document.getElementById('edit_payer_id').value,
        split_type: splitType,
    };

    // Collect custom splits if not equal
    if (splitType !== 'equal') {
        const customSplits = {};
        const splitInputs = document.querySelectorAll('.edit-split-input');
        splitInputs.forEach(input => {
            const memberId = input.id.replace('edit_split_', '');
            const value = parseFloat(input.value) || 0;
            if (value > 0) {
                customSplits[memberId] = value;
            }
        });
        formData.custom_splits = customSplits;
    }

    const errorMessage = document.getElementById('edit-transaction-error-message');

    try {
        const response = await fetch(`/api/v1/transactions/${transactionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(formData),
        });

        if (response.ok) {
            window.location.reload();
        } else {
            const error = await response.json();
            errorMessage.textContent = error.detail || 'Failed to update transaction';
            errorMessage.style.display = 'block';
        }
    } catch (error) {
        errorMessage.textContent = 'Network error. Please try again.';
        errorMessage.style.display = 'block';
    }
});

// Delete transaction
async function deleteTransaction(transactionId) {
    if (!confirm('Are you sure you want to delete this transaction?')) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/transactions/${transactionId}`, {
            method: 'DELETE',
            credentials: 'include',
        });

        if (response.ok) {
            window.location.reload();
        } else {
            alert('Failed to delete transaction');
        }
    } catch (error) {
        alert('Network error. Please try again.');
    }
}

// Close modal when clicking outside
window.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.style.display = 'none';
    }
});
