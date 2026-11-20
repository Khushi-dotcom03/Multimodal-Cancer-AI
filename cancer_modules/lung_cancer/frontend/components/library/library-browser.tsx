'use client'

import { useMemo, useState } from 'react'
import { BookMarked, Database, ExternalLink, FileText, GraduationCap, Newspaper, Search, SearchX, Wrench } from 'lucide-react'
import { Badge, EmptyState, inputClass } from '@/components/common/primitives'
import { LIBRARY_CATEGORIES, LIBRARY_RESOURCES } from '@/lib/demo-data'
import { cn } from '@/lib/utils'
import type { LibraryResource } from '@/types'

const TYPE_ICON: Record<LibraryResource['type'], typeof FileText> = {
  Article: Newspaper,
  Publication: BookMarked,
  Dataset: Database,
  Tutorial: GraduationCap,
  Tool: Wrench,
}

const TYPE_TONE = { Article: 'blue', Publication: 'violet', Dataset: 'teal', Tutorial: 'pink', Tool: 'amber' } as const

export function LibraryBrowser() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return LIBRARY_RESOURCES.filter(
      (r) => (category === 'all' || r.category === category) && (!q || [r.title, r.description, r.type].some((v) => v.toLowerCase().includes(q))),
    )
  }, [query, category])

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3">
        <div className="relative">
          <label htmlFor="library-search" className="sr-only">
            Search library
          </label>
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            id="library-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search articles, datasets, tutorials…"
            className={cn(inputClass, 'h-11 pl-9')}
          />
        </div>
        <div role="group" aria-label="Filter by category" className="flex flex-wrap gap-2">
          {['all', ...LIBRARY_CATEGORIES].map((c) => (
            <button
              key={c}
              type="button"
              aria-pressed={category === c}
              onClick={() => setCategory(c)}
              className={cn(
                'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                category === c ? 'border-transparent bg-primary text-primary-foreground' : 'border-border bg-card text-muted-foreground hover:text-foreground',
              )}
            >
              {c === 'all' ? 'All' : c}
            </button>
          ))}
        </div>
      </div>

      {filtered.length ? (
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((r) => {
            const Icon = TYPE_ICON[r.type]
            return (
              <li key={r.id}>
                <article className="flex h-full flex-col gap-3 rounded-2xl border border-border bg-card p-5 transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-slate-900/5">
                  <div className="flex items-center justify-between gap-2">
                    <Badge tone={TYPE_TONE[r.type]}>
                      <Icon className="size-3" aria-hidden /> {r.type}
                    </Badge>
                    {r.isPlaceholder && <Badge>Placeholder</Badge>}
                  </div>
                  <h3 className="font-semibold text-pretty">{r.title}</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{r.description}</p>
                  <div className="mt-auto flex items-center justify-between pt-2 text-xs">
                    <span className="text-muted-foreground">{r.category}</span>
                    {r.url ? (
                      <a href={r.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold text-wc-teal hover:underline dark:text-wc-turquoise">
                        Open <ExternalLink className="size-3" aria-hidden />
                      </a>
                    ) : (
                      <span className="text-muted-foreground">Link pending</span>
                    )}
                  </div>
                </article>
              </li>
            )
          })}
        </ul>
      ) : (
        <EmptyState icon={SearchX} title="No resources found" description="Try another search term or category." />
      )}
    </div>
  )
}
