import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { FusionAnalysis } from '@/components/lung/fusion-analysis'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Lung Image + Clinical Analysis' }

export default function LungFusionPage() {
  return (
    <div className="flex flex-col gap-6">
      <Link href="/lung" className="inline-flex w-fit items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Lung modules
      </Link>
      <PageHeader
        eyebrow="Lung Cancer · Module 3"
        title="Image + Clinical Analysis"
        description="Run the CT image and clinical models together and review both outputs in one place."
      />
      <FusionAnalysis />
      <ResearchDisclaimer />
    </div>
  )
}
