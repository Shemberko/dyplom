<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { api } from '@/composables/api';
import { useUserStore } from '@/stores/user';
import { storeToRefs } from 'pinia';
import { Search, ExternalLink, ChevronLeft, ChevronRight, Loader2 } from 'lucide-vue-next';

const { getData } = api();
const userStore = useUserStore();
const { user } = storeToRefs(userStore);

const recommendations = ref<any[] | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const RECOMMENDATIONS_URL = '/recommendations';

const searchQuery = ref('');
const currentPage = ref(1);
const itemsPerPage = 6;

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

// --- Ваш оригінальний запит (без змін логіки) ---
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

onMounted(() => {
    fetchRecommendations();
});
</script>

<template>
    <div class="min-h-screen bg-gray-50 text-gray-900 font-sans py-10 px-4 sm:px-6 lg:px-8">
        
        <div class="max-w-6xl mx-auto">
            
            <div class="text-center mb-10">
                <h1 class="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl mb-3">
                    Tab Insights
                </h1>
                <p class="text-lg text-gray-500 max-w-2xl mx-auto">
                    <span v-if="user.email">Вітаємо, {{ user.email }}. </span>
                    Ось ваші персональні рекомендації. Відкривайте нове з історії переглядів.
                </p>
            </div>

            <div class="max-w-xl mx-auto mb-12 relative">
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <Search class="h-5 w-5 text-gray-400 group-focus-within:text-gray-600 transition-colors" />
                    </div>
                    <input 
                        v-model="searchQuery"
                        type="text"
                        class="block w-full pl-11 pr-4 py-3 bg-white border border-gray-200 rounded-xl leading-5 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm transition-shadow duration-200"
                        placeholder="Filter recommendations..."
                    />
                </div>
            </div>

            <div v-if="loading" class="flex flex-col items-center justify-center py-20">
                <Loader2 class="h-10 w-10 text-blue-600 animate-spin mb-4" />
                <p class="text-gray-500">Завантаження даних...</p>
            </div>

            <div v-else-if="error" class="text-center py-10 bg-red-50 rounded-xl border border-red-100">
                <p class="text-red-600 mb-4">Помилка: {{ error }}</p>
                <div class="space-x-4">
                    <button @click="fetchRecommendations" class="px-4 py-2 bg-white border border-red-200 text-red-600 rounded-lg hover:bg-red-50 transition">
                        Спробувати ще
                    </button>
                    <button @click="userStore.logOut()" class="px-4 py-2 text-gray-600 hover:text-gray-800 underline">
                        Вийти
                    </button>
                </div>
            </div>

            <div v-else-if="recommendations && recommendations.length > 0">
                
                <div v-if="paginatedItems.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    <article 
                        v-for="rec in paginatedItems" 
                        :key="rec.id" 
                        class="bg-white rounded-2xl shadow-sm hover:shadow-md border border-gray-100 overflow-hidden flex flex-col transition-all duration-300 hover:-translate-y-1 h-full"
                    >
                        <div class="h-48 w-full bg-gray-100 overflow-hidden relative">
                            <img 
                                v-if="rec.image" 
                                :src="rec.image" 
                                :alt="rec.title" 
                                class="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
                            />
                            <div v-else class="w-full h-full flex items-center justify-center bg-gray-200 text-gray-400">
                                <span class="text-sm">No Image</span>
                            </div>
                        </div>

                        <div class="p-6 flex flex-col flex-grow">
                            <h3 class="text-xl font-bold text-gray-900 mb-2 line-clamp-2 leading-tight">
                                {{ rec.title || 'Рекомендація' }}
                            </h3>
                            <p class="text-gray-500 text-sm leading-relaxed line-clamp-3 mb-6 flex-grow">
                                {{ rec.description || 'Опис відсутній.' }}
                            </p>

                            <a 
                                :href="rec.url || '#'" 
                                target="_blank" 
                                class="mt-auto w-full py-2.5 px-4 bg-gray-50 hover:bg-gray-100 text-gray-700 font-medium text-sm rounded-lg flex items-center justify-center transition-colors group"
                            >
                                Visit Page
                                <ExternalLink class="ml-2 h-3.5 w-3.5 text-gray-400 group-hover:text-gray-600" />
                            </a>
                        </div>
                    </article>
                </div>
                
                <div v-else class="text-center py-10">
                    <p class="text-gray-500">Нічого не знайдено за запитом "{{ searchQuery }}"</p>
                </div>

                <div v-if="totalPages > 1" class="mt-16 flex justify-center items-center space-x-4">
                    <button 
                        :disabled="currentPage === 1" 
                        @click="currentPage--"
                        class="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                        <ChevronLeft class="h-5 w-5" />
                    </button>
                    
                    <span class="text-sm font-medium text-gray-600 bg-white px-4 py-2 rounded-lg border border-gray-200 shadow-sm">
                        Page {{ currentPage }} of {{ totalPages }}
                    </span>
                    
                    <button 
                        :disabled="currentPage === totalPages" 
                        @click="currentPage++"
                        class="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                        <ChevronRight class="h-5 w-5" />
                    </button>
                </div>
            </div>

            <div v-else class="text-center py-20">
                <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
                    <Search class="h-8 w-8 text-gray-400" />
                </div>
                <h3 class="text-lg font-medium text-gray-900">Рекомендацій поки немає</h3>
                <button @click="fetchRecommendations" class="mt-4 text-blue-600 hover:underline">Оновити</button>
            </div>

        </div>
    </div>
</template>

<style scoped>
/* Стилі Tailwind працюють через класи, тут нічого писати не треба */
</style>


<!--

# Встановлення Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Встановлення пакету іконок (для лупи та стрілочок)
npm install lucide-vue-next
-->