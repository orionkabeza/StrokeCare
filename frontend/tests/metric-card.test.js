// Owner: Emmanuel Happy Rangira (Frontend developer)
// The week cards: an empty day is blank (never a zero bar), every day is read out, and no colour depends on a value.
import './setup.js'

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { describe, it } from 'node:test'

import { dotMatrix, lineArea, pillBars, rangeBars, rings, stackedBars, weekCards } from '../site/js/components/metric-card.js'
import { useMessages } from '../site/js/i18n.js'
import { SITE } from './helpers.js'

useMessages('en', JSON.parse(readFileSync(`${SITE}/locales/en.json`, 'utf8')))

const dates = ['2026-11-09', '2026-11-10', '2026-11-11', '2026-11-12', '2026-11-13', '2026-11-14', '2026-11-15']
const fills = (svg) => [...String(svg).matchAll(/(?:fill|stroke)="(var\([^"]+\)|#[0-9a-fA-F]+)"/g)].map((m) => m[1])
const label = (svg) => /aria-label="([^"]*)"/.exec(String(svg))[1]
const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const charts = {
  pillBars: (empty) => pillBars(dates, empty ? Array(7).fill(null) : [20, null, 35, 0, 10, null, 5], 'Movement'),
  rangeBars: (empty) => rangeBars(dates, empty ? Array(7).fill(null) : [{ lo: 70, hi: 130 }, null, null, { lo: 40, hi: 250 }, null, null, null], 'BP'),
  dotMatrix: (empty) => dotMatrix(dates, dates.map((_, i) => ({ slots: empty ? [0, 0, 0].map(() => ({ due: 0, taken: 0 })) : [{ due: 1, taken: i % 2 }, { due: 0, taken: 0 }, { due: 1, taken: 1 }] })), 'Doses'),
  rings: (empty) => rings(dates, empty ? Array(7).fill(false) : [true, false, true, true, false, false, true], 'Check-ins'),
  stackedBars: (empty) => stackedBars(dates, dates.map((_, i) => (empty ? { done: 0, in_plan: 0 } : { done: i % 3, in_plan: 3 })), 'Tasks'),
}

describe('week cards', () => {
  it('a week with nothing recorded draws only tracks: no value marks at all', () => {
    for (const [name, draw] of Object.entries(charts)) {
      const svg = String(draw(true))
      assert.ok(!/class="grow"|class="pop"/.test(svg), `${name} drew a value mark for an empty week`)
    }
    assert.ok(!String(pillBars(dates, [0, 0, 0, 0, 0, 0, 0], 'M')).includes('class="grow"'), 'zero minutes draws no bar')
  })

  it('reads every day of the week out, saying when nothing was recorded', () => {
    for (const [name, draw] of Object.entries(charts)) {
      const text = label(draw(false))
      for (const d of days) assert.ok(text.includes(d), `${name} label is missing ${d}`)
    }
    assert.match(label(charts.pillBars(false)), /Tuesday none recorded/)
  })

  it('uses the same colours whatever the values are', () => {
    const low = fills(rangeBars(dates, [{ lo: 50, hi: 90 }, ...Array(6).fill(null)], 'BP'))
    const high = fills(rangeBars(dates, [{ lo: 120, hi: 220 }, ...Array(6).fill(null)], 'BP'))
    assert.deepEqual(low, high)
    assert.ok(fills(charts.pillBars(false)).every((c) => c.startsWith('var(--m-move')))
    assert.ok(!fills(lineArea(dates, [{ at: 0, date: dates[0], pulse: 150, x: 0.3 }, { at: 3600e3, date: dates[0], pulse: 50, x: 0.4 }], 'P')).some((c) => /danger|#B91C1C/i.test(c)))
  })

  it('leaves out a metric that was not shared and hides pulse when no reading has one', () => {
    const week = { dates, checkins: dates.map((date) => ({ date, sent: true })), readings: [{ date: dates[6], taken_at: `${dates[6]}T08:10:00Z`, systolic: 128, diastolic: 80, pulse: null }] }
    const out = String(weekCards(week, (p) => `/p/me/${p}`))
    assert.ok(out.includes('Blood pressure') && out.includes('Check-ins'))
    assert.ok(!out.includes('Pulse') && !out.includes('Movement') && !out.includes('Medicine doses'))
  })
})
