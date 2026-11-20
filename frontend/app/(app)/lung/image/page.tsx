import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { AnalysisWorkspace } from '@/components/analysis/analysis-workspace'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Lung CT Image Analysis' }

export default function LungImagePage() {
  return (
    <div className="flex flex-col gap-6">
      <Link href="/lung" className="inline-flex w-fit items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Lung modules
      </Link>
      <PageHeader
        eyebrow="Lung Cancer · Module 1"
        title="CT Slice Image Analysis"
        description="Upload one 2D CT slice image (JPG, JPEG, or PNG). This research prototype does not accept full 3D CT/NIfTI volumes."
      />
      <AnalysisWorkspace
        moduleId="lung-cancer-image"
        moduleName="Lung Cancer · Image"
        uploadTitle="CT Slice Upload"
        uploadDescription="One 2D CT scan slice image in JPG, JPEG, or PNG format."
        uploadLabel="Uploaded CT slice"
      />
      <ResearchDisclaimer />
    </div>
  )
}
