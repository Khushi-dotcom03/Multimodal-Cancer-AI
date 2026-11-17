import type { Metadata } from 'next'
import { BrainMultimodalWorkspace } from '@/components/analysis/brain-multimodal-workspace'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Brain Multimodal Analysis' }

export default function BrainMultimodalPage() {
  return <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Multimodal Research · Brain Cancer" title="Brain MRI + Clinical Analysis" description="Submit an MRI with Age, Sex, and Tumour location to run the existing brain image and clinical research models in one workflow." />
    <BrainMultimodalWorkspace />
  </div>
}
