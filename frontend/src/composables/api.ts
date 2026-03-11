// composables/api.ts

import { storeToRefs } from 'pinia';
import axios, { AxiosError } from 'axios';
// *** ВИДАЛЕНО: import { jwtDecode } from 'jwt-decode'; ***

import { useUserStore } from '@/stores/user';
import { useNotificationStore } from '@/stores/notification';

const BACKEND_URL = 'http://127.0.0.1:8001';
const FRONTEND_APP_ORIGIN = 'http://localhost:5173';

const requestSsoTokenFromExtension = (): Promise<string> => {
    
    return new Promise((resolve, reject) => {
        
        const responseListener = (event: MessageEvent) => {            
            console.log('Отримано повідомлення від розширення:', event);

            if (event.origin !== FRONTEND_APP_ORIGIN || !event.data || event.data.action !== "SSO_RESPONSE_TO_FRONTEND") {
                return;
            }
            window.removeEventListener('message', responseListener);

            if (event.data.oneTimeToken) {
                resolve(event.data.oneTimeToken);
            } else {
                reject(new Error(event.data.error || "Невідома помилка при отриманні токена від розширення."));
            }
        };

        window.addEventListener('message', responseListener);

        try {
            console.log('Відправка запиту SSO до розширення через postMessage...');
            window.postMessage({ action: "REQUEST_SSO_FROM_FRONTEND" }, 'http://localhost:5173')
        } catch (e) {
            window.removeEventListener('message', responseListener);
            reject(new Error("Не вдалося ініціювати SSO-запит через postMessage."));
        }
    });
};


