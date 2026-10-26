<!--
  TextField — labeled input with hint and error text.
  Usage: <TextField v-model="email" label="Email" type="email" autocomplete="email" :error="errors.email" />
  multiline = textarea. type="password" gets a Show / Hide button.
-->
<script setup>
import { computed, ref, useId } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, required: true },
  type: { type: String, default: 'text' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
  inputmode: { type: String, default: undefined },
  required: { type: Boolean, default: false },
  multiline: { type: Boolean, default: false },
  maxlength: { type: Number, default: undefined },
})
defineEmits(['update:modelValue'])

const id = useId()
const helpId = `${id}-help`
const showPassword = ref(false)
const inputType = computed(() => (props.type === 'password' && showPassword.value ? 'text' : props.type))
</script>

<template>
  <div class="af-field" :class="{ 'af-field--error': error }">
    <label :for="id" class="af-field__label">
      {{ label }}<span v-if="!required" class="af-field__opt"> (optional)</span>
    </label>

    <div class="af-field__box">
      <textarea
        v-if="multiline"
        :id="id"
        class="af-field__input af-field__input--area"
        :value="modelValue"
        :placeholder="placeholder"
        :maxlength="maxlength"
        rows="3"
        :aria-invalid="!!error || undefined"
        :aria-describedby="error || hint ? helpId : undefined"
        @input="$emit('update:modelValue', $event.target.value)"
      ></textarea>
      <input
        v-else
        :id="id"
        class="af-field__input"
        :type="inputType"
        :value="modelValue"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :inputmode="inputmode"
        :required="required"
        :maxlength="maxlength"
        :aria-invalid="!!error || undefined"
        :aria-describedby="error || hint ? helpId : undefined"
        @input="$emit('update:modelValue', $event.target.value)"
      />
      <button
        v-if="type === 'password'"
        type="button"
        class="af-field__toggle"
        :aria-pressed="showPassword"
        @click="showPassword = !showPassword"
      >
        {{ showPassword ? 'Hide' : 'Show' }}
      </button>
    </div>

    <p v-if="error" :id="helpId" class="af-field__help af-field__help--error">{{ error }}</p>
    <p v-else-if="hint" :id="helpId" class="af-field__help">{{ hint }}</p>
  </div>
</template>

<style scoped>
.af-field { display: grid; gap: 6px; min-width: 0; }
.af-field__label { font-size: 14px; font-weight: 700; color: var(--af-ink); }
.af-field__opt { font-weight: 500; color: var(--af-ink-2); }
.af-field__box { position: relative; display: flex; }
.af-field__input {
  width: 100%;
  min-height: 48px;
  padding: 12px 14px;
  font: 500 16px/1.4 var(--af-font); /* 16px stops iPhone/Android from zooming in */
  color: var(--af-ink);
  background: var(--af-surface);
  border: 1.5px solid var(--af-line);
  border-radius: var(--af-r-sm);
  transition: border-color var(--af-dur) var(--af-ease), box-shadow var(--af-dur) var(--af-ease);
}
.af-field__input--area { resize: vertical; min-height: 88px; }
.af-field__input::placeholder { color: color-mix(in srgb, var(--af-ink-2) 70%, transparent); }
.af-field__input:focus { outline: none; border-color: var(--af-primary); box-shadow: 0 0 0 3px var(--af-primary-tint); }
.af-field--error .af-field__input { border-color: var(--af-danger); }
.af-field__toggle {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  min-height: 36px;
  padding: 0 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--af-primary);
  font: 700 13px var(--af-font);
  cursor: pointer;
}
.af-field__toggle:hover { background: var(--af-primary-tint); }
.af-field__help { margin: 0; font-size: 13px; color: var(--af-ink-2); }
.af-field__help--error { color: var(--af-danger); font-weight: 600; }
</style>
