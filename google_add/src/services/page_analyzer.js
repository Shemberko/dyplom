chrome.runtime.onMessage.addListener((message) => {
    if (message.tabId) {
        const getPageText = () => {
            // Try to get main content from <article>, <main>, or <section>
            const mainEl = document.querySelector("article, main, section");
            if (mainEl) {
            return mainEl.innerText;
            }
            // Fallback: get largest <p> element
            const paragraphs = Array.from(document.querySelectorAll("p"));
            if (paragraphs.length) {
            const largestP = paragraphs.reduce((a, b) => a.innerText.length > b.innerText.length ? a : b);
            return largestP.innerText.slice(0, 1000);
            }
            // Final fallback: body text
            return document.body.innerText.slice(0, 1000);
        };

        const info = {
            url: window.location.href,
            title: document.title,
            metaDescription: document.querySelector("meta[name='description']")?.content || "",
            textSample: getPageText(),
            tabId: String(message.tabId)
        };

        console.log("[page_analyzer]Page info:", info);

        chrome.storage.local.get(["activityParsedData"], (result) => {
            const log = result.activityParsed || [];
            const existingIndex = log.findIndex(entry => entry.info.tabId === info.tabId);
            if (existingIndex !== -1) {
            log[existingIndex] = { info: info, timestamp: Date.now() };
            } else {
            log.push({ info: info, timestamp: Date.now() });
            }
            chrome.storage.local.set({ activityParsedData: log });
        });
    }
});