'use client'

import { useMemo, useState } from 'react'
import { Search, SearchX } from 'lucide-react'
import { EmptyState, inputClass } from '@/components/common/primitives'
import { MODULE_CATEGORIES, RESEARCH_MODULES } from '@/lib/modules'
import { cn } from '@/lib/utils'
import type { ModuleStatus } from '@/types'
import { ModuleGrid } from './module-grid'

type StatusFilter = 'all' | ModuleStatus

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'available', label: 'Available' },
  { value: 'coming-soon', label: 'Coming Soon' },
]

export function ModuleExplorer({ initialQuery }: { initialQuery: string }) {
  const [query, setQuery] = useState(initialQuery)
  const [status, setStatus] = useState<StatusFilter>('all')
  const [category, setCategory] = useState('all')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return RESEARCH_MODULES.filter(
      (m) =>
        (status === 'all' || m.status === status) &&
        (category === 'all' || m.category === category) &&
        (!q || [m.name, m.description, m.category, m.imaging].some((v) => v.toLowerCase().includes(q))),
    )
  }, [query, status, category])

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-3 lg:flex-row lg:items-center">
        <div className="relative flex-1">
          <label htmlFor="module-search" className="sr-only">
            Search modules
          </label>
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            id="module-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, imaging type or category…"
            className={cn(inputClass, 'pl-9')}
          />
        </div>
        <div role="group" aria-label="Filter by status" className="flex gap-1 rounded-xl bg-muted p-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              aria-pressed={status === f.value}
              onClick={() => setStatus(f.value)}
              className={cn(
                'flex-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors lg:flex-none',
                status === f.value ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <label htmlFor="module-category" className="sr-only">
          Filter by category
        </label>
        <select id="module-category" value={category} onChange={(e) => setCategory(e.target.value)} className={cn(inputClass, 'lg:w-52')}>
          <option value="all">All categories</option>
          {MODULE_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <p className="text-sm text-muted-foreground" aria-live="polite">
        Showing {filtered.length} of {RESEARCH_MODULES.length} modules
      </p>

      {filtered.length ? (
        <ModuleGrid modules={filtered} />
      ) : (
        <EmptyState
          icon={SearchX}
          title="No modules match your filters"
          description="Try a different search term or reset the filters."
          action={
            <button
              type="button"
              onClick={() => {
                setQuery('')
                setStatus('all')
                setCategory('all')
              }}
              className="h-9 rounded-xl border border-border px-4 text-sm font-medium hover:bg-muted"
            >
              Reset filters
            </button>
          }
        />
      )}
    </div>
  )
}
