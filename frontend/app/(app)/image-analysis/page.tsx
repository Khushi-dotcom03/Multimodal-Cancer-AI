import type { Metadata } from 'next'
import { AnalysisWorkspace } from '@/components/analysis/analysis-workspace'
import { SkinCancerFeatureNav } from '@/components/analysis/skin-cancer-feature-nav'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Image Analysis' }

export default function ImageAnalysisPage() {
  return <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Skin Cancer" title="Image Analysis" description="Use the saved ResNet-18 image classifier without clinical metadata. Its Grad-CAM overlay is an attention visualization, not a diagnosis." />
    <SkinCancerFeatureNav />
    <AnalysisWorkspace moduleId="skin-image-analysis" />
    <ResearchDisclaimer />
  </div>
}
