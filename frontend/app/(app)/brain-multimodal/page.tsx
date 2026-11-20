import type { Metadata } from 'next'
import { BrainMultimodalWorkspace } from '@/components/analysis/brain-multimodal-workspace'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Brain Multimodal Analysis' }

export default function BrainMultimodalPage() {
  return <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Brain Cancer" title="Brain Multimodal Analysis" />
    <BrainMultimodalWorkspace />
  </div>
}
