import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '@/composables/api';

export interface PageRecommendation {
  id: string;
  url: string;
  title: string;
  image: string | null;
  score: number;
  description?: string;
  type: string;
  visit_count?: number;
  last_visited?: string;
}

export const useRecommendationStore = defineStore('recommendations', () => {
  const { getData, postData } = api();

  const rawRecommendations = ref<PageRecommendation[]>([]);
  const visitedIds = ref<Set<string>>(new Set());
  
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

  async function visitRecommendation(pageId: string, userId: string) {
    visitedIds.value.add(pageId);
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
    rawRecommendations,
    isLoading,
    hasMoreOnServer,
    displayRecommendations,
    fetchNextBatch,
    visitRecommendation
  };
});