'use client'

import { useState } from 'react'
import { Activity, Cpu, FileText, ImageUp } from 'lucide-react'
import { Badge, EmptyState, Panel, PanelHeader } from '@/components/common/primitives'
import { useDemoMode } from '@/components/providers'
import { DEMO_REPORTS } from '@/lib/demo-data'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'activity', label: 'Recent activity', icon: Activity },
  { id: 'uploads', label: 'Image uploads', icon: ImageUp },
  { id: 'models', label: 'Model updates', icon: Cpu },
  { id: 'reports', label: 'Reports', icon: FileText },
] as const

type TabId = (typeof TABS)[number]['id']

const EMPTY_COPY: Record<TabId, { title: string; description: string }> = {
  activity: { title: 'No research activity yet', description: 'Activity from analyses, uploads and reports will appear here once the backend is connected.' },
  uploads: { title: 'No images uploaded', description: 'Upload a dermoscopic image in Image Analysis to begin a research session.' },
  models: { title: 'No model updates', description: 'Model registration and evaluation updates will appear after a trained model is integrated.' },
  reports: { title: 'No reports generated', description: 'Research reports are created from completed analyses.' },
}

const STATUS_TONE = { completed: 'emerald', pending: 'amber', failed: 'red' } as const

export function ResearchActivity() {
  const [tab, setTab] = useState<TabId>('activity')
  const { demoMode } = useDemoMode()
  const showDemoRows = demoMode && (tab === 'activity' || tab === 'uploads' || tab === 'reports')

  return (
    <Panel className="h-full">
      <PanelHeader
        title="Research Activity"
        description="Uploads, model integration and report generation."
        icon={Activity}
        action={demoMode ? <Badge tone="violet">Demo data</Badge> : undefined}
      />
      <div className="px-5 pt-4 sm:px-6">
        <div role="tablist" aria-label="Activity type" className="flex gap-1 overflow-x-auto rounded-xl bg-muted p-1">
          {TABS.map((t) => {
            const Icon = t.icon
            return (
              <button
                key={t.id}
                role="tab"
                type="button"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                  tab === t.id ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="size-3.5" aria-hidden />
                {t.label}
              </button>
            )
          })}
        </div>
      </div>
      <div role="tabpanel" className="p-5 sm:p-6">
        {showDemoRows ? (
          <ul className="flex flex-col divide-y divide-border">
            {DEMO_REPORTS.map((r) => (
              <li key={r.analysisId} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-wc-blue/12 text-wc-blue">
                  {tab === 'reports' ? <FileText className="size-4" aria-hidden /> : <ImageUp className="size-4" aria-hidden />}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{tab === 'reports' ? `Report ${r.analysisId}` : r.fileName}</p>
                  <p className="text-xs text-muted-foreground">
                    {r.moduleName} · {r.uploadDate}
                  </p>
                </div>
                <Badge tone={STATUS_TONE[r.analysisStatus]} className="capitalize">
                  {r.analysisStatus}
                </Badge>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon={TABS.find((t) => t.id === tab)!.icon} {...EMPTY_COPY[tab]} />
        )}
      </div>
    </Panel>
  )
}
