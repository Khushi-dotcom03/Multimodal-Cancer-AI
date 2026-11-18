import type { Metadata } from 'next'
import { PageHeader } from '@/components/common/primitives'
import { PADClinicalAnalysisWorkspace } from '@/components/platform/pad-clinical-analysis-workspace'
import { SkinCancerFeatureNav } from '@/components/analysis/skin-cancer-feature-nav'

export const metadata: Metadata = { title: 'Clinical Analysis' }

export default function ClinicalAnalysisPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Research Module 2"
        title="Clinical Analysis"
        description="Review supported clinical features without uploading an image."
      />
      <SkinCancerFeatureNav />
      <PADClinicalAnalysisWorkspace />
    </div>
  )
}
