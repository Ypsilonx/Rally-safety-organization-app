/**
 * Rally Safety App - WebSocket Client
 * Handles real-time communication with backend server
 */

const WS_BASE_URL = 'ws://localhost:8000';
const RECONNECT_DELAY = 3000; // 3 seconds
const MAX_RECONNECT_ATTEMPTS = 5;
const HEARTBEAT_INTERVAL_MS = 30000; // 30 seconds

/**
 * WebSocket Client Manager
 */
class WebSocketClient {
    constructor() {
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;
        this.heartbeatTimer = null;
        this.messageQueue = [];
        this.eventHandlers = {
            onMessage: [],
            onStatusChange: [],
            onError: [],
        };
    }

    /**
     * Connect to WebSocket server
     * @param {string} authIdentifier - PIN code or session token
     */
    connect(authIdentifier) {
        if (!authIdentifier) {
            console.error('Cannot connect: no auth identifier');
            return;
        }

        const wsUrl = `${WS_BASE_URL}/ws/${authIdentifier}`;
        console.log('Connecting to WebSocket:', wsUrl);

        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => this.handleOpen();
            this.ws.onmessage = (event) => this.handleMessage(event);
            this.ws.onerror = (error) => this.handleError(error);
            this.ws.onclose = (event) => this.handleClose(event);

        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleError(error);
        }
    }

    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        if (this.ws) {
            console.log('Disconnecting WebSocket');
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
        this.clearReconnectTimer();
        this.stopHeartbeat();
    }

    /**
     * Send message to server
     * @param {Object} message - Message object
     * @returns {boolean} Success
     */
    sendMessage(message) {
        if (!this.isConnected || !this.ws) {
            console.warn('Not connected - queueing message');
            this.messageQueue.push(message);
            return false;
        }

        try {
            const payload = JSON.stringify(message);
            this.ws.send(payload);
            console.log('Message sent:', message);
            return true;

        } catch (error) {
            console.error('Failed to send message:', error);
            this.handleError(error);
            return false;
        }
    }

    /**
     * Send chat message
     * @param {string} content - Message content
     */
    sendChatMessage(content) {
        const message = {
            message_type: 'chat',
            content: content.trim(),
            created_at: new Date().toISOString(),
        };
        
        this.sendMessage(message);
    }

    /**
     * Send system message (quick actions, status updates)
     * @param {string} messageType - Type of message
     * @param {string} content - Message content
     */
    sendSystemMessage(messageType, content) {
        const message = {
            message_type: messageType,
            content: content,
            created_at: new Date().toISOString(),
        };
        
        // Broadcast messages are always critical priority
        if (messageType === 'broadcast') {
            message.priority = 'critical';
        }
        
        this.sendMessage(message);
    }

    /**
     * Handle WebSocket open event
     */
    handleOpen() {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.clearReconnectTimer();
        
        // Update status indicator
        this.notifyStatusChange('online');

        // Keep station presence alive on server.
        this.startHeartbeat();
        
        // Send queued messages
        this.flushMessageQueue();
    }

    /**
     * Handle incoming message
     * @param {MessageEvent} event
     */
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            console.log('Message received:', message);
            
            // Notify all message handlers
            this.eventHandlers.onMessage.forEach(handler => {
                try {
                    handler(message);
                } catch (error) {
                    console.error('Message handler error:', error);
                }
            });

        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    }

    /**
     * Handle WebSocket error
     * @param {Event} error
     */
    handleError(error) {
        console.error('WebSocket error:', error);
        
        // Notify error handlers
        this.eventHandlers.onError.forEach(handler => {
            try {
                handler(error);
            } catch (err) {
                console.error('Error handler failed:', err);
            }
        });
    }

    /**
     * Handle WebSocket close event
     * @param {CloseEvent} event
     */
    handleClose(event) {
        console.log('WebSocket closed:', event.code, event.reason);
        this.isConnected = false;
        this.ws = null;
        this.stopHeartbeat();

        // Authentication failures require fresh login (e.g., server restart invalidated session).
        if (event.code === 1008) {
            this.notifyStatusChange('auth_failed');
            return;
        }
        
        // Update status
        this.notifyStatusChange('offline');
        
        // Attempt reconnect if not manually closed
        if (event.code !== 1000 && this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            this.scheduleReconnect();
        } else if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            console.error('Max reconnect attempts reached');
            this.notifyStatusChange('failed');
        }
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        this.reconnectAttempts++;
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}`);
        
        this.notifyStatusChange('reconnecting');
        
        this.reconnectTimer = setTimeout(() => {
            const authIdentifier = window.Auth.getAuthIdentifier();
            if (authIdentifier) {
                this.connect(authIdentifier);
            } else {
                console.error('Cannot reconnect: no auth identifier');
            }
        }, RECONNECT_DELAY);
    }

    /**
     * Clear reconnect timer
     */
    clearReconnectTimer() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
    }

    /**
     * Start periodic heartbeat sending.
     */
    startHeartbeat() {
        this.stopHeartbeat();
        this.sendHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            this.sendHeartbeat();
        }, HEARTBEAT_INTERVAL_MS);
    }

    /**
     * Stop periodic heartbeat sending.
     */
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    /**
     * Send one heartbeat ping to backend.
     */
    sendHeartbeat() {
        if (!this.isConnected || !this.ws) {
            return;
        }

        this.sendMessage({
            message_type: 'heartbeat',
            content: '',
            created_at: new Date().toISOString(),
        });
    }

    /**
     * Send all queued messages
     */
    flushMessageQueue() {
        if (this.messageQueue.length === 0) return;
        
        console.log(`Flushing ${this.messageQueue.length} queued messages`);
        
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.sendMessage(message);
        }
    }

    /**
     * Register event handler
     * @param {string} eventType - 'onMessage', 'onStatusChange', 'onError'
     * @param {Function} handler - Callback function
     */
    on(eventType, handler) {
        if (this.eventHandlers[eventType]) {
            this.eventHandlers[eventType].push(handler);
        } else {
            console.warn('Unknown event type:', eventType);
        }
    }

    /**
     * Unregister event handler
     * @param {string} eventType
     * @param {Function} handler
     */
    off(eventType, handler) {
        if (this.eventHandlers[eventType]) {
            const index = this.eventHandlers[eventType].indexOf(handler);
            if (index > -1) {
                this.eventHandlers[eventType].splice(index, 1);
            }
        }
    }

    /**
     * Notify status change to all listeners
     * @param {string} status - 'online', 'offline', 'reconnecting', 'failed'
     */
    notifyStatusChange(status) {
        this.eventHandlers.onStatusChange.forEach(handler => {
            try {
                handler(status);
            } catch (error) {
                console.error('Status handler error:', error);
            }
        });
    }

    /**
     * Get connection status
     * @returns {string} 'online', 'offline', 'reconnecting'
     */
    getStatus() {
        if (this.isConnected) return 'online';
        if (this.reconnectTimer) return 'reconnecting';
        return 'offline';
    }
}

// Create global WebSocket client instance
window.wsClient = new WebSocketClient();

// Export
window.WebSocketClient = WebSocketClient;