export const api = () => { 
    const userStore = useUserStore();
    const { token, isAuthenticated } = storeToRefs(userStore);
    const { setNotification } = useNotificationStore();

    const fetchUserProfile = async (jwtToken: string) => {
        try {
            const response = await axios.get(`${BACKEND_URL}/profile`, {
                headers: { 'Authorization': `Bearer ${jwtToken}` }
            });
            return response.data;
        } catch (e) {
            console.error('Помилка отримання профілю:', e);
            throw new Error("Не вдалося завантажити профіль користувача.");
        }
    };

    /**
     * Обмінює One-Time Token на постійний JWT, а потім отримує дані профілю.
     * @returns JWT Token.
     */
    const exchangeTokenAndSetAuth = async (oneTimeToken: string): Promise<string> => {
        try {
            const exchangeResponse = await axios.post(`${BACKEND_URL}/sso/exchange-token`, { token: oneTimeToken });
            const jwtToken = exchangeResponse.data.jwt;
            
            if (!jwtToken) throw new Error("API не повернув JWT.");
            
            const profileData = await fetchUserProfile(jwtToken);
            userStore.setAuthData(jwtToken, profileData.id, profileData.email);
            
            return jwtToken;
            
        } catch (error) {
            console.error('Помилка обміну токена/профілю:', error);
            userStore.logOut();
            throw new Error('Авторизація не вдалася: недійсний токен або профіль.');
        }
    }

    const ensureAuth = async (): Promise<string> => {
        

        if (token.value && (!userStore.user.id || !userStore.user.email)) {
             try {
                const profileData = await fetchUserProfile(token.value);
                userStore.setAuthData(token.value, profileData.id, profileData.email);
                return token.value;
             } catch (e) {
                 userStore.logOut();
             }
        }
        
        if (isAuthenticated.value && token.value) {
            return token.value;
        }

        try {
            console.log('Ініціалізація SSO через розширення браузера...');
            const oneTimeToken = await requestSsoTokenFromExtension(); 
            console.log('Отримано One-Time Token від розширення SSO.', oneTimeToken);
            const newJwt = await exchangeTokenAndSetAuth(oneTimeToken);
            return newJwt;

        } catch (error) {
            userStore.logOut();
            setNotification('Помилка авторизації. Спробуйте увійти знову.', 5000);
            throw new Error('Потрібна авторизація.');
        }
    };

   // -------------------------------------------------------------------------
    // ФУНКЦІЯ POST/FETCH
    // -------------------------------------------------------------------------
    const fetchData = async (url: string, initData: string, options: object = {}) => {
        
      console.log('fetchData called with URL:', url, 'initData:', initData, 'options:', options);
        const currentToken = await ensureAuth(); 
        console.log('Using JWT Token:', currentToken);
        const absoluteUrl = getAbsoluteUrl(url);

        const executeRequest = async (jwt: string) => {
            const headers = {
                'Authorization': `Bearer ${jwt}`,
                'Content-Type': 'application/json'
            };
            
            const payload = {
                ...(initData && { initData }),
                options: options
            };

            const { data } = await axios.post(absoluteUrl, payload, { headers }); 
            return data;
        };

        try {
            const data = await executeRequest(currentToken);
            
            if (data.locale?.error) {
                 console.error('Error fetching data:', data.locale.message);
                 setNotification(data.locale.message);
            }
            return data;
            
        } catch(error) {
            const axiosError = error as AxiosError;
            
            if (axiosError.response?.status === 401 || axiosError.code === 'ERR_NETWORK') {
                console.warn("JWT прострочений/недійсний. Спроба автоматичної повторної авторизації...");
                
                try {
                    const newToken = await ensureAuth(); 
                    const data = await executeRequest(newToken);
                    setNotification('Сесію успішно відновлено.', 3000);
                    return data;

                } catch (reAuthError) {
                    console.error('Критична помилка авторизації:', reAuthError);
                    userStore.logOut();
                    throw new Error('Сесія закінчилася. Потрібен повторний вхід.');
                }
            }
            
            console.error('Error fetching data:', error);
            throw error;
        }
    }

    // POST-ЗАПИТ
    const postData = async (url: string, body: Record<string, any> = {}) => {
        const currentToken = await ensureAuth(); 
        const absoluteUrl = getAbsoluteUrl(url);

        const executePost = async (jwt: string) => {
            const headers = {
                'Authorization': `Bearer ${jwt}`,
                'Content-Type': 'application/json'
            };

            const { data } = await axios.post(absoluteUrl, body, { headers }); 
            return data;
        };

        try {
            return await executePost(currentToken);
        } catch(error) {
            const axiosError = error as AxiosError;
            
            if (axiosError.response?.status === 401 || axiosError.code === 'ERR_NETWORK') {
                console.warn("POST: JWT прострочений/недійсний. Спроба автоматичної повторної авторизації...");
                
                try {
                    const newToken = await ensureAuth(); 
                    const data = await executePost(newToken);
                    setNotification('Сесію успішно відновлено.', 3000);
                    return data;
                } catch (reAuthError) {
                    console.error('Критична помилка авторизації:', reAuthError);
                    userStore.logOut();
                    throw new Error('Сесія закінчилася. Потрібен повторний вхід.');
                }
            }
            
            console.error('Error posting data:', error);
            throw error;
        }
    }

    const getAbsoluteUrl = (url: string): string => {
      const base = BACKEND_URL.endsWith('/') ? BACKEND_URL.slice(0, -1) : BACKEND_URL;
      const path = url.startsWith('/') ? url : `/${url}`;
      return `${base}${path}`;
    };


    const deleteData = async (url: string, id: number) => {
        
        const currentToken = await ensureAuth(); 
        const absoluteUrl = getAbsoluteUrl(url);
        const executeDelete = async (jwt: string) => {
            const headers = { 'Authorization': `Bearer ${jwt}` };
            const { data } = await axios.delete(`${absoluteUrl}/${id}`, { headers }); 
            return data;
        };

        try {
            const data = await executeDelete(currentToken);
            
            if (data.locale?.error) {
                console.error('Error deleting data:', data.locale.message);
                setNotification(data.locale.message);
            }
            if (data.notification) {
                setNotification(data.notification);
            }
            return data;
            
        } catch (error) {
            const axiosError = error as AxiosError;
            
            if (axiosError.response?.status === 401) {
                console.warn("DELETE: JWT прострочений. Спроба повторної авторизації...");
                
                try {
                    const newToken = await ensureAuth(); 
                    const data = await executeDelete(newToken);
                    setNotification('Сесію успішно відновлено.', 3000);
                    return data;
                    
                } catch (reAuthError) {
                    userStore.logOut();
                    throw new Error('Сесія закінчилася. Потрібен повторний вхід.');
                }
            }
            
            console.error('Error deleting data:', error);
            throw error;
        }
    };


    const getData = async (url: string, params: Record<string, any> = {}) => {
    const currentToken = await ensureAuth(); 
    const absoluteUrl = getAbsoluteUrl(url);

    const executeGet = async (jwt: string) => {
        const headers = {
            'Authorization': `Bearer ${jwt}`,
            'Content-Type': 'application/json'
        };

        const { data } = await axios.get(absoluteUrl, { 
            headers, 
            params
        }); 
        return data;
    };

    try {
        return await executeGet(currentToken);
    } catch(error) {
         const axiosError = error as AxiosError;
            
            if (axiosError.response?.status === 401 || axiosError.code === 'ERR_NETWORK') {
                
                console.warn("GET: JWT прострочений/недійсний. Спроба автоматичної повторної авторизації...");
                
                try {
                    const newToken = await ensureAuth(); 
                    const data = await executeGet(newToken);
                    setNotification('Сесію успішно відновлено.', 3000);
                    return data;

                } catch (reAuthError) {
                    console.error('Критична помилка авторизації:', reAuthError);
                    userStore.logOut();
                    throw new Error('Сесія закінчилася. Потрібен повторний вхід.');
                }
            }
            
            console.error('Error fetching data:', error);
            throw error;
    }
}

    return {
        postData,
        getData,
        fetchData,
        deleteData,
        ensureAuth,
        exchangeTokenAndSetAuth
    };
}
