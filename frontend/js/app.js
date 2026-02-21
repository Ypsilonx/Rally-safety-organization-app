/**
 * Rally Safety App - Main Application Controller
 * Coordinates all app functionality after login
 */

const App = {
    user: null,
    messageCount: 0,

    /**
     * Initialize application
     */
    init() {
        console.log('Initializing app...');
        
        // Get current user
        this.user = window.Auth.getCurrentUser();
        if (!this.user) {
            console.error('No user found - redirecting to login');
            window.location.reload();
            return;
        }

        // Setup UI based on role
        this.setupUI();
        
        // Connect WebSocket
        this.connectWebSocket();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('App initialized for user:', this.user.name);
    },

    /**
     * Setup UI based on user role
     */
    setupUI() {
        // Update header
        document.getElementById('user-name').textContent = this.user.name;
        
        const roleBadge = document.getElementById('user-role-badge');
        roleBadge.textContent = this.getRoleLabel(this.user.role);
        
        // Show/hide admin panel (only for vedeni roles)
        const isVedeni = this.user.role === 'vedouci' || this.user.role === 'zastupce';
        const adminPanel = document.getElementById('admin-panel');
        const quickActions = document.getElementById('quick-actions');
        
        if (isVedeni) {
            adminPanel.classList.remove('hidden');
            quickActions.classList.add('hidden');
        } else {
            adminPanel.classList.add('hidden');
            quickActions.classList.remove('hidden');
        }
    },

    /**
     * Get user-friendly role label
     * @param {string} role
     * @returns {string}
     */
    getRoleLabel(role) {
        const labels = {
            'vedouci': 'Vedoucí',
            'zastupce': 'Zástupce',
            'komisar_trat': 'Komisař tratě',
            'casomer': 'Časomíra',
            'parkovani': 'Parkování',
            'zdravotnik': 'Zdravotník',
            'start': 'Start',
            'cil': 'Cíl',
            'bezpecnost': 'Bezpečnost',
        };
        return labels[role] || role;
    },

    /**
     * Connect to WebSocket server
     */
    connectWebSocket() {
        const authIdentifier = window.Auth.getAuthIdentifier();
        
        if (!authIdentifier) {
            console.error('No auth identifier - cannot connect WebSocket');
            this.showToast('Chyba připojení', 'error');
            return;
        }

        // Register event handlers
        window.wsClient.on('onMessage', (message) => this.handleMessage(message));
        window.wsClient.on('onStatusChange', (status) => this.handleStatusChange(status));
        window.wsClient.on('onError', (error) => this.handleError(error));
        
        // Connect
        window.wsClient.connect(authIdentifier);
    },

    /**
     * Setup event listeners for UI elements
     */
    setupEventListeners() {
        // Message form
        document.getElementById('message-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendChatMessage();
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });

        // Admin panel collapse
        const panelHeader = document.querySelector('.panel-header');
        if (panelHeader) {
            panelHeader.addEventListener('click', () => {
                this.toggleAdminPanel();
            });
        }

        // Broadcast button
        const broadcastBtn = document.getElementById('btn-broadcast');
        if (broadcastBtn) {
            broadcastBtn.addEventListener('click', () => {
                this.sendBroadcast();
            });
        }

        // Quick action buttons
        document.querySelectorAll('.btn-quick').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.handleQuickAction(action);
            });
        });
    },

    /**
     * Send chat message
     */
    sendChatMessage() {
        const input = document.getElementById('message-input');
        const content = input.value.trim();
        
        if (!content) return;
        
        // Optimistic update - show own message immediately
        const ownMessage = {
            message_id: `temp_${Date.now()}`,
            sender: {
                user_id: this.user.user_id,
                name: this.user.name,
                role: this.user.role
            },
            message_type: 'chat',
            content: content,
            created_at: new Date().toISOString()
        };
        
        // Display immediately (as own message)
        this.displayMessage(ownMessage);
        
        // Send via WebSocket
        window.wsClient.sendChatMessage(content);
        
        // Clear input
        input.value = '';
        input.focus();
    },

    /**
     * Handle incoming WebSocket message
     * @param {Object} message
     */
    handleMessage(message) {
        console.log('Handling message:', message);
        
        // Increment counter
        this.messageCount++;
        this.updateStats();
        
        // Display message in chat
        this.displayMessage(message);
        
        // Show notification for certain message types
        if (message.message_type === 'incident' || message.message_type === 'broadcast') {
            this.showToast(message.content, 'error');
        }
    },

    /**
     * Display message in chat area
     * @param {Object} message
     */
    displayMessage(message) {
        const messagesArea = document.getElementById('messages');
        
        // Remove welcome message if present
        const welcomeMsg = messagesArea.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        // Create message element
        const messageEl = document.createElement('div');
        messageEl.className = 'message';
        
        // Check if own message
        const isOwnMessage = message.sender?.user_id === this.user.user_id;
        if (isOwnMessage) {
            messageEl.classList.add('own');
        }
        
        // System/broadcast messages
        if (message.message_type === 'system' || message.message_type === 'broadcast') {
            messageEl.classList.add('system');
        }
        
        // Build message HTML
        const senderName = message.sender?.name || 'Systém';
        const timestamp = this.formatTime(message.created_at);
        
        messageEl.innerHTML = `
            <div class="message-header">
                <span class="message-sender">${senderName}</span>
                <span class="message-time">${timestamp}</span>
            </div>
            <div class="message-content">${this.escapeHtml(message.content)}</div>
        `;
        
        // Add to DOM
        messagesArea.appendChild(messageEl);
        
        // Scroll to bottom
        messagesArea.scrollTop = messagesArea.scrollHeight;
    },

    /**
     * Handle connection status change
     * @param {string} status - 'online', 'offline', 'reconnecting', 'failed'
     */
    handleStatusChange(status) {
        console.log('Status changed:', status);
        
        const indicator = document.getElementById('connection-status');
        
        // Update indicator
        indicator.className = 'status-indicator';
        
        switch (status) {
            case 'online':
                indicator.classList.add('online');
                indicator.title = 'Připojeno';
                this.showToast('Připojeno k serveru', 'success');
                break;
                
            case 'offline':
                indicator.classList.add('offline');
                indicator.title = 'Odpojeno';
                break;
                
            case 'reconnecting':
                indicator.classList.add('offline');
                indicator.title = 'Připojování...';
                break;
                
            case 'failed':
                indicator.classList.add('offline');
                indicator.title = 'Spojení selhalo';
                this.showToast('Spojení se serverem selhalo', 'error');
                break;
        }
    },

    /**
     * Handle WebSocket error
     * @param {Error} error
     */
    handleError(error) {
        console.error('App error:', error);
        this.showToast('Chyba komunikace', 'error');
    },

    /**
     * Update admin stats
     */
    updateStats() {
        const messagesEl = document.getElementById('stat-messages');
        if (messagesEl) {
            messagesEl.textContent = this.messageCount;
        }
    },

    /**
     * Toggle admin panel collapse
     */
    toggleAdminPanel() {
        const header = document.querySelector('.panel-header');
        const content = document.querySelector('.panel-content');
        
        if (header.classList.contains('collapsed')) {
            header.classList.remove('collapsed');
            content.style.display = 'block';
        } else {
            header.classList.add('collapsed');
            content.style.display = 'none';
        }
    },

    /**
     * Send broadcast message (admin only)
     */
    async sendBroadcast() {
        const content = prompt('Hromadná zpráva všem stanicím:');
        if (!content || !content.trim()) return;
        
        // Get current online count from stats
        let onlineCount = '-';
        try {
            const statsResponse = await fetch('http://localhost:8000/api/stats');
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                onlineCount = stats.active_connections || 0;
            }
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
        
        // Show broadcast message immediately in own UI
        const broadcastMessage = {
            message_id: `broadcast_${Date.now()}`,
            sender: {
                user_id: this.user.user_id,
                name: this.user.name,
                role: this.user.role
            },
            message_type: 'broadcast',
            content: `📢 HROMADNÁ ZPRÁVA VŠEM\n\n${content.trim()}\n\n→ Odesláno ${onlineCount} online stanicím`,
            created_at: new Date().toISOString()
        };
        
        this.displayMessage(broadcastMessage);
        
        // Send via WebSocket
        window.wsClient.sendSystemMessage('broadcast', content.trim());
        
        this.showToast(`Hromadná zpráva odeslána ${onlineCount} stanicím`, 'success');
    },

    /**
     * Handle quick action button click
     * @param {string} action
     */
    handleQuickAction(action) {
        let content = '';
        
        switch (action) {
            case 'ready':
                content = '✅ Stanice připravena';
                break;
            case 'issue':
                content = '⚠️ Problém na stanici';
                break;
            default:
                return;
        }
        
        window.wsClient.sendSystemMessage('status_update', content);
        this.showToast('Stav odeslán', 'success');
    },

    /**
     * Handle logout
     */
    handleLogout() {
        if (confirm('Opravdu se chcete odhlásit?')) {
            window.Auth.logout();
        }
    },

    /**
     * Show toast notification
     * @param {string} message
     * @param {string} type - 'success', 'error', 'info'
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /**
     * Format timestamp to HH:MM
     * @param {string} isoString
     * @returns {string}
     */
    formatTime(isoString) {
        if (!isoString) return '';
        
        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString('cs-CZ', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        } catch {
            return '';
        }
    },

    /**
     * Escape HTML to prevent XSS
     * @param {string} text
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

// Export to global scope
window.App = App;
