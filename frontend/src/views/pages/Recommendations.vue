<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { Search, Loader2 } from 'lucide-vue-next';
import { api } from '@/composables/api';
import { useUserStore } from '@/stores/user';
import { storeToRefs } from 'pinia';

import RecommendationCard from '../components/RecommendationCard.vue';
import MyPagination from '../components/MyPagination.vue';

const { getData } = api();
const userStore = useUserStore();
const { user } = storeToRefs(userStore);

const recommendations = ref<any[] | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const searchQuery = ref('');
const currentPage = ref(1);
const itemsPerPage = 6;
const RECOMMENDATIONS_URL = '/recommendations';



const filteredRecommendations = computed(() => {
  if (!recommendations.value) return [];
  if (!searchQuery.value) return recommendations.value;
  
  const query = searchQuery.value.toLowerCase();
  return recommendations.value.filter((rec: any) => 
    (rec.title && rec.title.toLowerCase().includes(query)) ||
    (rec.description && rec.description.toLowerCase().includes(query))
  );
});

// Розрахунок кількості сторінок
const totalPages = computed(() => 
  Math.ceil(filteredRecommendations.value.length / itemsPerPage)
);

// Отримання елементів для поточної сторінки
const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return filteredRecommendations.value.slice(start, end);
});

// Скидання сторінки на 1 при пошуку
watch(searchQuery, () => {
  currentPage.value = 1;
});

// ... (логіка filteredRecommendations, totalPages, paginatedItems залишається такою ж)
const fetchRecommendations = async () => {
    loading.value = true;
    error.value = null;
    recommendations.value = null;

    try {
        const response = await getData(RECOMMENDATIONS_URL); 
        console.log('Отримані рекомендації:', response);
        
        if (response && response.data) {
            recommendations.value = response.data;
        } else {
            recommendations.value = [];
        }

    } catch (e: any) {
        error.value = e.message || "Не вдалося завантажити рекомендації.";
        console.error('Помилка завантаження рекомендацій:', e);
    } finally {
        loading.value = false;
    }
};


onMounted(fetchRecommendations);
watch(searchQuery, () => currentPage.value = 1);
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-10 px-4">
    <div class="max-w-6xl mx-auto">
      
      <header class="text-center mb-10">
        <h1 class="text-4xl font-extrabold mb-3">Tab Insights</h1>
        <p class="text-gray-500">Вітаємо, {{ user.email }}. Ось ваші рекомендації.</p>
      </header>

      <div class="max-w-xl mx-auto mb-12 relative">
        <div class="relative group">
          <Search class="absolute left-4 top-3.5 h-5 w-5 text-gray-400" />
          <input v-model="searchQuery" type="text" placeholder="Filter recommendations..." class="w-full pl-11 pr-4 py-3 border rounded-xl focus:ring-2 focus:ring-blue-500 outline-none shadow-sm" />
        </div>
      </div>

      <div v-if="loading" class="flex flex-col items-center py-20">
        <Loader2 class="h-10 w-10 text-blue-600 animate-spin mb-4" />
        <p class="text-gray-500">Завантаження...</p>
      </div>

      <div v-else-if="error" class="text-center py-10 bg-red-50 rounded-xl border border-red-100">
        <p class="text-red-600 mb-4">{{ error }}</p>
        <button @click="fetchRecommendations" class="px-4 py-2 bg-white text-red-600 border border-red-200 rounded-lg">Спробувати ще</button>
      </div>

      <div v-else-if="recommendations?.length">
        <div v-if="paginatedItems.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <RecommendationCard 
            v-for="item in paginatedItems" 
            :key="item.id" 
            :rec="item" 
          />
        </div>
        
        <div v-else class="text-center py-10 text-gray-500">
          Нічого не знайдено за запитом "{{ searchQuery }}"
        </div>

        <MyPagination 
          v-if="totalPages > 1"
          v-model:current="currentPage"
          :total="totalPages"
        />
      </div>

    </div>
  </div>
</template>