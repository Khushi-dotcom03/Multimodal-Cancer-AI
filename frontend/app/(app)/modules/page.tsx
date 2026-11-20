import type { Metadata } from 'next'
import { PageHeader } from '@/components/common/primitives'
import { ModuleExplorer } from '@/components/modules/module-explorer'

export const metadata: Metadata = { title: 'Cancer Research Modules' }

export default async function ModulesPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const { q } = await searchParams
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Research Modules"
        title="Cancer Research Modules"
        description="Explore the four cancer research areas and their existing module-specific interfaces. Brain model inference requires the original checkpoint and clinical CSV to be supplied locally."
      />
      <ModuleExplorer initialQuery={q ?? ''} />
    </div>
  )
}
