<template>
  <img v-if="!failed" class="company-logo" :style="sizeStyle" :src="src" :alt="name" @error="failed = true" />
  <span v-else class="logo-tile-fallback" :style="[sizeStyle, tileStyle]">{{ name.slice(0, 1) }}</span>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 42 },
})

const failed = ref(false)
const src = computed(() => '/api/logo?company=' + encodeURIComponent(props.name))
const sizeStyle = computed(() => ({
  width: props.size + 'px', height: props.size + 'px',
  fontSize: Math.round(props.size * 0.44) + 'px',
  borderRadius: Math.round(props.size * 0.24) + 'px',
}))
const COLORS = [['#2f66f6', '#6f9bff'], ['#18a058', '#4fd394'], ['#e07c1f', '#f5b04f'],
                ['#7a5af5', '#a68dff'], ['#d93025', '#f0704f'], ['#0e9fae', '#4fd0e3']]
const tileStyle = computed(() => {
  let h = 0
  for (const ch of String(props.name)) h = (h * 31 + (ch.codePointAt(0) || 0)) % 997
  const [a, b] = COLORS[h % COLORS.length]
  return { background: `linear-gradient(135deg, ${a}, ${b})` }
})
</script>

<style scoped>
.company-logo { object-fit: contain; background: #fff; border: 1px solid #e8ecf4; flex-shrink: 0; }
.logo-tile-fallback { color: #fff; font-weight: 600; display: inline-grid; place-items: center; flex-shrink: 0; box-shadow: inset 0 -2px 4px rgba(0, 0, 0, .12); }
</style>
