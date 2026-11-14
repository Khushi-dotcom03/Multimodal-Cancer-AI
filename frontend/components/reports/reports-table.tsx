'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import useSWR from 'swr'
import { AlertTriangle, Download, Eye, FileText, Loader2, Search, X } from 'lucide-react'
import { Badge, EmptyState, inputClass, Panel } from '@/components/common/primitives'
import { cn } from '@/lib/utils'
import { reportsService } from '@/services/reports-service'
import type { ReportStatus, ResearchReport } from '@/types'

/* eslint-disable @next/next/no-img-element -- report images are data URLs returned by the analysis API */

const STATUS_TONE: Record<ReportStatus, 'emerald' | 'amber' | 'red'> = { completed: 'emerald', pending: 'amber', failed: 'red' }

export function ReportsTable() {
  const { data, error, isLoading } = useSWR('reports', () => reportsService.list())
  const openedQueryId = useRef<string | null>(null)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<'all' | ReportStatus>('all')
  const [selected, setSelected] = useState<ResearchReport | null>(null)
  const detailKey = selected && !selected.isDemo ? `report:${selected.analysisId}` : null
  const { data: selectedDetail, error: detailError, isLoading: detailLoading } = useSWR<ResearchReport>(
    detailKey,
    () => reportsService.get(selected!.analysisId),
  )

  useEffect(() => {
    if (!data || typeof window === 'undefined') return
    const id = new URLSearchParams(window.location.search).get('analysisId')
    if (!id || openedQueryId.current === id) return
    openedQueryId.current = id
    const summary = data.find((report) => report.analysisId === id)
    if (summary) setSelected(summary)
    else reportsService.get(id).then(setSelected).catch(() => undefined)
  }, [data])

  const reports = data ?? []

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
            placeholder="Search by analysis ID, module or fileâ€¦"
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
            <Loader2 className="size-4 animate-spin" aria-hidden /> Loading reportsâ€¦
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
              description={reports.length ? 'Adjust your search or status filter.' : 'Reports appear here after a completed analysis on the Analysis page.'}
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

      {selected && (
        <ReportDialog
          report={selectedDetail ?? selected}
          loading={detailLoading}
          loadError={detailError instanceof Error ? detailError.message : null}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}

function DownloadButton({ report }: { report: ResearchReport }) {
  const url = report.isDemo || report.analysisStatus !== 'completed' ? null : reportsService.downloadUrl(report.analysisId)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const className = 'inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground'
  if (!url)
    return (
      <button type="button" disabled className={cn(className, 'cursor-not-allowed opacity-40')} aria-label={`Download unavailable for ${report.analysisId}`}>
        <Download className="size-4" />
      </button>
    )
  const download = async () => {
    setDownloading(true)
    setError(null)
    try {
      const response = await fetch(url)
      if (!response.ok) throw new Error('Report download failed. Please try again.')
      const blob = await response.blob()
      const isPdf = response.headers.get('content-type')?.includes('application/pdf') ?? false
      const objectUrl = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = objectUrl
      anchor.download = `wecure-report-${report.analysisId}.${isPdf ? 'pdf' : 'json'}`
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Report download failed.')
    } finally {
      setDownloading(false)
    }
  }
  return (
    <span className="relative">
      <button type="button" onClick={download} disabled={downloading} className={className} aria-label={`Download report ${report.analysisId}`} title="Downloads a PDF when detailed report data is available; legacy reports retain their JSON download.">
        {downloading ? <Loader2 className="size-4 animate-spin" /> : <Download className="size-4" />}
      </button>
      {error && <span role="alert" className="absolute right-0 top-full z-10 mt-1 w-48 rounded-lg border border-border bg-card p-2 text-xs text-red-600 shadow-lg">{error}</span>}
    </span>
  )
}

function ReportDialog({ report, loading, loadError, onClose }: { report: ResearchReport; loading: boolean; loadError: string | null; onClose: () => void }) {
  const result = report.result
  const metrics = report.evaluationMetrics
  const probabilities = result?.probabilities
  const probabilityEntries = probabilities ? Object.entries(probabilities) : []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-wc-navy/50 p-4 backdrop-blur-sm" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-dialog-title"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.key === 'Escape' && onClose()}
        className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-border px-5 py-4">
          <div>
            <p className="text-xs font-medium tracking-wide text-wc-teal uppercase">Research report</p>
            <h2 id="report-dialog-title" className="mt-0.5 font-semibold">{report.analysisId}</h2>
          </div>
          <button type="button" autoFocus onClick={onClose} className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted" aria-label="Close report">
            <X className="size-4" />
          </button>
        </div>
        <div className="overflow-y-auto p-5 sm:p-6">
          {loading && <p className="mb-4 text-sm text-muted-foreground">Loading detailed reportâ€¦</p>}
          {loadError && <p role="alert" className="mb-4 rounded-xl border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-700">Detailed report could not be loaded: {loadError}</p>}
          {!result && !loading && !report.isDemo && (
            <p className="mb-5 rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-3 text-sm text-muted-foreground">
              This report was created before detailed image and probability data were stored. The original record is preserved; unavailable fields are not reconstructed.
            </p>
          )}

          <ReportSection title="Patient and image information">
            <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
              <ReportField label="Analysis ID" value={report.analysisId} mono />
              <ReportField label="Module" value={report.moduleName} />
              <ReportField label="Uploaded filename" value={report.fileName || 'Not provided'} />
              <ReportField label="Uploaded at" value={formatTimestamp(report.uploadDate)} />
              <ReportField label="Age" value={report.age == null ? 'Not provided' : String(report.age)} />
              <ReportField label="Sex" value={!report.sex || report.sex === 'unknown' ? 'Not provided' : report.sex} />
              <ReportField label="Lesion location" value={!report.localization || report.localization === 'unknown' ? 'Not provided' : report.localization} />
              <ReportField label="Model status" value={report.modelStatus} />
              <ReportField label="Analysis status" value={report.analysisStatus} />
            </dl>
          </ReportSection>

          <ReportSection title="AI prediction">
            {result ? (
              <>
                <div className="grid gap-3 sm:grid-cols-3">
                  <ReportMetric label="Predicted class" value={result.prediction || 'Not available'} />
                  <ReportMetric label="Class code" value={result.classification || 'Not available'} />
                  <ReportMetric label="Model confidence" value={typeof result.confidence === 'number' ? `${(result.confidence * 100).toFixed(2)}%` : 'Not available'} />
                </div>
                {probabilityEntries.length > 0 ? (
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {probabilityEntries.map(([code, value]) => (
                      <div key={code}>
                        <div className="mb-1 flex justify-between gap-2 text-xs"><span className="font-medium">{result.classNames?.[code] || code} <span className="text-muted-foreground">({code})</span></span><span className="shrink-0 text-muted-foreground">{(value * 100).toFixed(2)}%</span></div>
                        <div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-wc-turquoise" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div>
                      </div>
                    ))}
                  </div>
                ) : <p className="mt-3 text-sm text-muted-foreground">Class probabilities were not stored for this report.</p>}
              </>
            ) : <p className="text-sm text-muted-foreground">Prediction details were not stored for this report.</p>}
          </ReportSection>

          <ReportSection title="Visual explainability">
            <div className="grid gap-4 md:grid-cols-2">
              <ReportImage title="Original uploaded image" src={result?.originalImageUrl} empty="Original image not available in this report." />
              <ReportImage title="Grad-CAM overlay" src={result?.heatmapUrl} empty="Grad-CAM output not available in this report." />
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{result?.heatmapDescription || 'Grad-CAM highlights image regions that influenced the model output. It is not a lesion boundary, proof, or diagnosis.'}</p>
          </ReportSection>

          <ReportSection title="Model and evaluation">
            <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <ReportField label="Image model" value={result?.model?.imageModel || (report.moduleId === 'skin-image-analysis' ? result?.model?.name : undefined) || 'Not recorded'} />
              <ReportField label="Clinical model" value={result?.model?.clinicalModel || (report.moduleId === 'clinical-analysis' ? result?.model?.name : undefined) || 'Not recorded'} />
              <ReportField label="Checkpoint version" value={result?.model?.version || 'Not recorded'} />
              <ReportField label="Fusion architecture" value={result?.model?.architecture || 'Not available'} />
              <ReportField label="Dataset" value={result?.model?.dataset || 'HAM10000'} />
            </dl>
            {metrics ? (
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <ReportMetric label="Accuracy" value={`${(metrics.accuracy * 100).toFixed(2)}%`} />
                <ReportMetric label="Weighted precision" value={`${(metrics.precision * 100).toFixed(2)}%`} />
                <ReportMetric label="Weighted recall" value={`${(metrics.recall * 100).toFixed(2)}%`} />
                <ReportMetric label="Weighted F1" value={`${(metrics.f1 * 100).toFixed(2)}%`} />
                {metrics.macroF1 != null && <ReportMetric label="Macro F1" value={`${(metrics.macroF1 * 100).toFixed(2)}%`} />}
                {metrics.testSamples != null && <ReportMetric label="Evaluation test samples" value={metrics.testSamples.toLocaleString()} />}
              </div>
            ) : <p className="mt-3 text-sm text-muted-foreground">Evaluation metrics are not attached to this older report.</p>}
          </ReportSection>

          <ReportSection title="Educational information">
            {report.educationalOverview?.overview ? <p className="text-sm leading-relaxed">{report.educationalOverview.overview}</p> : <p className="text-sm text-muted-foreground">Category-specific educational information is not available for this report.</p>}
            {report.educationalOverview?.source && <a href={report.educationalOverview.source} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm font-medium text-wc-teal underline">Read the educational reference</a>}
            {report.researchReferences && report.researchReferences.length > 0 && <div className="mt-3"><p className="text-xs font-semibold text-muted-foreground">Research references</p><ul className="mt-1 list-inside list-disc space-y-1">{report.researchReferences.map((ref) => <li key={ref.url}><a href={ref.url} target="_blank" rel="noreferrer" className="text-sm text-wc-teal underline">{ref.title}</a></li>)}</ul></div>}
            <p className="mt-3 rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-3 text-sm leading-relaxed text-foreground">This experimental AI output is not a confirmed diagnosis and must not be used to choose treatment. Discuss skin concerns with a qualified dermatologist, especially if a spot is new, changing, bleeding, itchy, crusted, or not healing.</p>
          </ReportSection>

          <p className="mt-4 text-xs text-muted-foreground">{result?.reportStorage === 'sqlite' ? (result.originalImageUrl || result.heatmapUrl ? 'This detailed report and its image data are stored in the API SQLite database.' : 'This clinical-only report is stored in the API SQLite database; it contains no uploaded image.') : 'This report is held in API memory only and may be lost when the API process exits. Older reports created before persistence may remain only in their original API process.'}</p>
          {report.isDemo && <p className="mt-3 border-t border-border pt-3 text-xs text-muted-foreground">Illustrative demo report â€” no real analysis data.</p>}
        </div>
      </div>
    </div>
  )
}

function ReportSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="mb-5 rounded-xl border border-border p-4 sm:p-5"><h3 className="mb-3 text-sm font-semibold tracking-wide">{title}</h3>{children}</section>
}

function ReportField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return <div className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className={cn('mt-0.5 break-words text-sm font-medium', mono && 'font-mono')}>{value}</dd></div>
}

function ReportMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg bg-elevated p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-sm font-semibold">{value}</p></div>
}

function ReportImage({ title, src, empty }: { title: string; src?: string; empty: string }) {
  return <figure><div className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-lg bg-muted">{src ? <img src={src} alt={title} className="size-full object-contain" /> : <p className="px-4 text-center text-sm text-muted-foreground">{empty}</p>}</div><figcaption className="mt-1.5 text-xs text-muted-foreground">{title}</figcaption></figure>
}

function formatTimestamp(value: string) {
  if (!value) return 'Not available'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : `${date.toLocaleString()} (${date.toISOString()})`
}

