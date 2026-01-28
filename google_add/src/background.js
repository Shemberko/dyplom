let API_URL = "http://127.0.0.1:8000"; // <-- Replace with your actual API URL
let AUTH_URL = "http://127.0.0.1:8001";

let tabDurations = {}; // { tabId: { opened: timestamp, active: ms, lastActive: timestamp, totalOpen: ms } }
let activeTabId = null;
const STORAGE_KEY = 'tracking_enabled'; // Replace with your actual storage key

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
 chrome.storage.local.get([STORAGE_KEY], (result) => {
    // Якщо значення === false, ми просто виходимо з функції і нічого не надсилаємо
    if (result[STORAGE_KEY] === false) {
        // console.log('Клік проігноровано, бо розширення вимкнено');
        return;
    }

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
});
// Track tab open and active durations, and update activityParsed every minute


chrome.tabs.onActivated.addListener(({ tabId }) => {
 chrome.storage.local.get([STORAGE_KEY], (result) => {
    // Якщо значення === false, ми просто виходимо з функції і нічого не надсилаємо
    if (result[STORAGE_KEY] === false) {
        // console.log('Клік проігноровано, бо розширення вимкнено');
        return;
    }
    const now = Date.now();
    if (!tabDurations[tabId]) {
      tabDurations[tabId] = { opened: now, active: 0, lastActive: now, totalOpen: 0 };
    } else {
      // If previously inactive, set lastActive
      tabDurations[tabId].lastActive = now;
    }
    activeTabId = tabId;
  });
});

// When browser loses focus
chrome.windows.onFocusChanged.addListener((windowId) => {
 chrome.storage.local.get([STORAGE_KEY], (result) => {
    // Якщо значення === false, ми просто виходимо з функції і нічого не надсилаємо
    if (result[STORAGE_KEY] === false) {
        // console.log('Клік проігноровано, бо розширення вимкнено');
        return;
    }

    if (windowId === chrome.windows.WINDOW_ID_NONE && activeTabId !== null) {
      const tabData = tabDurations[activeTabId];
      if (tabData && tabData.lastActive) {
        tabData.active += Date.now() - tabData.lastActive;
        tabData.lastActive = null;
      }
      activeTabId = null;
    }
  });
});

// When tab is closed
// ...existing code...
chrome.tabs.onRemoved.addListener((tabId) => {
  chrome.storage.local.get([STORAGE_KEY], (result) => {
    // Якщо значення === false, ми просто виходимо з функції і нічого не надсилаємо
    if (result[STORAGE_KEY] === false) {
      return;
    }

    const tabData = tabDurations[tabId];
    if (tabData) {
      if (tabData.lastActive) {
        tabData.active += Date.now() - tabData.lastActive;
        tabData.lastActive = null;
      }
      tabData.totalOpen = Date.now() - tabData.opened;
    }

    const sid = String(tabId);
    const record = { tabId: sid, closedAt: Date.now() };

    chrome.storage.local.get(["closedTabIds"], (stored) => {
      const closed = stored.closedTabIds || [];
      const idx = closed.findIndex(c => String(c.tabId) === sid);
      if (idx === -1) {
        closed.push(record);
      } else {
        // оновити час закриття, якщо запис уже є
        closed[idx].closedAt = record.closedAt;
      }
      chrome.storage.local.set({ closedTabIds: closed }, () => {
        console.log("[background]Saved closed tab id", sid);
      });
    });
  });
});

