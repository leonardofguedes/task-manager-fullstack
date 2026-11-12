import { describe, expect, it } from 'vitest'

import { clampPage, pageCount } from '../lib/pagination'

describe('pagination helpers', () => {
  it('counts at least one page', () => {
    expect(pageCount(0, 10)).toBe(1)
    expect(pageCount(10, 10)).toBe(1)
    expect(pageCount(11, 10)).toBe(2)
  })

  it('moves back to the last page when the current one became empty', () => {
    // 11 tasks, user on page 2, deletes the only task there -> 10 left -> page 1
    expect(clampPage(2, 10, 10)).toBe(1)
  })

  it('keeps a page that still has items', () => {
    expect(clampPage(3, 25, 10)).toBe(3)
  })

  it('falls back to page 1 when nothing matches', () => {
    expect(clampPage(5, 0, 10)).toBe(1)
  })
})
