import type { Metadata } from 'next'
import { Compass, Eye, Layers, ShieldCheck, Target, Users } from 'lucide-react'
import { ResearchDisclaimer } from '@/components/common/brand'
import { PageHeader, Panel } from '@/components/common/primitives'
import { RESEARCH_MODULES } from '@/lib/modules'

export const metadata: Metadata = { title: 'About WeCure' }

const PILLARS = [
  { icon: Target, title: 'Mission', text: 'Explore how artificial intelligence can support cancer research through intelligent medical image analysis and multimodal insights.' },
  { icon: Eye, title: 'Vision', text: 'A modular research platform where each cancer type can be studied with dedicated, transparent and well-evaluated models.' },
  { icon: Compass, title: 'Approach', text: 'Start with a focused Skin Cancer prototype, validate the workflow end-to-end, then extend to breast, lung and brain research modules.' },
  { icon: ShieldCheck, title: 'Responsible AI', text: 'Clear labelling of demo data, explainability outputs and a strict research-only scope — never a diagnostic tool.' },
]

const OBJECTIVES = [
  'Build a reliable image upload and analysis workflow for research use.',
  'Integrate a trained deep learning model for skin lesion classification.',
  'Provide explainability outputs such as attention heatmaps.',
  'Report model evaluation metrics transparently.',
  'Design the architecture so new cancer modules can be added independently.',
]

export default function AboutPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="About WeCure"
        title="AI-Powered Multimodal Cancer Research"
        description="WeCure is a research and educational platform exploring the potential of artificial intelligence in cancer research."
      />

      <div className="grid gap-4 sm:grid-cols-2">
        {PILLARS.map((p) => (
          <Panel key={p.title} className="p-6">
            <span className="flex size-11 items-center justify-center rounded-xl brand-gradient text-white">
              <p.icon className="size-5" aria-hidden />
            </span>
            <h2 className="mt-4 text-lg font-semibold">{p.title}</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{p.text}</p>
          </Panel>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel className="p-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <Target className="size-5 text-wc-teal dark:text-wc-turquoise" aria-hidden /> Research objectives
          </h2>
          <ol className="mt-4 flex flex-col gap-3">
            {OBJECTIVES.map((o, i) => (
              <li key={o} className="flex gap-3 text-sm">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-xs font-semibold">{i + 1}</span>
                <span className="leading-relaxed">{o}</span>
              </li>
            ))}
          </ol>
        </Panel>
        <Panel className="p-6">
          <h2 className="flex items-center gap-2 text-lg font-semibold">
            <Layers className="size-5 text-wc-violet" aria-hidden /> Module roadmap
          </h2>
          <ul className="mt-4 flex flex-col gap-3">
            {RESEARCH_MODULES.map((m) => (
              <li key={m.id} className="flex items-center justify-between gap-3 rounded-xl border border-border px-4 py-3 text-sm">
                <span className="font-medium">{m.name}</span>
                <span className="text-xs text-muted-foreground">{m.statusLabel}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel className="p-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Users className="size-5 text-wc-pink" aria-hidden /> Team
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Team member profiles will be added here. Each entry can include name, role, research focus and contact details.
        </p>
      </Panel>

      <ResearchDisclaimer />
    </div>
  )
}