// Update durations and activityParsed every minute
setInterval(() => {
  chrome.storage.local.get([STORAGE_KEY], (result) => {
    // Якщо значення === false, ми просто виходимо з функції і нічого не надсилаємо
    // if (result[STORAGE_KEY] === false) {
    //   return;
    // }

    const now = Date.now();
    chrome.storage.local.get(['closedTabIds'], (stored) => {
      const closed = stored.closedTabIds || [];
      const closedSet = new Set(closed.map(c => String(c.tabId)));
      for (const tabId in tabDurations) {
        if (closedSet.has(String(tabId))) continue;
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
    });

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
  });
}, 60000); 

function sendLogToServer() {
  chrome.storage.local.get([STORAGE_KEY], (result) => {
    // Якщо значення === false, ми просто виходимо з функції і нічого не надсилаємо
    if (result[STORAGE_KEY] === false) {
      return;
    }
    
    chrome.identity.getProfileUserInfo((info) => {
      chrome.storage.local.get(["activityParsedData", "activityParsedTime", "closedTabIds"], (result) => {
        const data = result.activityParsedData || [];
        const time = result.activityParsedTime || [];
        const closed = result.closedTabIds || []; // [{tabId, closedAt}, ...]


        const dataMap = new Map(data.map(e => [String(e.info.tabId), e]));
        const timeMap = new Map(time.map(e => [String(e.info.tabId), e]));

        const log = [];
        for (const [tabId, dataEntry] of dataMap.entries()) {
          if (timeMap.has(tabId)) {
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
            const closedIds = new Set((closed || []).map(c => String(c.tabId)));
            const newTime = time.filter(e => !closedIds.has(String(e.info.tabId)));
            const newData = data.filter(e => !closedIds.has(String(e.info.tabId)));
            // clear closedTabIds
            chrome.storage.local.set({
              activityParsedTime: newTime,
              activityParsedData: newData,
              closedTabIds: []
            }, () => {
              console.log("[background]Removed closed tabs from storage:", Array.from(closedIds));
            });
          } else {
            console.error("[background]Failed to send activity log");
          }
        })
        .catch(error => {
          console.error("[background]Error sending activity log:", error);
        });
      });
    });
  });  
}

// Send log every 10 minutes (600,000 ms)
setInterval(sendLogToServer, 6000);


const getUserIdAndGenerateToken = () => {
    
    // Повертаємо Promise, який буде розв'язано або відхилено (resolve/reject)
    // усередині callback-функції chrome.identity.
    return new Promise((resolve, reject) => {
        
        // 1. Отримуємо ID користувача Chrome Identity
        chrome.identity.getProfileUserInfo(async function(userInfo) {
            
            // Якщо є помилка Runtime або відсутній ID
            if (chrome.runtime.lastError) {
                return reject(new Error(chrome.runtime.lastError.message));
            }
            if (!userInfo.id) {
                return reject(new Error("Помилка: Не вдалося отримати ID користувача Chrome (порожній ID)."));
            }

            const userId = userInfo.id; 
            
            // 2. Виконуємо fetch запит (використовуємо async/await всередині callback)
            try {
                const response = await fetch(`${AUTH_URL}/sso/generate-one-time-token`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId: userId })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(`API Error: ${response.status} - ${errorData.detail || 'Failed to generate token.'}`);
                }
                
                const data = await response.json();
                
                if (data && data.oneTimeToken) {
                    // Успіх: Розв'язуємо Promise, повертаючи об'єкт
                    resolve({ oneTimeToken: data.oneTimeToken });
                } else {
                    reject(new Error("API не повернув одноразовий токен у відповідному форматі."));
                }
                
            } catch (error) {
                console.error("SSO Token Generation Failed:", error);
                // Помилка: Відхиляємо Promise
                reject(new Error(error.message || "Невідома помилка генерації токена."));
            }
        });
    });
};

// ----------------------------------------------------------------------
// Слухач chrome.runtime.onMessage залишається без змін:
// ----------------------------------------------------------------------

chrome.runtime.onMessage.addListener(
    (request, sender, sendResponse) => {
        
        if (request.action === "REQUEST_SSO_TOKEN") {
            
            // Тепер getUserIdAndGenerateToken гарантовано повертає Promise
            getUserIdAndGenerateToken()
                .then(response => {
                    sendResponse(response);
                })
                .catch(error => {
                    sendResponse({ error: error.message });
                });
            
            return true; // Зберігаємо Service Worker живим
        }
    }
);