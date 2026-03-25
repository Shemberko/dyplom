import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/composables/api';

export const useStatsStore = defineStore('stats', () => {
  const { getData } = api();
  
  const totalUsers = ref(0);
  const totalPages = ref(0);
  const isLoaded = ref(false);

  async function fetchStats() {
    if (isLoaded.value) return;
    
    try {
      const response = await getData('/stats');
      totalUsers.value = response.total_users || 0;
      totalPages.value = response.total_pages || 0;
      isLoaded.value = true;
    } catch (e) {
      console.error('Помилка завантаження статистики:', e);
    }
  }

  return { totalUsers, totalPages, fetchStats };
});