/**
 * Authentication utilities for JWT token management.
 */

// Check if user is authenticated
function isAuthenticated() {
    return !!localStorage.getItem('access_token');
}

// Get access token
function getAccessToken() {
    return localStorage.getItem('access_token');
}

// Get refresh token
function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

// Get current user
function getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

// Logout function
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    window.location.href = '/login/';
}

// Refresh access token
async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    
    if (!refreshToken) {
        logout();
        return null;
    }
    
    try {
        const response = await fetch('/api/auth/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access);
            return data.access;
        } else {
            logout();
            return null;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        logout();
        return null;
    }
}

// Setup logout button handler
document.addEventListener('DOMContentLoaded', function() {
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
    
    // Display username if authenticated
    if (isAuthenticated()) {
        const user = getCurrentUser();
        const usernameDisplay = document.getElementById('username-display');
        if (usernameDisplay && user) {
            usernameDisplay.textContent = user.username;
        }
    }
});

