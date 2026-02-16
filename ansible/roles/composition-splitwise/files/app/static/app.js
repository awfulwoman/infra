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

document.getElementById('addTransactionForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
        group_id: GROUP_ID,
        description: document.getElementById('description').value,
        amount: parseFloat(document.getElementById('amount').value),
        payer_id: document.getElementById('payer_id').value,
        currency: 'EUR',
        split_type: 'equal',
    };

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
