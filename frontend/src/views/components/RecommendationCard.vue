<script setup lang="ts">
import { computed } from 'vue';
// Імпортуємо інтерфейс з вашого стора
import type { PageRecommendation } from '@/stores/recommendations';
import { Image as ImageIcon, ArrowRight } from 'lucide-vue-next'; // іконки

const props = defineProps<{
  rec: PageRecommendation;
}>();

// Форматуємо score (0.9954 -> 99.5%)
const formattedScore = computed(() => {
  return (props.rec.score * 100).toFixed(1) + '%';
});

// Витягуємо домен з URL (наприклад, "uk.wikipedia.org" з "https://uk.wikipedia.org/wiki/...")
const domain = computed(() => {
  try {
    return new URL(props.rec.url).hostname.replace('www.', '');
  } catch {
    return 'Зовнішній ресурс';
  }
});
</script>

<template>
  <a
    :href="rec.url"
    target="_blank"
    rel="noopener noreferrer"
    class="group flex flex-col bg-white rounded-2xl border border-gray-200 shadow-sm hover:shadow-lg transition-all duration-300 overflow-hidden h-full cursor-pointer focus:outline-none focus:ring-2 focus:ring-indigo-500"
  >
    <div class="relative h-48 w-full bg-gray-50 overflow-hidden">
      <img
        v-if="rec.image"
        :src="rec.image"
        :alt="rec.title"
        class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
      />
      <div v-else class="w-full h-full flex items-center justify-center text-gray-300">
        <ImageIcon class="w-12 h-12" stroke-width="1.5" />
      </div>

      <div class="absolute top-3 right-3 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-full shadow-sm flex items-center">
        <span class="text-xs font-bold text-emerald-600" title="Відсоток релевантності">
          {{ formattedScore }}
        </span>
      </div>
    </div>

    <div class="p-5 flex flex-col flex-grow">
      <p class="text-xs font-semibold text-indigo-600 mb-2 uppercase tracking-wider">
        {{ domain }}
      </p>

      <h3 class="text-lg font-bold text-gray-900 mb-3 line-clamp-2 group-hover:text-indigo-600 transition-colors">
        {{ rec.title }}
      </h3>

      <p v-if="rec.description" class="text-sm text-gray-600 line-clamp-3 mb-4 flex-grow">
        {{ rec.description }}
      </p>
      <div v-else class="flex-grow"></div> 

      <div class="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
        <span class="text-sm font-medium text-gray-500 group-hover:text-indigo-600 transition-colors flex items-center gap-1.5">
          Читати статтю
          <ArrowRight class="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
        </span>
      </div>
    </div>
  </a>
</template>