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
        description="Each module is an independent research area. Skin Cancer is the initial research prototype; other modules are in development and do not yet have working models."
      />
      <ModuleExplorer initialQuery={q ?? ''} />
    </div>
  )
}
