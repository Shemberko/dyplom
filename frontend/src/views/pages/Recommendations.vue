<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue';
import { storeToRefs } from 'pinia';
import { useRecommendationStore } from '@/stores/recommendations';
import { Loader2 } from 'lucide-vue-next';
import RecommendationCard from '../components/RecommendationCard.vue';

const store = useRecommendationStore();

const { isLoading, hasMoreOnServer, displayRecommendations } = storeToRefs(store);

const LOCAL_STEP = 10;
const visibleCount = ref(LOCAL_STEP);

const visibleItems = computed(() => {
    return displayRecommendations.value.slice(0, visibleCount.value);
});

const loadMoreLocal = async () => {
    const totalAvailable = displayRecommendations.value.length;

    if (visibleCount.value < totalAvailable) {
        visibleCount.value += LOCAL_STEP;
    }

    const remainingInCache = totalAvailable - visibleCount.value;
    if (remainingInCache < 20 && hasMoreOnServer.value && !isLoading.value) {
        await store.fetchNextBatch();
    }
};

const setupIntersectionObserver = () => {
    const sentinel = document.getElementById('load-more-sentinel');
    if (!sentinel) return;

    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting && !isLoading.value) {
            loadMoreLocal();
        }
    }, { 
        rootMargin: '200px', 
        threshold: 0.01 
    });

    observer.observe(sentinel);
};

onMounted(async () => {
    if (displayRecommendations.value.length === 0) {
        await store.fetchNextBatch();
    }
    
    await nextTick();
    setupIntersectionObserver();
});
</script>

<template>
  <div class="min-h-screen max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    
    <div v-if="visibleItems.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <RecommendationCard 
            v-for="item in visibleItems" 
            :key="item.id" 
            :rec="item" 
            @click="store.visitRecommendation(item.id, 'user_123')"
        />
    </div>

    <div v-else-if="!isLoading" class="text-center py-20 text-gray-400">
        Рекомендацій поки немає
    </div>

    <div id="load-more-sentinel" class="h-32 flex flex-col items-center justify-center mt-10">
        <Loader2 v-if="isLoading" class="h-8 w-8 animate-spin text-indigo-600" />
        <div v-if="!hasMoreOnServer && visibleItems.length > 0 && visibleCount >= displayRecommendations.length" class="text-sm text-gray-400 italic">
          Ви переглянули всі матеріали
        </div>
    </div>
  </div>
</template>