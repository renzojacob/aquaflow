<!-- One order in the dispatcher's queue. Pending orders get a quick Confirm button. -->
<script setup>
import AppButton from '@/components/ui/AppButton.vue'
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
  <div class="row" :class="{ 'row--sel': selected }">
    <button type="button" class="row__main" :aria-current="selected ? 'true' : undefined" @click="$emit('open', order)">
      <span class="row__qty" aria-hidden="true">{{ order.quantity }}</span>
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
  display: flex;
  align-items: center;
  gap: var(--af-s2);
  padding-right: var(--af-s3);
  background: var(--af-surface);
  border: 1px solid var(--af-line);
  border-radius: var(--af-r-md);
  transition: border-color var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease);
}
.row:hover { box-shadow: var(--af-shadow-2); }
.row--sel { border-color: var(--af-primary); box-shadow: 0 0 0 3px var(--af-primary-tint); }
.row__main {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
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
.row__qty {
  width: 44px;
  height: 44px;
  border-radius: var(--af-r-sm);
  background: var(--af-primary-tint);
  color: var(--af-primary);
  display: grid;
  place-items: center;
  font-size: 18px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.row__text { display: grid; gap: 2px; min-width: 0; }
.row__top { display: flex; align-items: baseline; gap: var(--af-s2); min-width: 0; }
.row__top b { font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.row__code { font-size: 12px; font-weight: 700; color: var(--af-ink-2); flex: none; }
.row__meta { font-size: 13px; color: var(--af-ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-variant-numeric: tabular-nums; }
.row__quick { flex: none; }
@media (max-width: 520px) {
  .row__pill { display: none; }
}
</style>
