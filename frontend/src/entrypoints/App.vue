<script setup lang="ts">
import { useUserStore } from '@/stores/user';
import TheHeader from '@/views/components/TheHeder.vue';

const userStore = useUserStore();
userStore.initializeAuth(); 
</script>

<template>
  <div class="min-h-screen">
    <TheHeader />
    <main class="pt-16">
      <router-view />
    </main>
  </div>
</template>