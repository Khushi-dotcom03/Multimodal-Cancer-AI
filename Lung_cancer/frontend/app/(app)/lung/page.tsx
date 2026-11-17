import type { Metadata } from 'next'
import Link from 'next/link'
import { Activity, ArrowRight, ScanSearch, Workflow } from 'lucide-react'
import { PageHeader, Panel, PanelHeader } from '@/components/common/primitives'
import { ResearchDisclaimer } from '@/components/common/brand'

export const metadata: Metadata = { title: 'Lung Cancer Research Modules' }

export default function LungModulePage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Lung Cancer · Research Module"
        title="Lung Cancer Analysis"
        description="Image, clinical aur combined workflow modules. Teesra module dono existing models ke outputs ek jagah dikhata hai."
      />
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        <Panel className="flex flex-col">
          <PanelHeader title="Module 1 · Image Analysis" description="Single 2D CT slice image ka research classification." icon={ScanSearch} />
          <div className="flex flex-1 flex-col p-5 sm:p-6">
            <p className="text-sm leading-relaxed text-muted-foreground">
              JPG, JPEG ya PNG CT slice upload karo. Is prototype ka model 3D NIfTI/CT volume accept nahi karta.
            </p>
            <Link href="/lung/image" className="mt-5 inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground hover:opacity-90">
              Open Image Analysis <ArrowRight className="size-4" />
            </Link>
          </div>
        </Panel>
        <Panel className="flex flex-col">
          <PanelHeader title="Module 2 · Clinical Analysis" description="Clinical and risk-factor values ka dataset-level estimate." icon={Activity} />
          <div className="flex flex-1 flex-col p-5 sm:p-6">
            <p className="text-sm leading-relaxed text-muted-foreground">
              Form ke fields source CSV ke numeric coding ko follow karte hain. Output Low, Medium ya High dataset label hai, confirmed diagnosis nahi.
            </p>
            <Link href="/lung/clinical" className="mt-5 inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground hover:opacity-90">
              Open Clinical Analysis <ArrowRight className="size-4" />
            </Link>
          </div>
        </Panel>
        <Panel className="flex flex-col">
          <PanelHeader title="Module 3 · Image + Clinical" description="CT aur clinical models ke independent results ek workflow mein." icon={Workflow} />
          <div className="flex flex-1 flex-col p-5 sm:p-6">
            <p className="text-sm leading-relaxed text-muted-foreground">
              CT slice aur Module 2 ke clinical fields ek saath do. Dono model outputs alag dikhte hain; linked training data ke bina joint fusion score nahi banega.
            </p>
            <Link href="/lung/fusion" className="mt-5 inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground hover:opacity-90">
              Open Image + Clinical <ArrowRight className="size-4" />
            </Link>
          </div>
        </Panel>
      </div>
      <ResearchDisclaimer />
    </div>
  )
}
