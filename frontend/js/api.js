/**
 * API Wrapper with JWT Auth Handling
 */
const api = {
    baseUrl: '/api',
    
    getToken() { return localStorage.getItem('access_token'); },
    getRefreshToken() { return localStorage.getItem('refresh_token'); },
    setTokens(access, refresh) {
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
    },
    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    },

    async fetchWithAuth(endpoint, options = {}) {
        const token = this.getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        let response = await fetch(`${this.baseUrl}${endpoint}`, { ...options, headers });

        if (response.status === 401 && this.getRefreshToken()) {
            // Need to refresh token (simplified for now, ideally call /api/auth/refresh)
            this.clearTokens();
            window.location.href = "/";
            return null;
        }

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Request failed with status ${response.status}`);
        }

        return response.json();
    },

    get(endpoint) { return this.fetchWithAuth(endpoint); },
    post(endpoint, body) { return this.fetchWithAuth(endpoint, { method: 'POST', body: JSON.stringify(body) }); },
    put(endpoint, body) { return this.fetchWithAuth(endpoint, { method: 'PUT', body: JSON.stringify(body) }); },
    delete(endpoint) { return this.fetchWithAuth(endpoint, { method: 'DELETE' }); }
};
