// true/false that follows a CSS media query, e.g. useMediaQuery('(min-width: 1100px)')
import { onBeforeUnmount, ref } from 'vue'

export function useMediaQuery(query) {
  const mql = window.matchMedia(query)
  const matches = ref(mql.matches)
  const onChange = (e) => (matches.value = e.matches)
  mql.addEventListener('change', onChange)
  onBeforeUnmount(() => mql.removeEventListener('change', onChange))
  return matches
}
