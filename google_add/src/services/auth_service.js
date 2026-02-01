export function initAuthService(authUrl) {
    
    const getUserIdAndGenerateToken = () => {
        return new Promise((resolve, reject) => {
            chrome.identity.getProfileUserInfo(async function (userInfo) {
                if (chrome.runtime.lastError) {
                    return reject(new Error(chrome.runtime.lastError.message));
                }
                if (!userInfo || !userInfo.id) {
                    return reject(new Error("User ID not found via Chrome Identity."));
                }

                const userId = userInfo.id;

                try {
                    const response = await fetch(`${authUrl}/sso/generate-one-time-token`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ userId: userId })
                    });

                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({}));
                        throw new Error(`API Error: ${response.status} - ${errorData.detail || 'Failed'}`);
                    }

                    const data = await response.json();

                    if (data && data.oneTimeToken) {
                        resolve({ oneTimeToken: data.oneTimeToken });
                    } else {
                        reject(new Error("No token in response."));
                    }

                } catch (error) {
                    console.error("[AuthService] Token generation failed:", error);
                    reject(new Error(error.message || "Unknown error"));
                }
            });
        });
    };

    // Слухач для отримання запиту від попапа або контент-скрипта
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === "REQUEST_SSO_TOKEN") {
            getUserIdAndGenerateToken()
                .then(response => sendResponse(response))
                .catch(error => sendResponse({ error: error.message }));
            
            return true; // Keep channel open for async response
        }
    });

    console.log("[AuthService] Initialized");
}