import { HeroSection } from '@/components/dashboard/hero-section'
import { QuickActions } from '@/components/dashboard/quick-actions'
import { ResearchActivity } from '@/components/dashboard/research-activity'
import { StatCards } from '@/components/dashboard/stat-cards'
import { ModuleGrid } from '@/components/modules/module-grid'
import { RESEARCH_MODULES } from '@/lib/modules'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

export default function OverviewPage() {
  return (
    <div className="flex flex-col gap-8">
      <HeroSection />
      <StatCards />
      <section aria-labelledby="modules-heading" className="flex flex-col gap-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 id="modules-heading" className="text-xl font-bold tracking-tight">
              Cancer Research Modules
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">Modular research areas — each can be activated independently.</p>
          </div>
          <Link href="/modules" className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-wc-teal hover:underline dark:text-wc-turquoise">
            View all <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
        <ModuleGrid modules={RESEARCH_MODULES} />
      </section>
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <ResearchActivity />
        </div>
        <QuickActions />
      </div>
    </div>
  )
}
