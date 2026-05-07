import { ref, onUnmounted, type Ref } from 'vue'
import { CONST } from '@/constants'

/**
 * Carousel scroll state management.
 * Tracks scroll position for arrow visibility and page navigation.
 */
export function useCarousel(trackRef: Ref<HTMLElement | null>) {
  const canScrollLeft = ref(false)
  const canScrollRight = ref(false)
  const canPageLeft = ref(false)
  const canPageRight = ref(false)

  function updateScrollArrows() {
    const track = trackRef.value
    if (!track) {
      canScrollLeft.value = false
      canScrollRight.value = false
      canPageLeft.value = false
      canPageRight.value = false
      return
    }
    const scrollLeft = track.scrollLeft
    const scrollRight = track.scrollWidth - track.clientWidth - scrollLeft
    canScrollLeft.value = scrollLeft > CONST.SCROLL_THRESHOLD_PX
    canScrollRight.value = scrollRight > CONST.SCROLL_THRESHOLD_PX

    const boundaries = getPageBoundaries()
    const idx = getCurrentPageIndex(boundaries)
    canPageLeft.value = idx > 0
    canPageRight.value = idx < boundaries.length - 1
  }

  function getPageBoundaries(): number[] {
    const track = trackRef.value
    if (!track) return []
    const boundaries = [0]
    const dividers = track.querySelectorAll('.carousel-slide--divider')
    for (const div of dividers) {
      boundaries.push((div as HTMLElement).offsetLeft)
    }
    return boundaries
  }

  function getCurrentPageIndex(boundaries: number[]): number {
    const track = trackRef.value
    if (!track || boundaries.length === 0) return 0
    const scrollLeft = track.scrollLeft
    let closestIdx = 0
    let closestDist = Math.abs(scrollLeft - boundaries[0])
    for (let i = 1; i < boundaries.length; i++) {
      const dist = Math.abs(scrollLeft - boundaries[i])
      if (dist < closestDist) {
        closestIdx = i
        closestDist = dist
      }
    }
    return closestIdx
  }

  function scrollToStart() {
    const track = trackRef.value
    if (track) track.scrollTo({ left: 0, behavior: 'smooth' })
    scheduleScrollArrowUpdate()
  }

  function scrollCarousel(direction: number) {
    const track = trackRef.value
    if (!track) return
    const slide = track.children[0] as HTMLElement | undefined
    const slideWidth = slide ? slide.offsetWidth + CONST.CAROUSEL_GAP_PX : 300
    track.scrollBy({ left: direction * slideWidth, behavior: 'smooth' })
  }

  function scrollToPrevPage() {
    const track = trackRef.value
    if (!track) return
    const boundaries = getPageBoundaries()
    const idx = getCurrentPageIndex(boundaries)
    if (idx > 0) {
      track.scrollTo({ left: boundaries[idx - 1], behavior: 'smooth' })
      scheduleScrollArrowUpdate()
    }
  }

  function scrollToNextPage() {
    const track = trackRef.value
    if (!track) return
    const boundaries = getPageBoundaries()
    const idx = getCurrentPageIndex(boundaries)
    if (idx < boundaries.length - 1) {
      track.scrollTo({ left: boundaries[idx + 1], behavior: 'smooth' })
      scheduleScrollArrowUpdate()
    }
  }

  function scheduleScrollArrowUpdate() {
    requestAnimationFrame(() => updateScrollArrows())
    setTimeout(() => updateScrollArrows(), CONST.SCROLL_ARROW_DELAY_MS)
    setTimeout(() => updateScrollArrows(), CONST.SCROLL_ARROW_SETTLE_MS)
  }

  function onTrackScroll() {
    updateScrollArrows()
  }

  // Resize handler
  const _onResize = () => updateScrollArrows()
  window.addEventListener('resize', _onResize)
  onUnmounted(() => window.removeEventListener('resize', _onResize))

  return {
    canScrollLeft,
    canScrollRight,
    canPageLeft,
    canPageRight,
    updateScrollArrows,
    scheduleScrollArrowUpdate,
    scrollToStart,
    scrollCarousel,
    scrollToPrevPage,
    scrollToNextPage,
    onTrackScroll,
  }
}
