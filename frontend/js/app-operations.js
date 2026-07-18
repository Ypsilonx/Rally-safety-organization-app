/**
 * Rally Safety App - Operational facade.
 * Delegates to specialized RZ and incident modules.
 */

const AppOperationsModule = {
    /**
     * Update admin stats.
     */
    updateStats() {
        return window.AppOperationsRzModule.updateStats();
    },

    /**
     * Toggle admin panel collapse.
     */
    toggleAdminPanel() {
        return window.AppOperationsRzModule.toggleAdminPanel();
    },

    /**
     * Send broadcast message (admin only).
     * @param {Object} app
     */
    async sendBroadcast(app) {
        return window.AppOperationsIncidentsModule.sendBroadcast(app);
    },

    /**
     * Send predefined operational alert from vedeni panel.
     * @param {Object} app
     * @param {string} alertKey
     */
    sendAlertPreset(app, alertKey) {
        return window.AppOperationsIncidentsModule.sendAlertPreset(app, alertKey);
    },

    /**
     * Update top badge + map border according to current RZ state.
     * @param {Object} app
     */
    applyRzStateUi(app) {
        return window.AppOperationsRzModule.applyRzStateUi(app);
    },

    /**
     * Apply RZ state based on operation command.
     * @param {Object} app
     * @param {string} command
     */
    applyRzStateFromCommand(app, command) {
        return window.AppOperationsRzModule.applyRzStateFromCommand(app, command);
    },

    /**
     * Inspect message payload and update RZ state when command/state text indicates change.
     * @param {Object} app
     * @param {Object} message
     */
    applyRzStateFromMessage(app, message) {
        return window.AppOperationsRzModule.applyRzStateFromMessage(app, message);
    },

    /**
     * Handle quick action button click.
     * @param {Object} app
     * @param {string} action
     */
    handleQuickAction(app, action) {
        return window.AppOperationsIncidentsModule.handleQuickAction(app, action);
    },

    /**
     * Refresh readiness gate state from backend for admin dashboard.
     * @param {Object} app
     */
    startGateStatusRefresh(app) {
        return window.AppOperationsRzModule.startGateStatusRefresh(app);
    },

    /**
     * Load readiness snapshot and update gate indicator in admin board.
     * @param {Object} app
     * @returns {Promise<void>}
     */
    async refreshGateStatus(app) {
        return window.AppOperationsRzModule.refreshGateStatus(app);
    },

    /**
     * Queue immediate gate refresh (debounced).
     * @param {Object} app
     */
    requestGateStatusRefresh(app) {
        return window.AppOperationsRzModule.requestGateStatusRefresh(app);
    },

    /**
     * Return true when current user is vedeni role.
     * @param {Object} app
     * @returns {boolean}
     */
    isVedeniUser(app) {
        return window.AppOperationsRzModule.isVedeniUser(app);
    },

    /**
     * Determine if message should appear in incident warning board.
     * @param {Object} message
     * @returns {boolean}
     */
    isIncidentForDashboard(message) {
        return window.AppOperationsIncidentsModule.isIncidentForDashboard(message);
    },

    /**
     * Add newest incident to warning board for vedeni.
     * @param {Object} app
     * @param {Object} message
     * @param {boolean} persist
     */
    addIncidentWarning(app, message, persist = true) {
        return window.AppOperationsIncidentsModule.addIncidentWarning(app, message, persist);
    },
};

window.AppOperationsModule = AppOperationsModule;