<!--
  PageHeader — the title block at the top of every screen.
  Usage:
    <PageHeader crumb="Dispatcher · Orders" title="Order queue" subtitle="14 pending">
      <template #actions><AppButton>Plan Deliveries</AppButton></template>
    </PageHeader>
-->
<script setup>
defineProps({
  crumb: { type: String, default: '' },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<template>
  <header class="af-ph">
    <div class="af-ph__text">
      <div v-if="crumb" class="af-ph__crumb">{{ crumb }}</div>
      <h1 class="af-ph__title">{{ title }}</h1>
      <p v-if="subtitle" class="af-ph__sub">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="af-ph__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.af-ph { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--af-s4); flex-wrap: wrap; }
.af-ph__text { min-width: 0; }
.af-ph__crumb { font-size: 13px; color: var(--af-ink-2); font-weight: 600; }
.af-ph__title { margin: 4px 0 0; font-size: 28px; line-height: 36px; font-weight: 800; letter-spacing: -0.02em; text-wrap: balance; }
.af-ph__sub { margin: 4px 0 0; color: var(--af-ink-2); font-size: 14px; font-variant-numeric: tabular-nums; }
.af-ph__actions { display: flex; gap: var(--af-s2); flex-wrap: wrap; }
</style>