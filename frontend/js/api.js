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

loaderTimeout: null,
    activeRequests: 0,

    showLoader() {
        this.activeRequests++;
        if (this.activeRequests === 1) {
            this.loaderTimeout = setTimeout(() => {
                const loader = document.getElementById('global-loader');
                if (loader && this.activeRequests > 0) {
                    loader.classList.remove('hidden');
                    setTimeout(() => loader.classList.remove('opacity-0'), 10);
                }
            }, 300); // 300ms debounce
        }
    },

    hideLoader() {
        this.activeRequests--;
        if (this.activeRequests <= 0) {
            this.activeRequests = 0;
            if (this.loaderTimeout) {
                clearTimeout(this.loaderTimeout);
                this.loaderTimeout = null;
            }
            const loader = document.getElementById('global-loader');
            if (loader) {
                loader.classList.add('opacity-0');
                setTimeout(() => loader.classList.add('hidden'), 300);
            }
        }
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

        if (!options.background) {
            this.showLoader();
        }
        
        try {
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

            return await response.json();
        } finally {
            if (!options.background) {
                this.hideLoader();
            }
        }
    },

    get(endpoint, options = {}) { return this.fetchWithAuth(endpoint, options); },
    post(endpoint, body, options = {}) { return this.fetchWithAuth(endpoint, { method: 'POST', body: JSON.stringify(body), ...options }); },
    put(endpoint, body, options = {}) { return this.fetchWithAuth(endpoint, { method: 'PUT', body: JSON.stringify(body), ...options }); },
    delete(endpoint, options = {}) { return this.fetchWithAuth(endpoint, { method: 'DELETE', ...options }); }
};
