<script setup lang="ts">
import { ExternalLink } from 'lucide-vue-next';

defineProps<{
  rec: {
    id: number | string;
    title?: string;
    description?: string;
    image?: string;
    url?: string;
  }
}>();
</script>

<template>
  <article class="bg-white rounded-2xl shadow-sm hover:shadow-md border border-gray-100 overflow-hidden flex flex-col transition-all duration-300 hover:-translate-y-1 h-full">
    <div class="h-48 w-full bg-gray-100 overflow-hidden relative">
      <img v-if="rec.image" :src="rec.image" :alt="rec.title" class="w-full h-full object-cover transition-transform duration-500 hover:scale-105" />
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
      <a :href="rec.url || '#'" target="_blank" class="mt-auto w-full py-2.5 px-4 bg-gray-50 hover:bg-gray-100 text-gray-700 font-medium text-sm rounded-lg flex items-center justify-center transition-colors group">
        Visit Page
        <ExternalLink class="ml-2 h-3.5 w-3.5 text-gray-400 group-hover:text-gray-600" />
      </a>
    </div>
  </article>
</template>