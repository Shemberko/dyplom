chrome.runtime.onMessage.addListener((message) => {
    if (message.tabId) {
        const getPageText = () => {
        let text = "";

        // 1. Спроба отримати текст з основного семантичного елемента
        const mainEl = document.querySelector("article, main, section, [role='main']");
        
        if (mainEl) {
            const clonedEl = mainEl.cloneNode(true);
            // Видалення елементів, які зазвичай не є частиною основного контенту
            clonedEl.querySelectorAll("nav, aside, footer, header, script, style, .sidebar, .ad, .advertisement, [aria-label='Related content']").forEach(el => el.remove());
            
            text = clonedEl.innerText;
        }

        // 2. Резервний варіант (Fallback) 1: найбільший <p>, якщо основного тексту немає або його занадто мало
        if (text.trim().length < 50) {
            const paragraphs = Array.from(document.querySelectorAll("p"));
            if (paragraphs.length) {
                // Фільтруємо дуже короткі або порожні параграфи
                const relevantParagraphs = paragraphs.filter(p => p.innerText.trim().length > 50);
                if (relevantParagraphs.length) {
                    // Знаходимо параграф з найбільшою кількістю символів
                    const largestP = relevantParagraphs.reduce((a, b) => a.innerText.length > b.innerText.length ? a : b);
                    text = largestP.innerText;
                }
            }
        }

        // 3. Фінальний резервний варіант (Fallback) 2: очищений body
        if (text.trim().length < 50) {
            const bodyClone = document.body.cloneNode(true);
            // Видаляємо багато шуму з body
            bodyClone.querySelectorAll("nav, aside, footer, header, script, style").forEach(el => el.remove());
            text = bodyClone.innerText;
        }
        
        // 4. Очищення та обрізання результату
        return text.trim().replace(/\s+/g, ' ').slice(0, 1000);
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