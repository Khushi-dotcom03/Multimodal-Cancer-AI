import type { Metadata } from 'next'
import { BrainImageWorkspace } from '@/components/analysis/brain-image-workspace'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Brain MRI Image Analysis' }

export default function BrainImagePage() {
  return <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Image Analysis · Brain Cancer" title="Brain MRI Image Analysis" description="Upload a brain MRI image to view the four-class research model output and its Grad-CAM visualization." />
    <BrainImageWorkspace />
  </div>
}
