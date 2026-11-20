import type { Metadata } from 'next'
import { PageHeader } from '@/components/common/primitives'
import { AssistantWorkspace } from '@/components/platform/assistant-workspace'
import { SkinCancerFeatureNav } from '@/components/analysis/skin-cancer-feature-nav'

export const metadata: Metadata = { title: 'AI Assistant' }

export default function AssistantPage() {
  return <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Skin Cancer Education" title="AI Assistant" description="Educational skin-cancer information from the WeCure Assistant. Not a diagnosis." />
    <SkinCancerFeatureNav />
    <AssistantWorkspace />
  </div>
}
