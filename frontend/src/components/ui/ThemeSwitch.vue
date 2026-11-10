<!-- Light / Dark / Auto switch (mode only). For brand + mode use ThemePicker. -->
<script setup>
import SegmentedControl from '@/components/form/SegmentedControl.vue'
import { useTheme } from '@/composables/useTheme'

defineProps({ block: { type: Boolean, default: false } })

const { mode, setMode, MODES } = useTheme()
</script>

<template>
  <SegmentedControl :model-value="mode" :options="MODES" label="Light or dark" :block="block" @update:model-value="setMode" />
</template>
