/**
 * API client with JWT authentication and automatic token refresh.
 */

// Make authenticated API call
async function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    // Merge options
    const requestOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        }
    };
    
    // Add authorization header if authenticated
    if (isAuthenticated()) {
        const token = getAccessToken();
        if (token) {
            requestOptions.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    
    // Make request
    let response = await fetch(url, requestOptions);
    
    // If unauthorized, try refreshing token
    if (response.status === 401 && isAuthenticated()) {
        const newToken = await refreshAccessToken();
        
        if (newToken) {
            // Retry request with new token
            requestOptions.headers['Authorization'] = `Bearer ${newToken}`;
            response = await fetch(url, requestOptions);
        } else {
            // Refresh failed, redirect to login
            window.location.href = '/login/';
            throw new Error('Authentication failed');
        }
    }
    
    // Parse response
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || data.detail || 'Request failed');
        }
        
        return data;
    } else {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.text();
    }
}

// Helper function for GET requests
async function apiGet(url) {
    return apiCall(url, { method: 'GET' });
}

// Helper function for POST requests
async function apiPost(url, data) {
    return apiCall(url, {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

// Helper function for PUT requests
async function apiPut(url, data) {
    return apiCall(url, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

// Helper function for DELETE requests
async function apiDelete(url) {
    return apiCall(url, { method: 'DELETE' });
}

