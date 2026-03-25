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
  <div class="relative min-h-screen w-full bg-[#F8FAFC] overflow-hidden z-0">
    
    <div class="fixed inset-0 w-full h-full pointer-events-none -z-10">
        <div class="absolute top-[-10%] left-[-5%] w-[400px] h-[400px] bg-indigo-200/40 rounded-full mix-blend-multiply filter blur-[100px] animate-blob"></div>
        <div class="absolute bottom-[20%] right-[-5%] w-[500px] h-[500px] bg-purple-200/40 rounded-full mix-blend-multiply filter blur-[100px] animate-blob animation-delay-2000"></div>
    </div>

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-12 relative z-10">
      
      <div v-if="visibleItems.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <RecommendationCard 
              v-for="item in visibleItems" 
              :key="item.id" 
              :rec="item" 
              @click="store.visitRecommendation(item.id, 'user_123')"
              class="animate-fade-in-up"
          />
      </div>

      <div v-else-if="!isLoading" class="flex flex-col items-center justify-center py-32 text-slate-400">
          <div class="w-20 h-20 mb-6 bg-white/50 backdrop-blur-md rounded-3xl flex items-center justify-center shadow-sm border border-white">
              <Loader2 class="w-8 h-8 opacity-50" />
          </div>
          <p class="text-lg font-medium">Рекомендацій поки немає</p>
      </div>

      <div id="load-more-sentinel" class="h-32 flex flex-col items-center justify-center mt-10">
          <div v-if="isLoading" class="bg-white/80 backdrop-blur-md p-3 rounded-full shadow-sm border border-white">
              <Loader2 class="h-6 w-6 animate-spin text-indigo-600" />
          </div>
          <div v-if="!hasMoreOnServer && visibleItems.length > 0 && visibleCount >= displayRecommendations.length" class="text-sm font-medium text-slate-400 bg-white/50 backdrop-blur-md px-6 py-2 rounded-full border border-white/60">
            Ви переглянули всі матеріали
          </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.animate-fade-in-up {
    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) backwards;
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-blob {
    animation: blob 10s infinite alternate cubic-bezier(0.4, 0, 0.2, 1);
}
.animation-delay-2000 {
    animation-delay: 2s;
}

@keyframes blob {
    0% { transform: translate(0px, 0px) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
    100% { transform: translate(0px, 0px) scale(1); }
}
</style>