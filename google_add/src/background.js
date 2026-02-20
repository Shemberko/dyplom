// src/background.js
import { initAuthService } from './services/auth_service.js';

const API_URL = "http://127.0.0.1:8000";
const AUTH_URL = "http://127.0.0.1:8001";
const STORAGE_KEY = 'tracking_enabled';

initAuthService(AUTH_URL);

// Структура: { tabId: { openedAt: timestamp, activeTimeMs: number, lastActiveStart: timestamp|null } }
let tabMetrics = {}; 
let currentActiveTabId = null;

function initTab(tabId) {
    if (!tabMetrics[tabId]) {
        tabMetrics[tabId] = {
            openedAt: Date.now(),
            activeTimeMs: 0,
            lastActiveStart: null 
        };
    }
}

function updateCurrentTabMetrics() {
    const now = Date.now();
    if (currentActiveTabId !== null && tabMetrics[currentActiveTabId]) {
        const data = tabMetrics[currentActiveTabId];
        if (data.lastActiveStart) {
            const delta = now - data.lastActiveStart;
            data.activeTimeMs += delta;
            data.lastActiveStart = now;
        }
    }
}

function sendLogToServer() {
    chrome.storage.local.get([STORAGE_KEY, "activityParsedData", "closedTabIds", "debug_logs"], (res) => {
        if (res[STORAGE_KEY] === false) return;

        chrome.identity.getProfileUserInfo((userInfo) => {
            if (!userInfo.id) return;

            const metaMap = new Map((res.activityParsedData || []).map(e => [String(e.info.tabId), e]));
            
            const now = Date.now();
            const logPayload = [];
            
            for (const [tId, metrics] of Object.entries(tabMetrics)) {
                if (metaMap.has(tId)) {
                    const meta = metaMap.get(tId);
                    logPayload.push({
                        info: {
                            ...meta.info,
                            active: metrics.activeTimeMs,
                            totalOpen: now - metrics.openedAt
                        }
                    });
                }
            }

            const currentDebugLogs = res.debug_logs || [];
            const debugEntry = {
                timestamp: new Date().toISOString(),
                payloadSize: logPayload.length,
                payload: logPayload,        
                rawMetrics: { ...tabMetrics }, 
                metaMapKeys: Array.from(metaMap.keys())
            };
            
            const updatedLogs = [...currentDebugLogs, debugEntry].slice(-20);
            chrome.storage.local.set({ debug_logs: updatedLogs });
            console.log("[background] Debug log saved to storage:", debugEntry);

            if (logPayload.length === 0) return;

            fetch(API_URL + "/data/post-collected-data", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user: { info: userInfo },
                    log: logPayload
                })
            })
            .then(resp => {
                if (resp.ok) {
                    console.log("[background] Log sent successfully.");
                    
                    const now = Date.now();
                    
                    const closedIds = (res.closedTabIds || []).map(c => String(c.tabId));
                    const closedSet = new Set(closedIds);

                    for (const [tId, metrics] of Object.entries(tabMetrics)) {
                        
                        if (closedSet.has(tId)) {
                            delete tabMetrics[tId];
                        } else {
                            metrics.activeTimeMs = 0; 
                            metrics.openedAt = now;
                            if (metrics.lastActiveStart !== null) {
                                metrics.lastActiveStart = now;
                            }
                        }
                    }

                    chrome.storage.local.set({ closedTabIds: [] });
                    const newMetaData = (res.activityParsedData || []).filter(e => !closedSet.has(String(e.info.tabId)));
                    chrome.storage.local.set({ activityParsedData: newMetaData });
                }
            })
            .catch(err => {
                console.error("Send log failed:", err);
            });
        });
    });
}


const IGNORED_DOMAINS_KEY = 'ignored_domains';

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    chrome.storage.local.get([STORAGE_KEY, IGNORED_DOMAINS_KEY], (res) => {
        if (res[STORAGE_KEY] === false) return;

        const ignoredDomains = res[IGNORED_DOMAINS_KEY] || [];

        if (changeInfo.status === "complete" && tab.url && !tab.url.startsWith("chrome://")) {
            
            try {
                const url = new URL(tab.url);
                const hostname = url.hostname.replace('www.', ''); 
                
                if (ignoredDomains.some(domain => hostname.includes(domain))) {
                    console.log(`Домен ${hostname} в списку ігнорування. Пропускаємо.`);
                    return;
                }
            } catch (e) {
                console.error("Invalid URL:", tab.url);
            }

            initTab(tabId);
            
            if (tab.active) {
                currentActiveTabId = tabId;
                tabMetrics[tabId].lastActiveStart = Date.now();
            }

            chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ["services/page_analyzer.js"]
            }).then(() => {
                chrome.tabs.sendMessage(tabId, { tabId: tabId }).catch(() => {});
            }).catch(e => console.log("Injection failed:", e));
        }
    });
});

chrome.tabs.onActivated.addListener(({ tabId }) => {
    chrome.storage.local.get([STORAGE_KEY], (res) => {
        if (res[STORAGE_KEY] === false) return;

        updateCurrentTabMetrics();

        if (currentActiveTabId !== null && tabMetrics[currentActiveTabId]) {
            tabMetrics[currentActiveTabId].lastActiveStart = null;
        }

        initTab(tabId);
        currentActiveTabId = tabId;
        tabMetrics[tabId].lastActiveStart = Date.now();
    });
});

chrome.windows.onFocusChanged.addListener((windowId) => {
    chrome.storage.local.get([STORAGE_KEY], (res) => {
        if (res[STORAGE_KEY] === false) return;

        updateCurrentTabMetrics();

        if (windowId === chrome.windows.WINDOW_ID_NONE) {
            if (currentActiveTabId !== null && tabMetrics[currentActiveTabId]) {
                tabMetrics[currentActiveTabId].lastActiveStart = null;
            }
        } else {
            chrome.tabs.query({ active: true, windowId }, (tabs) => {
                if (tabs.length > 0) {
                    const t = tabs[0];
                    currentActiveTabId = t.id;
                    initTab(t.id);
                    tabMetrics[t.id].lastActiveStart = Date.now();
                }
            });
        }
    });
});

chrome.tabs.onRemoved.addListener((tabId) => {
    chrome.storage.local.get([STORAGE_KEY, "closedTabIds"], (res) => {
        if (res[STORAGE_KEY] === false) return;

        if (tabId === currentActiveTabId) {
            updateCurrentTabMetrics();
            currentActiveTabId = null;
        }

        if (tabMetrics[tabId]) {
            const closedLog = res.closedTabIds || [];
            closedLog.push({ tabId: String(tabId), closedAt: Date.now() });
            chrome.storage.local.set({ closedTabIds: closedLog });
        }
    });
});

setInterval(sendLogToServer, 60000);