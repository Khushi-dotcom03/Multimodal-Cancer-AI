import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { AnalysisWorkspace } from '@/components/analysis/analysis-workspace'
import { BreastCancerModuleNav } from '@/components/analysis/breast-cancer-module-nav'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Breast Ultrasound Image Analysis' }

export default function BreastImagePage() {
  return (
    <div className="flex flex-col gap-6">
      <Link href="/modules" className="inline-flex w-fit items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> All cancer modules
      </Link>
      <PageHeader
        eyebrow="Breast Cancer · Module 1"
        title="Ultrasound Image Analysis"
        description="Upload a BUSI breast ultrasound image to run the existing image validator and three-class model."
      />
      <BreastCancerModuleNav />
      <AnalysisWorkspace
        moduleId="breast-cancer-image"
        moduleName="Breast Cancer"
        uploadTitle="Ultrasound Image Upload"
        uploadDescription="Upload a breast ultrasound image in JPG, JPEG, or PNG format."
        uploadLabel="Uploaded ultrasound"
      />
      <ResearchDisclaimer />
    </div>
  )
}
