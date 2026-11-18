import type { Metadata } from 'next'
import { SkinCancerFeatureNav } from '@/components/analysis/skin-cancer-feature-nav'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'
import { AnalysisWorkspace } from '@/components/analysis/analysis-workspace'

export const metadata: Metadata = { title: 'Combined Analysis' }

export default function AnalysisPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Skin Cancer"
        title="Combined Analysis"
        description="Upload a lesion image and enter clinical information for that same lesion to run the compatible combined research model."
      />
      <SkinCancerFeatureNav />
      <AnalysisWorkspace moduleId="skin-cancer" />
      <ResearchDisclaimer />
    </div>
  )
}
