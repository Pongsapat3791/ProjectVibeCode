/**
 * @name VoiceActivityLog
 * @version 2.3.0
 * @description Logs detailed user join/leave events and displays them in a popup table.
 * @author Pongsapat, Gemini 2.5 Pro
 * @update Pongsapat, Gemini 2.5 Pro
 */
module.exports = class VoiceActivityLog {
    constructor() {
        this.handleVoiceStateUpdates = this.handleVoiceStateUpdates.bind(this);
        this.onVoice = this.onVoice.bind(this); // ผูกฟังก์ชัน onVoice ที่เพิ่มเข้ามาใหม่
        this.userStates = {};
        this.eventLog = [];
        this.observer = null;
        this.myButton = null;
        this.myStyles = null;
        this.modules = {};
    }
    
    loadModules() {
        try {
            this.modules.FluxDispatcher = BdApi.Webpack.getModule(m => m.dispatch && m.subscribe, { searchExports: false });
            this.modules.UserStore = BdApi.Webpack.getModule(BdApi.Webpack.Filters.byStoreName("UserStore"));
            this.modules.VoiceStateStore = BdApi.Webpack.getModule(BdApi.Webpack.Filters.byStoreName("VoiceStateStore"));
            this.modules.ChannelStore = BdApi.Webpack.getModule(BdApi.Webpack.Filters.byStoreName("ChannelStore"));
            return Object.values(this.modules).every(Boolean);
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Failed to load modules", error);
            return false;
        }
    }

    start() {
        try {
            if (!this.loadModules()) {
                console.error("VoiceActivityLog Plugin: Could not find required modules.");
                BdApi.showToast("Voice Activity Log: Error on start! Could not load modules.", { type: "error" });
                return;
            }

            this.modules.FluxDispatcher.subscribe("VOICE_STATE_UPDATES", this.handleVoiceStateUpdates);
            console.log("VoiceActivityLog Plugin: Started and listening for voice state updates.");

            this.populateInitialStates();
            this.injectCSS();

            this.observer = new MutationObserver(() => {
                const userSettingsButton = document.querySelector('button[aria-label="User Settings"]');
                if (userSettingsButton) {
                    const toolbar = userSettingsButton.parentElement;
                    if (toolbar && !toolbar.querySelector('#my-log-button')) {
                        this.createButton(toolbar);
                    }
                }
            });
            this.observer.observe(document.body, { childList: true, subtree: true });

            BdApi.showToast("Voice Activity Log: Activated!", { type: "success" });
        } catch (error) {
            console.error("VoiceActivityLog Plugin: A critical error occurred on start.", error);
            BdApi.showToast("Voice Activity Log: A critical error occurred on start. Check console.", { type: "error" });
        }
    }

    stop() {
        if (this.modules.FluxDispatcher) {
            this.modules.FluxDispatcher.unsubscribe("VOICE_STATE_UPDATES", this.handleVoiceStateUpdates);
        }
        if (this.observer) this.observer.disconnect();

        this.removeButton();
        this.removeCSS();
        this.userStates = {};
        this.eventLog = [];
        
        console.log("VoiceActivityLog Plugin: Stopped.");
        BdApi.showToast("Voice Activity Log: Deactivated!", { type: "info" });
    }

    // --- เพิ่ม: ฟังก์ชัน onVoice เพื่อบันทึกผู้ใช้ที่อยู่ในห้องแล้ว ---
    onVoice(channelId) {
        try {
            const currentStates = this.modules.VoiceStateStore.getVoiceStatesForChannel(channelId);
            const myUserId = this.modules.UserStore.getCurrentUser().id;
            const channel = this.modules.ChannelStore.getChannel(channelId);
            const channelName = channel ? channel.name : "Unknown Channel";

            for (const userId in currentStates) {
                // ไม่ต้องบันทึกตัวเอง เพราะมี event 'user_join' แยกอยู่แล้ว
                if (userId === myUserId) continue;

                const user = this.modules.UserStore.getUser(userId);
                if (!user) continue;

                const logData = {
                    timestamp: new Date(),
                    event: "user_present", // Event type ใหม่
                    userId: user.id,
                    userName: user.username,
                    channelId: channelId,
                    channelName: channelName
                };
                this.eventLog.push(logData);
                console.log(`VoiceActivityLog: ${logData.userName} (${logData.userId}) was present in channel ${logData.channelName} (${logData.channelId})`);
            }
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Error in onVoice", error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error in onVoice ${error}`, { type: "error" });
        }
    }


    handleVoiceStateUpdates(payload) {
        try {
            if (!payload || !Array.isArray(payload.voiceStates)) return;

            const myUser = this.modules.UserStore.getCurrentUser();
            if (!myUser) return;

            const myCurrentVoiceState = this.modules.VoiceStateStore.getVoiceStateForUser(myUser.id);
            const myCurrentChannelId = myCurrentVoiceState ? myCurrentVoiceState.channelId : null;

            const myOldVoiceState = this.userStates[myUser.id];
            const myOldChannelId = myOldVoiceState ? myOldVoiceState.channelId : null;
            
            const channelOfInterest = myCurrentChannelId || myOldChannelId;

            if (!channelOfInterest) {
                if (Object.keys(this.userStates).length > 0) {
                    this.userStates = {};
                }
                return;
            }

            for (const newState of payload.voiceStates) {
                const { userId } = newState;
                const user = this.modules.UserStore.getUser(userId);
                if (!user) continue;

                const oldState = this.userStates[userId];
                const oldChannelId = oldState ? oldState.channelId : null;
                const newChannelId = newState.channelId;

                if (oldChannelId === newChannelId) continue;

                let logData = null;
                let toastMessage = null;
                let toastType = "info";

                if (newChannelId === channelOfInterest && oldChannelId !== channelOfInterest) {
                    const channel = this.modules.ChannelStore.getChannel(newChannelId);
                    const channelName = channel ? channel.name : "Unknown Channel";
                    logData = {
                        timestamp: new Date(),
                        event: "user_join",
                        userId: user.id,
                        userName: user.username,
                        channelId: newChannelId,
                        channelName: channelName
                    };
                    toastMessage = userId === myUser.id ? `You joined ${channelName}.` : `${user.username} joined the channel.`;
                    toastType = "success";
                    
                    // --- แก้ไข: ถ้าเป็นเราที่เข้าร่วมห้อง ให้เรียก onVoice เพื่อบันทึกคนอื่น ---
                    if (userId === myUser.id) {
                        this.onVoice(newChannelId);
                    }

                } 
                else if (oldChannelId === channelOfInterest && newChannelId !== channelOfInterest) {
                    const channel = this.modules.ChannelStore.getChannel(oldChannelId);
                    const channelName = channel ? channel.name : "Unknown Channel";
                    logData = {
                        timestamp: new Date(),
                        event: "user_leave",
                        userId: user.id,
                        userName: user.username,
                        channelId: oldChannelId,
                        channelName: channelName
                    };
                    toastMessage = userId === myUser.id ? `You left ${channelName}.` : `${user.username} left the channel.`;
                    toastType = "error";
                }

                if (logData) {
                    this.eventLog.push(logData);
                    console.log(`VoiceActivityLog: ${logData.userName} (${logData.userId}) ${logData.event} channel ${logData.channelName} (${logData.channelId})`);
                    BdApi.showToast(toastMessage, { type: toastType });
                }
            }

            for (const newState of payload.voiceStates) {
                 const { userId } = newState;
                 if (newState.channelId) {
                     this.userStates[userId] = newState;
                 } else {
                     if (this.userStates[userId]) {
                         delete this.userStates[userId];
                     }
                 }
            }
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Error in handleVoiceStateUpdates" , error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error in handleVoiceStateUpdates ${error}`, { type: "error" });
        }
    }

    populateInitialStates() {
        try {
            const myUser = this.modules.UserStore.getCurrentUser();
            if (myUser) {
                const myVoiceState = this.modules.VoiceStateStore.getVoiceStateForUser(myUser.id);
                if (myVoiceState && myVoiceState.channelId) {
                    const currentChannelStates = this.modules.VoiceStateStore.getVoiceStatesForChannel(myVoiceState.channelId);
                    this.userStates = { ...currentChannelStates }; 
                    console.log("VoiceActivityLog Plugin: Initial states populated.");
                }
            }
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Error in populateInitialStates", error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error in populateInitialStates ${error}`, { type: "error" });
        }
    }

    showLogPopup() {
        try {
            const sortedLog = [...this.eventLog].reverse();

            const tableHeader = BdApi.React.createElement("thead", null, 
                BdApi.React.createElement("tr", null, [
                    BdApi.React.createElement("th", { key: 'h-time' }, "Timestamp"),
                    BdApi.React.createElement("th", { key: 'h-event' }, "Event"),
                    BdApi.React.createElement("th", { key: 'h-user' }, "User"),
                    BdApi.React.createElement("th", { key: 'h-channel' }, "Channel Name"),
                    BdApi.React.createElement("th", { key: 'h-userid' }, "User ID")
                ])
            );
            const tableBody = BdApi.React.createElement("tbody", null, 
                sortedLog.map((log, index) => {
                    // --- แก้ไข: เพิ่มเงื่อนไขสำหรับ event 'user_present' ---
                    const getEventStyle = (event) => {
                        if (event === 'user_join') return { color: '#2dc770', text: 'Joined' };
                        if (event === 'user_leave') return { color: '#f04747', text: 'Left' };
                        if (event === 'user_present') return { color: '#888888', text: 'Present' };
                        return { color: 'var(--header-primary)', text: event };
                    };
                    const eventInfo = getEventStyle(log.event);

                    return BdApi.React.createElement("tr", { key: `log-${index}` }, [
                        BdApi.React.createElement("td", { key: `time-${index}` }, log.timestamp.toLocaleString('th-TH')),
                        BdApi.React.createElement("td", { key: `event-${index}`, style: { color: eventInfo.color } }, eventInfo.text),
                        BdApi.React.createElement("td", { key: `user-${index}` }, log.userName),
                        BdApi.React.createElement("td", { key: `channel-${index}` }, log.channelName || 'N/A'),
                        BdApi.React.createElement("td", { key: `userid-${index}` }, log.userId)
                    ]);
                })
            );

            const dataTable = BdApi.React.createElement("div", { style: { maxHeight: "50vh", overflowY: "auto" } },
                BdApi.React.createElement("table", { className: "my-data-table" }, [
                    tableHeader,
                    tableBody
                ])
            );
            
            if (this.eventLog.length === 0) {
                BdApi.showConfirmationModal(
                    "Voice Channel Activity Log",
                    [ BdApi.React.createElement("p", { style: {color: "var(--header-primary)"} }, "No user activity has been logged yet.") ],
                    { confirmText: "Okay", cancelText: "Close" }
                );
            } else {
                BdApi.showConfirmationModal(
                    "Voice Channel Activity Log",
                    [ dataTable ],
                    { 
                        confirmText: "Save", 
                        cancelText: "Clear Log", 
                        onConfirm: () => { this.saveLogToFile(); }, 
                        onCancel: () => { 
                            this.eventLog = []; 
                            BdApi.showToast("Log cleared!", {type: "info"}); 
                        } 
                    }
                );
            }
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Error in showLogPopup", error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error in showLogPopup ${error}`, { type: "error" });
        }
    }

    saveLogToFile() {
        try {
            if (this.eventLog.length === 0) {
                BdApi.showToast("Log is empty. Nothing to save.", { type: "info" });
                return;
            }
    
            const bom = "\uFEFF";
            const header = ['"Timestamp"', '"Event"', '"User"', '"Channel Name"', '"User ID"'].join(',');
            const rows = this.eventLog.map(log => {
                const timestamp = `"${log.timestamp.toLocaleString('th-TH')}"`;
                // --- แก้ไข: เพิ่มเงื่อนไขสำหรับ event 'user_present' ในไฟล์ CSV ---
                const getEventText = (event) => {
                    if (event === 'user_join') return 'Joined';
                    if (event === 'user_leave') return 'Left';
                    if (event === 'user_present') return 'Present';
                    return event;
                };
                const event = `"${getEventText(log.event)}"`;
                const userName = `"${log.userName.replace(/"/g, '""')}"`;
                const channelName = `"${(log.channelName || 'N/A').replace(/"/g, '""')}"`;
                const userId = `"${log.userId}"`;
                return [timestamp, event, userName, channelName, userId].join(',');
            }).join('\n');
    
            const csvContent = bom + header + '\n' + rows;
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
            const link = document.createElement("a");
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            const now = new Date();
            const formattedDate = `${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, '0')}${now.getDate().toString().padStart(2, '0')}_${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}`;
            link.setAttribute("download", `voice-activity-log-${formattedDate}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            BdApi.showToast("Log saved successfully!", { type: "success" });
    
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Error in saveLogToFile", error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error saving log: ${error}`, { type: "error" });
        }
    }

    createButton(toolbar) {
        try {
            if (document.getElementById('my-log-button')) return;

            const myButton = document.createElement('div');
            myButton.id = 'my-log-button';
            myButton.className = 'my-button-style';
            myButton.innerHTML = '📁';
            myButton.setAttribute('role', 'button');
            myButton.setAttribute('aria-label', 'Show Activity Log');
            myButton.onclick = () => this.showLogPopup();
            
            const userSettingsButton = toolbar.querySelector('button[aria-label="User Settings"]');
            if (userSettingsButton) {
                this.myButton = toolbar.insertBefore(myButton, userSettingsButton);
            } else {
                this.myButton = toolbar.appendChild(myButton);
            }
        } catch (error)
        {
            console.error("VoiceActivityLog Plugin: Error in createButton", error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error in createButton ${error}`, { type: "error" });
        }
    }

    removeButton() {
        try {
            if (this.myButton) {
                this.myButton.remove();
                this.myButton = null;
            }
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Error in removeButton", error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error in removeButton ${error}`, { type: "error" });
        }
    }

    injectCSS() {
        try {
            const css = `
                .my-button-style {
                    background: var(--button-secondary-background); 
                    color: var(--interactive-normal); 
                    font-weight: bold;
                    width: 24px; height: 24px; border-radius: 50%;
                    display: flex; align-items: center; justify-content: center;
                    margin-left: 4px;
                    margin-right: 4px;
                    margin-top: 7px;
                    cursor: pointer;
                    transition: transform 0.2s, background-color 0.2s;
                }
                .my-button-style:hover { 
                    background: var(--button-secondary-background-hover); 
                    color: var(--interactive-hover);
                    transform: scale(1.1); 
                }
                .my-data-table {
                    width: 100%; border-collapse: collapse; margin-top: 10px;
                    color: var(--header-primary);
                }
                .my-data-table th, .my-data-table td {
                    padding: 8px 12px; text-align: left;
                    border-bottom: 1px solid var(--background-modifier-accent);
                    white-space: nowrap;
                }
                .my-data-table th { 
                    color: var(--header-primary); 
                    font-weight: bold; 
                    background-color: var(--background-secondary);
                }
                .my-data-table tr:last-child td { border-bottom: none; }
                .my-data-table tr:hover { background-color: var(--background-modifier-hover); }
            `;
            this.myStyles = BdApi.injectCSS('voice-log-styles-detailed', css);
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Error in injectCSS", error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error in injectCSS ${error}`, { type: "error" });
        }
    }

    removeCSS() {
        try{
            if (this.myStyles) {
                BdApi.clearCSS('voice-log-styles-detailed');
                this.myStyles = null;
            }
        } catch (error) {
            console.error("VoiceActivityLog Plugin: Error in removeCSS", error);
            BdApi.showToast(`VoiceActivityLog Plugin: Error in removeCSS ${error}`, { type: "error" });
        }
    }
};
