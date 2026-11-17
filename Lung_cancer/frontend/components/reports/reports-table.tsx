'use client'

import { useMemo, useState } from 'react'
import useSWR from 'swr'
import { AlertTriangle, Download, Eye, FileText, Loader2, Search, X } from 'lucide-react'
import { DemoBanner } from '@/components/common/brand'
import { Badge, EmptyState, inputClass, Panel } from '@/components/common/primitives'
import { useDemoMode } from '@/components/providers'
import { DEMO_REPORTS } from '@/lib/demo-data'
import { cn } from '@/lib/utils'
import { reportsService } from '@/services/reports-service'
import type { ReportStatus, ResearchReport } from '@/types'

const STATUS_TONE: Record<ReportStatus, 'emerald' | 'amber' | 'red'> = { completed: 'emerald', pending: 'amber', failed: 'red' }

export function ReportsTable() {
  const { demoMode } = useDemoMode()
  const { data, error, isLoading } = useSWR(demoMode ? null : 'reports', () => reportsService.list())
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<'all' | ReportStatus>('all')
  const [selected, setSelected] = useState<ResearchReport | null>(null)

  const reports = demoMode ? DEMO_REPORTS : (data ?? [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return reports.filter(
      (r) =>
        (status === 'all' || r.analysisStatus === status) &&
        (!q || [r.analysisId, r.moduleName, r.fileName].some((v) => v.toLowerCase().includes(q))),
    )
  }, [reports, query, status])

  return (
    <div className="flex flex-col gap-5">
      {demoMode && <DemoBanner message="Reports below are illustrative samples and cannot be downloaded." />}

      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-3 sm:flex-row">
        <div className="relative flex-1">
          <label htmlFor="report-search" className="sr-only">
            Search reports
          </label>
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input
            id="report-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by analysis ID, module or file…"
            className={cn(inputClass, 'pl-9')}
          />
        </div>
        <label htmlFor="report-status" className="sr-only">
          Filter by status
        </label>
        <select id="report-status" value={status} onChange={(e) => setStatus(e.target.value as typeof status)} className={cn(inputClass, 'sm:w-44')}>
          <option value="all">All statuses</option>
          <option value="completed">Completed</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <Panel className="overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 p-12 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" aria-hidden /> Loading reports…
          </div>
        ) : error ? (
          <div className="p-5">
            <EmptyState icon={AlertTriangle} title="Could not load reports" description={error instanceof Error ? error.message : 'Please try again later.'} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-5">
            <EmptyState
              icon={FileText}
              title={reports.length ? 'No reports match your filters' : 'No reports yet'}
              description={reports.length ? 'Adjust your search or status filter.' : 'Reports appear here after completed analyses. Turn on Demo Mode to preview the layout.'}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-elevated text-xs text-muted-foreground">
                <tr>
                  {['Analysis ID', 'Module', 'Upload date', 'Model status', 'Analysis status', ''].map((h) => (
                    <th key={h} scope="col" className="px-5 py-3 font-medium">
                      {h || <span className="sr-only">Actions</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map((r) => (
                  <tr key={r.analysisId} className="transition-colors hover:bg-muted/50">
                    <td className="px-5 py-3.5 font-mono font-medium">{r.analysisId}</td>
                    <td className="px-5 py-3.5">{r.moduleName}</td>
                    <td className="px-5 py-3.5 text-muted-foreground">{r.uploadDate}</td>
                    <td className="px-5 py-3.5">
                      <Badge tone={r.modelStatus === 'connected' ? 'emerald' : 'amber'} className="capitalize">
                        {r.modelStatus}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge tone={STATUS_TONE[r.analysisStatus]} className="capitalize">
                        {r.analysisStatus}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => setSelected(r)}
                          className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
                          aria-label={`View report ${r.analysisId}`}
                        >
                          <Eye className="size-4" />
                        </button>
                        <DownloadButton report={r} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {selected && <ReportDialog report={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function DownloadButton({ report }: { report: ResearchReport }) {
  const url = report.isDemo || report.analysisStatus !== 'completed' ? null : reportsService.downloadUrl(report.analysisId)
  const className = 'inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground'
  if (!url)
    return (
      <button type="button" disabled className={cn(className, 'cursor-not-allowed opacity-40')} aria-label={`Download unavailable for ${report.analysisId}`}>
        <Download className="size-4" />
      </button>
    )
  return (
    <a href={url} className={className} aria-label={`Download report ${report.analysisId}`}>
      <Download className="size-4" />
    </a>
  )
}

function ReportDialog({ report, onClose }: { report: ResearchReport; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-wc-navy/50 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-dialog-title"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.key === 'Escape' && onClose()}
        className="w-full max-w-md rounded-2xl border border-border bg-card shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 id="report-dialog-title" className="font-semibold">
            Report {report.analysisId}
          </h2>
          <button type="button" autoFocus onClick={onClose} className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted" aria-label="Close">
            <X className="size-4" />
          </button>
        </div>
        <dl className="flex flex-col divide-y divide-border px-5">
          {(
            [
              ['Module', report.moduleName],
              ['File', report.fileName],
              ['Upload date', report.uploadDate],
              ['Model status', report.modelStatus],
              ['Analysis status', report.analysisStatus],
            ] as const
          ).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 py-3 text-sm">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="font-medium capitalize">{v}</dd>
            </div>
          ))}
        </dl>
        {report.isDemo && <p className="border-t border-border px-5 py-3 text-xs text-muted-foreground">Illustrative demo report — no real analysis data.</p>}
      </div>
    </div>
  )
}
