import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { BreastCancerModuleNav } from '@/components/analysis/breast-cancer-module-nav'
import { BreastClinicalWorkspace } from '@/components/analysis/breast-clinical-workspace'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Breast Cancer Clinical Analysis' }

export default function BreastClinicalPage() {
  return (
    <div className="flex flex-col gap-6">
      <Link href="/modules" className="inline-flex w-fit items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> All cancer modules
      </Link>
      <PageHeader
        eyebrow="Breast Cancer · Module 2"
        title="Clinical Analysis"
        description="Use the existing preliminary symptom summary or predict histologic grade with the saved clinical model."
      />
      <BreastCancerModuleNav />
      <BreastClinicalWorkspace />
      <ResearchDisclaimer />
    </div>
  )
}
