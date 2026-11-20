import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { ClinicalAnalysis } from '@/components/lung/clinical-analysis'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Lung Clinical Analysis' }

export default function LungClinicalPage() {
  return (
    <div className="flex flex-col gap-6">
      <Link href="/lung" className="inline-flex w-fit items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Lung modules
      </Link>
      <PageHeader
        eyebrow="Lung Cancer · Module 2"
        title="Clinical Risk-Level Analysis"
        description="Enter the numeric-coded fields used by the included clinical CSV to estimate its Low, Medium, or High label."
      />
      <ClinicalAnalysis />
      <ResearchDisclaimer />
    </div>
  )
}
