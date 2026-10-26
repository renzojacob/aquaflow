<!-- System / Light / Dark switch. Used in the sidebar, Profile and More screens. -->
<script setup>
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import { useTheme } from '@/composables/useTheme'

defineProps({ block: { type: Boolean, default: false } })

const { preference, setTheme } = useTheme()
const options = [
  { value: 'system', label: 'System' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
]
</script>

<template>
  <SegmentedControl :model-value="preference" :options="options" label="Theme" :block="block" @update:model-value="setTheme" />
</template>
