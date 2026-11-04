import type { Metadata } from 'next'
import { AnalysisWorkspace } from '@/components/analysis/analysis-workspace'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Skin Cancer Image Analysis' }

export default function AnalysisPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Image Analysis · Skin Cancer"
        title="Skin Lesion Image Analysis"
        description="Upload a dermoscopic image to run it through the connected research model. Results appear only when a trained model is integrated."
      />
      <AnalysisWorkspace />
      <ResearchDisclaimer />
    </div>
  )
}
