import type { Metadata } from 'next'
import Link from 'next/link'
import { Activity, ExternalLink, Layers3, ScanSearch, MessageCircle } from 'lucide-react'
import { PageHeader, Panel } from '@/components/common/primitives'

export const metadata: Metadata = { title: 'Breast Cancer Research Modules' }

const apps = [
  { title: 'Ultrasound Image Analysis', description: 'The existing BUSI image classifier and image analysis interface.', port: 8501, icon: ScanSearch, command: 'streamlit run image_dashboard.py --server.port 8501', folder: 'module1_image_analysis' },
  { title: 'Clinical Analysis', description: 'The existing breast health and clinical grade assessment tools.', port: 8502, icon: Activity, command: 'streamlit run breast_health_assessment.py --server.port 8502', folder: 'module2_clinical_analysis' },
]

export default function BreastPage() {
  return <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Research Module · Breast Cancer" title="Breast Cancer Analysis" description="Access Breast Cancer image, clinical, and independent evidence analysis, or open the dedicated AI Assistant." />
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {apps.map(({ title, description, port, icon: Icon, command, folder }) => <Panel key={title} className="flex flex-col gap-4 p-5">
        <div className="flex items-center gap-2 font-semibold"><Icon className="size-5 text-wc-pink" />{title}</div>
        <p className="text-sm text-muted-foreground">{description}</p>
        <p className="text-xs text-muted-foreground">Folder: <code>cancer_modules/breast_cancer/{folder}</code></p>
        <code className="rounded-lg bg-muted p-3 text-xs">{command}</code>
        <a className="inline-flex items-center gap-2 text-sm font-semibold text-primary" href={`http://localhost:${port}`} target="_blank" rel="noreferrer">Open local app <ExternalLink className="size-4" /></a>
      </Panel>)}

      <Panel className="flex flex-col gap-4 p-5">
        <div className="flex items-center gap-2 font-semibold"><Layers3 className="size-5 text-wc-pink" />Combined Analysis</div>
        <p className="text-sm text-muted-foreground">Review image and clinical model outputs separately without combining them.</p>
        <p className="text-xs text-muted-foreground">Independent image and clinical evidence</p>
        <div className="mt-auto">
          <Link href="/breast-evidence-review" className="inline-flex items-center gap-2 text-sm font-semibold text-primary">Open Combined Analysis <ExternalLink className="size-4" /></Link>
        </div>
      </Panel>

      <Panel className="flex flex-col gap-4 p-5">
        <div className="flex items-center gap-2 font-semibold"><MessageCircle className="size-5 text-wc-pink" />Breast Cancer AI Assistant</div>
        <p className="text-sm text-muted-foreground">Ask breast-cancer-related educational questions and continue a conversation with the dedicated AI assistant.</p>
        <p className="text-xs text-muted-foreground">AI-powered educational support</p>
        <div className="mt-auto">
          <Link href="/breast-ai-assistant" className="inline-flex items-center gap-2 text-sm font-semibold text-primary">Open AI Assistant <ExternalLink className="size-4" /></Link>
        </div>
      </Panel>
    </div>
    <p className="text-sm text-muted-foreground">The existing image and clinical applications continue to use their original code and model workflows. The AI Assistant is a separate educational tool and does not diagnose or prescribe.</p>
    <Link href="/modules" className="text-sm text-primary">Back to all cancer modules</Link>
  </div>
}
