import type { Metadata } from 'next'
import { BreastAIAssistant } from '@/components/breast-ai-assistant/breast-ai-assistant'

export const metadata: Metadata = {
  title: 'Breast Cancer AI Assistant',
  description: 'Educational AI assistant focused on breast cancer.',
}

export default function BreastAIAssistantPage() {
  return <BreastAIAssistant />
}
