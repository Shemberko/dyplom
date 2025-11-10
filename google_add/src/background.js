let API_URL = "http://127.0.0.1:8000"; // <-- Replace with your actual API URL

let tabDurations = {}; // { tabId: { opened: timestamp, active: ms, lastActive: timestamp, totalOpen: ms } }
let activeTabId = null;

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (
    changeInfo.status === "complete" &&
    tab.url &&
    !tab.url.startsWith("chrome://")
  ) {
    const now = Date.now();
     tabDurations[tabId] = { opened: now, active: 0, lastActive: now, totalOpen: 0 };
     activeTabId = tabId;

    chrome.scripting.executeScript({
      target: { tabId: tabId },
      files: ["services/page_analyzer.js"]
    }).then(() => {
      chrome.tabs.sendMessage(tabId, { tabId: tabId });
    });
  }
});
// Track tab open and active durations, and update activityParsed every minute

// When a tab is activated
chrome.tabs.onActivated.addListener(({ tabId }) => {
  const now = Date.now();
  if (!tabDurations[tabId]) {
    tabDurations[tabId] = { opened: now, active: 0, lastActive: now, totalOpen: 0 };
  } else {
    // If previously inactive, set lastActive
    tabDurations[tabId].lastActive = now;
  }
  activeTabId = tabId;
});

// When browser loses focus
chrome.windows.onFocusChanged.addListener((windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE && activeTabId !== null) {
    const tabData = tabDurations[activeTabId];
    if (tabData && tabData.lastActive) {
      tabData.active += Date.now() - tabData.lastActive;
      tabData.lastActive = null;
    }
    activeTabId = null;
  }
});

// When tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  const tabData = tabDurations[tabId];
  if (tabData) {
    if (tabData.lastActive) {
      tabData.active += Date.now() - tabData.lastActive;
      tabData.lastActive = null;
    }
    tabData.totalOpen = Date.now() - tabData.opened;
  }
});

// Update durations and activityParsed every minute
setInterval(() => {
  const now = Date.now();
  for (const tabId in tabDurations) {
    const tab = tabDurations[tabId];
    // Update totalOpen
    tab.totalOpen = now - tab.opened;
    // Update active time if tab is currently active
    if (activeTabId == tabId && tab.lastActive) {
      tab.active += now - tab.lastActive;
      tab.lastActive = now;
    }
    tab.opened = now;
  }

  // Update activityParsed in storage
  chrome.storage.local.get(["activityParsedTime"], (result) => {
    const activityParsed = result.activityParsedTime || [];
    chrome.storage.local.set({log: activityParsed})
    for (const tabId in tabDurations) {
       const tab = tabDurations[tabId];
      // Find or create entry for tabId (search by int)
      let entry = activityParsed.find(e => String(e.info.tabId) == tabId);
      if (!entry) {
      entry = { info: {tabId: tabId, active: tab.active, totalOpen: tab.totalOpen} };
      activityParsed.push(entry);
      }
      // Add (not overwrite) durations
      entry.info.totalOpen += tab.totalOpen;
      entry.info.active += tab.active;

      // Reset durations in memory
      tab.totalOpen = 0;
      tab.active = 0;
    }
    chrome.storage.local.set({ activityParsedTime: activityParsed});
  });
}, 60000); 










function sendLogToServer() {
    chrome.identity.getProfileUserInfo((info) => {
      chrome.storage.local.get(["activityParsedData", "activityParsedTime"], (result) => {
        const data = result.activityParsedData || [];
        const time = result.activityParsedTime || [];
        // Create maps for fast lookup by tabId
        const dataMap = new Map(data.map(e => [String(e.info.tabId), e]));
        const timeMap = new Map(time.map(e => [String(e.info.tabId), e]));
        // Only include entries present in both
        const log = [];
        for (const [tabId, dataEntry] of dataMap.entries()) {
          if (timeMap.has(tabId)) {
            // Merge info objects (shallow merge)
            log.push({
              info: { ...dataEntry.info, ...timeMap.get(tabId).info }
            });
          }
        }
        if (log.length === 0) return;

        const payload = {
          user: {
            info: info
          },
          log
        };

        let url = API_URL + "/data/post-collected-data";

        fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        })
        .then(response => {
          if (response.ok) {
            console.log("[background]Activity log sent to server");

            chrome.storage.local.set({ activityParsedTime: [] });
            localStorage.setItem("activityLog", "[]");
          } else {
            console.error("[background]Failed to send activity log");
          }
        })
        .catch(error => {
          console.error("[background]Error sending activity log:", error);
        });
      });
    });
  
}

// Send log every 10 minutes (600,000 ms)
setInterval(sendLogToServer, 5000);