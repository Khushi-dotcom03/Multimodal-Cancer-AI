import type { Metadata } from 'next'
import { ExternalLink, Layers3 } from 'lucide-react'
import { BreastCancerModuleNav } from '@/components/analysis/breast-cancer-module-nav'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader, Panel } from '@/components/common/primitives'

export const metadata: Metadata = {
  title: 'Breast Cancer Combined Analysis',
  description: 'Review breast image and clinical model outputs together while keeping results separate.',
}

const evidenceViewerUrl = 'http://127.0.0.1:8503/?embed=true'

export default function BreastEvidenceReviewPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Breast Cancer · Combined Analysis"
        title="Combined Analysis"
        description="Review image and clinical model outputs together. The results remain separate and are not combined into a score or diagnosis."
      />

      <BreastCancerModuleNav />

      <Panel className="overflow-hidden p-2 sm:p-3">
        <iframe
          src={evidenceViewerUrl}
          title="Breast Cancer Combined Analysis"
          className="h-[calc(100vh-16rem)] min-h-[720px] w-full rounded-lg border-0 bg-[#081522]"
          allow="clipboard-read; clipboard-write"
        />
      </Panel>

      <a
        href={evidenceViewerUrl}
        target="_blank"
        rel="noreferrer"
        className="inline-flex w-fit items-center gap-2 text-sm font-semibold text-primary"
      >
        <Layers3 className="size-4" aria-hidden />
        Open Combined Analysis in a new tab
        <ExternalLink className="size-4" aria-hidden />
      </a>

      <ResearchDisclaimer />
    </div>
  )
}
