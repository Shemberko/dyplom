// stores/user.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';
export const useUserStore = defineStore('user', () => {
    const token = ref(null);
    const user = ref({ id: null, email: null });
    const isAuthenticated = ref(false);
    function setAuthData(jwtToken, userId, userEmail) {
        token.value = jwtToken;
        user.value.id = userId;
        user.value.email = userEmail;
        isAuthenticated.value = true;
        localStorage.setItem('jwt_token', jwtToken);
    }
    function logOut() {
        token.value = null;
        user.value.id = null;
        user.value.email = null;
        isAuthenticated.value = false;
        localStorage.removeItem('jwt_token');
    }
    function initializeAuth() {
        const storedToken = localStorage.getItem('jwt_token');
        if (storedToken) {
            token.value = storedToken;
            isAuthenticated.value = true;
        }
    }
    return {
        token,
        user,
        isAuthenticated,
        logOut,
        setAuthData,
        initializeAuth,
    };
});
