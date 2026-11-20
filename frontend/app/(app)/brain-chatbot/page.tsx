import type { Metadata } from 'next'
import { PageHeader } from '@/components/common/primitives'
import { BrainChatbot } from '@/components/analysis/brain-chatbot'

export const metadata: Metadata = { title: 'Brain AI Assistant' }

export default function BrainChatbotPage() {
  return <div className="flex flex-col gap-6">
    <PageHeader eyebrow="Brain Cancer · Education & Research" title="Brain AI Assistant" description="Ask clear, brain-focused questions about tumors, MRI terminology, biomarkers, and results from the Brain analysis tools." />
    <BrainChatbot />
  </div>
}
