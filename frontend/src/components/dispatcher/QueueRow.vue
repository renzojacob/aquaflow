<!-- One order in the dispatcher's queue. Pending orders get a quick Confirm button. -->
<script setup>
import AppButton from '@/components/ui/AppButton.vue'
import LiquidFill from '@/components/ui/LiquidFill.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { PERIODS, timeOf } from '@/utils/format'

defineProps({
  order: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
})
defineEmits(['open', 'quick-confirm'])
</script>

<template>
  <div class="row af-spot" :class="{ 'row--sel': selected }">
    <button type="button" class="row__main" :aria-current="selected ? 'true' : undefined" @click="$emit('open', order)">
      <LiquidFill class="row__qty" shape="orb" :size="48" :level="Math.min(order.quantity / 10, 1)" :text="order.quantity" />
      <span class="row__text">
        <span class="row__top">
          <b>{{ order.customer.name }}</b>
          <span class="row__code">{{ order.code }}</span>
        </span>
        <span class="row__meta">
          {{ order.quantity }} × 5 gal · {{ order.address.barangay }} · {{ PERIODS[order.period].label }}
        </span>
        <span class="row__meta">Placed {{ timeOf(order.created_at) }}<template v-if="order.notes"> · has note</template></span>
      </span>
      <StatusPill :status="order.status" class="row__pill" />
    </button>
    <AppButton
      v-if="order.status === 'pending'"
      size="sm"
      class="row__quick"
      :loading="busy"
      :aria-label="`Confirm ${order.code} for ${order.customer.name}`"
      @click="$emit('quick-confirm', order)"
    >
      Confirm
    </AppButton>
  </div>
</template>

<style scoped>
.row {
  position: relative;
  container-type: inline-size;
  backdrop-filter: var(--af-glass-blur);
  -webkit-backdrop-filter: var(--af-glass-blur);
  box-shadow: inset 0 1px 0 var(--af-glass-edge);
  display: flex;
  align-items: center;
  gap: var(--af-s2);
  padding-right: var(--af-s3);
  background: var(--af-surface);
  border: 1px solid var(--af-line);
  border-radius: var(--af-r-md);
  transition: border-color var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease), background var(--af-dur) var(--af-ease);
}
.row:hover { box-shadow: var(--af-shadow-2); border-color: color-mix(in srgb, var(--af-primary) 35%, var(--af-line)); }
.row--sel {
  border-color: var(--af-primary);
  background: linear-gradient(90deg, var(--af-primary-tint) 0%, var(--af-surface) 70%);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--af-primary) 12%, transparent), var(--af-shadow-2);
}
.row__main {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto;
  gap: var(--af-s3);
  align-items: center;
  padding: var(--af-s3) 0 var(--af-s3) var(--af-s3);
  border: 0;
  background: transparent;
  color: var(--af-ink);
  font-family: var(--af-font);
  text-align: left;
  cursor: pointer;
  border-radius: var(--af-r-md);
}
.row__qty { filter: drop-shadow(0 0 10px color-mix(in srgb, var(--af-water) 30%, transparent)); }
.row__text { display: grid; gap: 3px; min-width: 0; }
.row__top { display: flex; align-items: baseline; gap: var(--af-s2); min-width: 0; }
.row__top b { font-size: 15px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row__code { font-family: var(--af-mono); font-size: 11px; font-weight: 600; letter-spacing: 0.04em; color: var(--af-ink-2); flex: none; }
.row__meta { font-size: 13px; color: var(--af-ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-variant-numeric: tabular-nums; }
.row__quick { flex: none; }
/* In a narrow list (phone, or the desktop split view) the tab already says the status */
@container (max-width: 480px) {
  .row__pill { display: none; }
}
</style>
