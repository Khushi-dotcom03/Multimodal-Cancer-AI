import type { Metadata } from 'next'
import { PageHeader } from '@/components/common/primitives'
import { ReportsTable } from '@/components/reports/reports-table'

export const metadata: Metadata = { title: 'Reports' }

export default function ReportsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Reports"
        title="Research Reports"
        description="Review, filter and download reports generated from completed research analyses."
      />
      <ReportsTable />
    </div>
  )
}
