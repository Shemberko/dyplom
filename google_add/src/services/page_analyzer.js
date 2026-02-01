chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    const tabId = message.tabId || sender.tab?.id;

    if (tabId) {
        const findPreviewImage = () => {
            const metaImg = document.querySelector("meta[property='og:image']")?.content ||
                            document.querySelector("meta[name='twitter:image']")?.content ||
                            document.querySelector("link[rel='image_src']")?.href;

            if (metaImg) {
                try { return new URL(metaImg, location.href).href; } catch (e) {}
            }

            const candidates = Array.from(document.querySelectorAll('img'));
            
            for (const img of candidates) {
                const src = img.currentSrc || img.src;

                if (!src || src.startsWith('data:')) continue;

                const lower = src.toLowerCase();
                if (['icon', 'logo', 'sprite', 'avatar', 'blank'].some(bad => lower.includes(bad))) continue;
                if (img.complete && (img.naturalWidth < 150 || img.naturalHeight < 150)) continue;

                try { return new URL(src, location.href).href; } catch (e) {}
            }

            const fav = document.querySelector("link[rel~='icon']")?.href;
            if (fav) try { return new URL(fav, location.href).href; } catch (e) {}

            return ""; 
        };

        const getPageText = () => {
            const contentCandidate = document.querySelector("article") || 
                                     document.querySelector("main") || 
                                     document.querySelector("[role='main']") || 
                                     document.body;

            if (!contentCandidate) return "";

            const clone = contentCandidate.cloneNode(true);
            const junkSelectors = [
                "nav", "header", "footer", "aside", "script", "style", "noscript", "iframe", "svg",
                ".ad", ".ads", ".advertisement", ".social-share", ".cookie-banner", ".popup",
                "[aria-hidden='true']", "[role='alert']"
            ];
            clone.querySelectorAll(junkSelectors.join(",")).forEach(el => el.remove());
            let text = clone.innerText; 
            
            return text.replace(/[\r\n\t]+/g, ' ').replace(/\s\s+/g, ' ').trim().slice(0, 2000); // Збільшив ліміт до 2000
        };

        const info = {
            url: window.location.href,
            previewImage: findPreviewImage(),
            title: document.title || "",
            metaDescription: document.querySelector("meta[name='description']")?.content || "",
            textSample: getPageText(),
            tabId: tabId
        };

        console.log("[page_analyzer] Extracted:", info);

        chrome.storage.local.get(["activityParsedData"], (result) => {
            let log = result.activityParsedData || [];
            const existingIndex = log.findIndex(entry => entry.info.tabId === tabId);
            const newEntry = { info: info, timestamp: Date.now() };

            if (existingIndex !== -1) {
                log[existingIndex] = newEntry;
            } else {
                log.push(newEntry);
            }

            chrome.storage.local.set({ activityParsedData: log }, () => {
                 if (chrome.runtime.lastError) console.error(chrome.runtime.lastError);
            });
        });
    }
    
    return true; 
});