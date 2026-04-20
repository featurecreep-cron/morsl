import { ref } from 'vue'

interface UseSearchOptions {
  endpoint: string
  debounceMs: number
  excludeIds: () => Set<number>
}

/**
 * Debounced search composable for setup wizard.
 * Searches keywords/foods/books via the API with deduplication.
 */
export function useSearch(options: UseSearchOptions) {
  const query = ref('')
  const results = ref<Array<{ id: number; name: string }>>([])
  let timerId: ReturnType<typeof setTimeout> | null = null

  function search(q: string) {
    query.value = q
    if (timerId) clearTimeout(timerId)
    if (q.length < 2) {
      results.value = []
      return
    }
    timerId = setTimeout(async () => {
      try {
        const res = await fetch(`${options.endpoint}?search=${encodeURIComponent(q)}&limit=20`)
        if (res.ok) {
          const data = await res.json()
          const excluded = options.excludeIds()
          results.value = (data.results || data).filter(
            (item: { id: number }) => !excluded.has(item.id),
          )
        }
      } catch {
        // ignore
      }
    }, options.debounceMs)
  }

  function clear() {
    query.value = ''
    results.value = []
    if (timerId) clearTimeout(timerId)
  }

  function destroy() {
    if (timerId) clearTimeout(timerId)
  }

  return { query, results, search, clear, destroy }
}
