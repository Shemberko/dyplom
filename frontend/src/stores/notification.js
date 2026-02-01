import { defineStore } from 'pinia';
import { ref } from 'vue';
export const useNotificationStore = defineStore('nofication', () => {
    const open = ref(false);
    const message = ref('');
    const setNotification = (text, timeout = 1000) => {
        open.value = true;
        message.value = text;
        setTimeout(() => open.value = false, timeout);
    };
    return {
        open,
        message,
        setNotification
    };
});
