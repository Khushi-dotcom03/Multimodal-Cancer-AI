import type { Metadata } from 'next'
import { PageHeader } from '@/components/common/primitives'
import { SettingsPanel } from '@/components/settings/settings-panel'

export const metadata: Metadata = { title: 'Settings' }

export default function SettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader eyebrow="Settings" title="Settings" description="Appearance, research preferences and backend connection." />
      <SettingsPanel />
    </div>
  )
}
