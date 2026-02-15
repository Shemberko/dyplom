<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next';

defineProps<{
  current: number;
  total: number;
}>();

defineEmits(['update:current']);
</script>

<template>
  <div class="mt-16 flex justify-center items-center space-x-4">
    <button 
      :disabled="current === 1" 
      @click="$emit('update:current', current - 1)"
      class="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
    >
      <ChevronLeft class="h-5 w-5" />
    </button>
    
    <span class="text-sm font-medium text-gray-600 bg-white px-4 py-2 rounded-lg border border-gray-200 shadow-sm">
      Page {{ current }} of {{ total }}
    </span>
    
    <button 
      :disabled="current === total" 
      @click="$emit('update:current', current + 1)"
      class="p-2 rounded-lg border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
    >
      <ChevronRight class="h-5 w-5" />
    </button>
  </div>
</template>