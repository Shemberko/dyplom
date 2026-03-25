import { defineStore } from 'pinia';
import { ref } from 'vue';
import { api } from '@/composables/api';

export interface HistoryItem {
  id: string;
  url: string;
  title: string;
  image: string | null;
  last_visited: string;
  visit_count: number;
}

export const useHistoryStore = defineStore('history', () => {
  const { getData, deleteData } = api();

  const historyItems = ref<HistoryItem[]>([]);
  const isLoading = ref(false);
  const serverPage = ref(1);
  const SERVER_SIZE = 20;
  const hasMore = ref(true);

  async function fetchHistory(days = 7) {
    if (isLoading.value || !hasMore.value) return;
    
    isLoading.value = true;
    console.log('Fetching history...');
    
    try {
      const response = await getData('/history', {
        page: serverPage.value,
        size: SERVER_SIZE,
        days: days
      });
      
      console.log('API Response:', response);
      
      // Надійно дістаємо масив. Якщо раптом бекенд повертає axios-об'єкт, 
      // ми це теж перехопимо (response?.data?.data)
      let newItems: HistoryItem[] = [];
      if (Array.isArray(response?.data)) {
        newItems = response.data;
      } else if (response?.data?.data && Array.isArray(response.data.data)) {
        newItems = response.data.data;
      }

      console.log('Parsed new items:', newItems);
      
      if (newItems.length > 0) {
        // КЛЮЧОВА ЗМІНА: Переприсвоюємо масив замість .push()
        // Це 100% змусить Vue та всі computed-властивості оновити UI
        historyItems.value = [...historyItems.value, ...newItems];
        
        // Дістаємо meta з урахуванням можливої вкладеності
        const meta = response?.meta || response?.data?.meta;
        hasMore.value = meta?.has_next ?? false;
        
        serverPage.value++;
      } else {
        hasMore.value = false;
      }
      
      console.log('Store items after update:', historyItems.value);
    } catch (e) {
      console.error('Помилка завантаження історії:', e);
    } finally {
      isLoading.value = false;
    }
  }

  async function removeItem(pageId: string) {
    // Оптимістичне видалення з UI
    historyItems.value = historyItems.value.filter(item => item.id !== pageId);
    try {
      await deleteData(`/history/${pageId}`);
    } catch (e) {
      console.error('Помилка при видаленні з історії:', e);
    }
  }

  return {
    historyItems,
    isLoading,
    hasMore,
    fetchHistory,
    removeItem
  };
});