/**
 * Auth Flow Management
 */
const auth = {
    checkUrlTokens() {
        const params = new URLSearchParams(window.location.search);
        const accessToken = params.get('token');
        const refreshToken = params.get('refresh');
        
        if (accessToken) {
            api.setTokens(accessToken, refreshToken || '');
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);
            return true;
        }
        return false;
    },

    async getCurrentUser() {
        if (!api.getToken()) return null;
        try {
            return await api.get('/auth/me');
        } catch (e) {
            console.error("Auth error:", e);
            alert("Authentication Error: " + e.message + "\nPlease check the backend server logs.");
            api.clearTokens();
            return null;
        }
    },

    login() {
        window.location.href = '/api/auth/google';
    },

    logout() {
        api.clearTokens();
        window.location.href = '/';
    },

    async requireAuth(expectedRole = null) {
        this.checkUrlTokens();
        const user = await this.getCurrentUser();
        
        if (!user) {
            window.location.href = '/';
            return null;
        }

        if (expectedRole === 'admin' && user.role !== 'admin') {
            window.location.href = '/client/';
            return null;
        }
        
        if (expectedRole === 'client' && user.role === 'admin') {
            window.location.href = '/admin/';
            return null;
        }
        
        // Update UI
        const nameEls = document.querySelectorAll('.user-name');
        const avatarEls = document.querySelectorAll('.user-avatar');
        
        nameEls.forEach(el => el.textContent = user.name);
        avatarEls.forEach(el => {
            if (user.avatar_url) {
                el.innerHTML = `<img src="${user.avatar_url}" alt="Avatar">`;
            } else {
                el.textContent = user.name.charAt(0).toUpperCase();
            }
        });
        
        return user;
    }
};
