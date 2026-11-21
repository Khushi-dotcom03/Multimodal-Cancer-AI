import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { BreastCombinedAnalysisWorkspace } from '@/components/analysis/breast-combined-analysis-workspace'
import { BreastCancerModuleNav } from '@/components/analysis/breast-cancer-module-nav'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = {
  title: 'Breast Cancer Combined Analysis',
  description: 'Review independent breast ultrasound and clinical grade research outputs. No combined cancer score is generated.',
}

export default function BreastEvidenceReviewPage() {
  return (
    <div className="flex flex-col gap-6">
      <Link href="/modules" className="inline-flex w-fit items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> All cancer modules
      </Link>
      <PageHeader
        eyebrow="Breast Cancer | Module 3"
        title="Combined Analysis"
        description="Run the existing Module 1 ultrasound and Module 2 clinical pipelines independently using their existing inputs. Fusion is unavailable without compatible patient-linked training data."
      />
      <BreastCancerModuleNav />
      <BreastCombinedAnalysisWorkspace />
      <ResearchDisclaimer />
    </div>
  )
}
