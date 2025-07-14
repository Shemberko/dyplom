chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    chrome.storage.local.get(["activityLog"], (result) => {
      const log = result.activityLog || [];
      log.push({ url: tab.url, timestamp: Date.now() });
    
      console.log("[background]Activity logged:", log);
      chrome.storage.local.set({ activityLog: log });
    });
  }
});
