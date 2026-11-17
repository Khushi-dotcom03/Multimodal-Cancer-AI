import type { Metadata } from 'next'
import { BrainClinicalWorkspace } from '@/components/analysis/brain-clinical-workspace'
import { PageHeader } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Brain Clinical Assessment & Reporting' }

export default function BrainClinicalPage() {
  return <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Clinical Assessment · Brain Cancer" title="Brain Clinical Assessment & Reporting" description="Record patient-reported and radiology information in a structured report. The separate research model uses only Age, Sex, and Tumour location." />
    <BrainClinicalWorkspace />
  </div>
}
