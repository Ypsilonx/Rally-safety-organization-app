/**
 * Rally Safety App - Authentication Module
 * Handles 2-tier login system: Vedení (username+password) + Komisař (PIN)
 */

// API Base URL
const API_BASE_URL = 'http://localhost:8000';

/**
 * Authentication state manager
 */
const Auth = {
    /**
     * Get current user from localStorage
     * @returns {Object|null} User object or null
     */
    getCurrentUser() {
        const userJson = localStorage.getItem('rally_user');
        return userJson ? JSON.parse(userJson) : null;
    },

    /**
     * Save user to localStorage
     * @param {Object} user - User object with role, name, pin/session_token
     */
    saveUser(user) {
        localStorage.setItem('rally_user', JSON.stringify(user));
    },

    /**
     * Clear user from localStorage (logout)
     */
    clearUser() {
        localStorage.removeItem('rally_user');
    },

    /**
     * Check if user is authenticated
     * @returns {boolean}
     */
    isAuthenticated() {
        return this.getCurrentUser() !== null;
    },

    /**
     * Get auth identifier for WebSocket (PIN or session_token)
     * @returns {string|null}
     */
    getAuthIdentifier() {
        const user = this.getCurrentUser();
        if (!user) return null;
        return user.pin_code || user.session_token;
    },

    /**
     * Login as Vedení (username + password)
     * @param {string} username
     * @param {string} password
     * @returns {Promise<Object>} User object
     * @throws {Error} Login failed
     */
    async loginVedeni(username, password) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/login-vedeni`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Přihlášení selhalo');
            }

            const data = await response.json();
            
            // Save user to localStorage
            const user = {
                user_id: data.user_id,
                name: data.name,
                role: data.role,
                phone: data.phone || null,
                session_token: data.session_token,
                login_type: 'vedeni',
                logged_in_at: new Date().toISOString(),
            };
            
            this.saveUser(user);
            return user;

        } catch (error) {
            console.error('Login Vedení error:', error);
            throw error;
        }
    },

    /**
     * Login as Komisař (PIN code)
     * @param {string} pin - 4-digit PIN code
     * @returns {Promise<Object>} User object
     * @throws {Error} Login failed
     */
    async loginKomisar(pin) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/login-komisar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ pin_code: pin }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Neplatný PIN kód');
            }

            const data = await response.json();
            
            // Save user to localStorage
            const user = {
                user_id: data.user_id || pin,
                name: data.name,
                role: data.role,
                station_id: data.station_id,
                vedeni_name: data.vedeni_name || 'Vedoucí RZ',
                vedeni_phone: data.vedeni_phone || '+420777123456',
                pin_code: pin,
                login_type: 'komisar',
                logged_in_at: new Date().toISOString(),
            };
            
            this.saveUser(user);
            return user;

        } catch (error) {
            console.error('Login Komisař error:', error);
            throw error;
        }
    },

    /**
     * Logout current user
     */
    logout() {
        this.clearUser();
        // Disconnect WebSocket if exists
        if (window.wsClient) {
            window.wsClient.disconnect();
        }
        // Redirect to login
        window.location.reload();
    },

    /**
     * Handle unauthorized (401) response - auto logout
     */
    handleUnauthorized() {
        console.warn('Unauthorized - logging out');
        this.clearUser();
        window.location.reload();
    },
};

/**
 * Login UI Controller
 */
const LoginUI = {
    /**
     * Initialize login screen event listeners
     */
    init() {
        // Role selection buttons
        document.getElementById('btn-vedeni').addEventListener('click', () => {
            this.showVedeniForm();
        });

        document.getElementById('btn-komisar').addEventListener('click', () => {
            this.showKomisarForm();
        });

        // Back buttons
        document.getElementById('back-from-vedeni').addEventListener('click', () => {
            this.showRoleSelection();
        });

        document.getElementById('back-from-komisar').addEventListener('click', () => {
            this.showRoleSelection();
        });

        // Form submissions
        document.getElementById('vedeni-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleVedeniLogin();
        });

        document.getElementById('komisar-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleKomisarLogin();
        });
    },

    /**
     * Show role selection screen
     */
    showRoleSelection() {
        document.getElementById('role-selection').classList.remove('hidden');
        document.getElementById('vedeni-login').classList.add('hidden');
        document.getElementById('komisar-login').classList.add('hidden');
        this.clearErrors();
    },

    /**
     * Show Vedení login form
     */
    showVedeniForm() {
        document.getElementById('role-selection').classList.add('hidden');
        document.getElementById('vedeni-login').classList.remove('hidden');
        document.getElementById('username').focus();
    },

    /**
     * Show Komisař login form
     */
    showKomisarForm() {
        document.getElementById('role-selection').classList.add('hidden');
        document.getElementById('komisar-login').classList.remove('hidden');
        document.getElementById('pin').focus();
    },

    /**
     * Handle Vedení login form submission
     */
    async handleVedeniLogin() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('vedeni-error');

        this.clearErrors();
        this.showLoading(true);

        try {
            const user = await Auth.loginVedeni(username, password);
            console.log('Vedení logged in:', user);
            
            // Switch to app screen
            this.switchToApp();
            
        } catch (error) {
            errorEl.textContent = error.message;
            errorEl.classList.remove('hidden');
        } finally {
            this.showLoading(false);
        }
    },

    /**
     * Handle Komisař login form submission
     */
    async handleKomisarLogin() {
        const pin = document.getElementById('pin').value.trim();
        const errorEl = document.getElementById('komisar-error');

        // Validate PIN format
        if (!/^\d{4}$/.test(pin)) {
            errorEl.textContent = 'PIN musí být 4 číslice';
            errorEl.classList.remove('hidden');
            return;
        }

        this.clearErrors();
        this.showLoading(true);

        try {
            const user = await Auth.loginKomisar(pin);
            console.log('Komisař logged in:', user);
            
            // Switch to app screen
            this.switchToApp();
            
        } catch (error) {
            errorEl.textContent = error.message;
            errorEl.classList.remove('hidden');
        } finally {
            this.showLoading(false);
        }
    },

    /**
     * Clear all error messages
     */
    clearErrors() {
        document.getElementById('vedeni-error').classList.add('hidden');
        document.getElementById('komisar-error').classList.add('hidden');
    },

    /**
     * Show/hide loading overlay
     * @param {boolean} show
     */
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    },

    /**
     * Switch from login screen to app screen
     */
    switchToApp() {
        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('login-screen').classList.add('hidden');
        document.getElementById('app-screen').classList.remove('hidden');
        document.getElementById('app-screen').classList.add('active');
        
        // Initialize app (will be called from app.js)
        if (window.App && window.App.init) {
            window.App.init();
        }
    },
};

// Auto-check authentication on page load
document.addEventListener('DOMContentLoaded', () => {
    const user = Auth.getCurrentUser();
    
    if (user) {
        // User already logged in - show app screen
        console.log('Auto-login detected:', user.name);
        LoginUI.switchToApp();
    } else {
        // Show login screen
        LoginUI.init();
    }
});

// Export to global scope
window.Auth = Auth;
window.LoginUI = LoginUI;
