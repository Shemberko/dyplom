import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '@/composables/api';

// Інтерфейс (як ми обговорювали раніше)
export interface PageRecommendation {
  id: string;
  url: string;
  title: string;
  image: string | null;
  score: number;
  description?: string;
}

export const useRecommendationStore = defineStore('recommendations', () => {
  const { getData, postData } = api();

  const rawRecommendations = ref<PageRecommendation[]>([]);
  const visitedIds = ref<Set<string>>(new Set());
  
  // Стан пагінації сервера
  const serverPage = ref(1);
  const SERVER_SIZE = 100;
  const isLoading = ref(false);
  const hasMoreOnServer = ref(true);


  const displayRecommendations = computed(() => {
    return rawRecommendations.value.filter(
      (page) => !visitedIds.value.has(page.id)
    );
  });

  async function fetchNextBatch() {
    if (isLoading.value || !hasMoreOnServer.value) return;
    
    isLoading.value = true;
    try {
      const response = await getData('/recommendations', { 
        page: serverPage.value, 
        size: SERVER_SIZE 
      });

      const newItems: PageRecommendation[] = response?.data || [];
      
      if (newItems.length > 0) {
        // Додаємо нові елементи до існуючих
        rawRecommendations.value.push(...newItems);
        
        hasMoreOnServer.value = response?.meta?.has_next ?? (newItems.length === SERVER_SIZE);
        serverPage.value++;
      } else {
        hasMoreOnServer.value = false;
      }
    } catch (e) {
      console.error("Помилка при завантаженні з сервера:", e);
      hasMoreOnServer.value = false;
    } finally {
      isLoading.value = false;
    }
  }

  // Клік по рекомендації
  async function visitRecommendation(pageId: string, userId: string) {
    // Оптимістичне приховування
    visitedIds.value.add(pageId);
    
    // Або повне видалення з пам'яті (радію, що ви обрали цей варіант!):
    rawRecommendations.value = rawRecommendations.value.filter(p => p.id !== pageId);

    try {
      await postData('/recommendations/visit', {
        user_id: userId,
        page_id: pageId,
        source: 'recommendation'
      });
    } catch (err) {
      console.error('Не вдалося записати візит:', err);
    }
  }

  return {
    isLoading,
    hasMoreOnServer,
    displayRecommendations,
    fetchNextBatch,
    visitRecommendation
  };
});