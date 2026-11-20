import type { Metadata } from 'next'
import { PageHeader } from '@/components/common/primitives'
import { ResearchDashboard } from '@/components/research/research-dashboard'

export const metadata: Metadata = { title: 'Research Dashboard' }

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Research Dashboard"
        title="Model Evaluation & Analytics"
        description="Performance metrics, dataset composition and research activity. Values appear once a trained model and evaluation results are connected."
      />
      <ResearchDashboard />
    </div>
  )
}
