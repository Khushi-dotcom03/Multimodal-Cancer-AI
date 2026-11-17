'use client'

import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import { BookOpen, FileText, Layers, Search, type LucideIcon } from 'lucide-react'
import { useDismissable } from '@/hooks/use-dismissable'
import { LIBRARY_RESOURCES } from '@/lib/demo-data'
import { RESEARCH_MODULES } from '@/lib/modules'
import { MAIN_NAV, SECONDARY_NAV } from '@/lib/navigation'
import { cn } from '@/lib/utils'

interface SearchEntry {
  id: string
  label: string
  hint: string
  href: string
  group: 'Pages' | 'Modules' | 'Library'
  icon: LucideIcon
}

const INDEX: SearchEntry[] = [
  ...[...MAIN_NAV, ...SECONDARY_NAV].map((n) => ({ id: `p-${n.href}`, label: n.label, hint: n.description, href: n.href, group: 'Pages' as const, icon: n.icon })),
  ...RESEARCH_MODULES.map((m) => ({
    id: `m-${m.id}`,
    label: m.name,
    hint: `${m.statusLabel} · ${m.category}`,
    href: m.status === 'available' ? m.href : `/modules?q=${encodeURIComponent(m.name)}`,
    group: 'Modules' as const,
    icon: Layers,
  })),
  { id: 'p-reports-search', label: 'Search reports', hint: 'Find reports by analysis ID', href: '/reports', group: 'Pages', icon: FileText },
  ...LIBRARY_RESOURCES.map((r) => ({ id: `l-${r.id}`, label: r.title, hint: r.category, href: `/library?q=${encodeURIComponent(r.category)}`, group: 'Library' as const, icon: BookOpen })),
]

export function GlobalSearch() {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listId = useId()
  const close = useCallback(() => setOpen(false), [])
  const containerRef = useDismissable<HTMLDivElement>(open, close)

  const results = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return INDEX.filter((e) => e.group !== 'Library').slice(0, 8)
    return INDEX.filter((e) => e.label.toLowerCase().includes(q) || e.hint.toLowerCase().includes(q)).slice(0, 10)
  }, [query])

  useEffect(() => setActiveIndex(0), [query])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        setOpen(true)
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  const go = (entry: SearchEntry) => {
    router.push(entry.href)
    setOpen(false)
    setQuery('')
    inputRef.current?.blur()
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing || e.keyCode === 229) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActiveIndex((i) => Math.min(i + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && results[activeIndex]) {
      e.preventDefault()
      go(results[activeIndex])
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-md flex-1">
      <label htmlFor="global-search" className="sr-only">
        Search modules, pages and reports
      </label>
      <Search className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
      <input
        ref={inputRef}
        id="global-search"
        type="search"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder="Search modules and reports…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className="h-10 w-full rounded-xl border border-border bg-card pr-14 pl-10 text-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30"
      />
      <kbd className="pointer-events-none absolute top-1/2 right-3 hidden -translate-y-1/2 rounded-md border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground md:block">
        ⌘K
      </kbd>

      {open && (
        <div className="absolute top-12 right-0 left-0 z-50 overflow-hidden rounded-2xl border border-border bg-popover p-2 text-popover-foreground shadow-xl shadow-slate-900/10 animate-in fade-in-0 zoom-in-95 sm:right-auto sm:w-[min(32rem,calc(100vw-2rem))]">
          <ul id={listId} role="listbox" aria-label="Search results" className="max-h-80 overflow-y-auto">
            {results.length === 0 && <li className="px-3 py-6 text-center text-sm text-muted-foreground">No matching modules, pages or resources.</li>}
            {results.map((entry, index) => {
              const Icon = entry.icon
              return (
                <li key={entry.id} role="option" aria-selected={index === activeIndex}>
                  <button
                    type="button"
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => go(entry)}
                    className={cn(
                      'flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition-colors',
                      index === activeIndex ? 'bg-muted' : 'hover:bg-muted',
                    )}
                  >
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                      <Icon className="size-4" aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">{entry.label}</span>
                      <span className="block truncate text-xs text-muted-foreground">{entry.hint}</span>
                    </span>
                    <span className="text-[10px] font-medium tracking-wide text-muted-foreground uppercase">{entry.group}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}
