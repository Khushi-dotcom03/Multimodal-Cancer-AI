'use client'

import { useEffect, useState } from 'react'
import { useTheme } from 'next-themes'
import { FlaskConical, Monitor, Moon, Palette, Server, Sun } from 'lucide-react'
import { Badge, Panel, PanelHeader, Switch } from '@/components/common/primitives'
import { useDemoMode } from '@/components/providers'
import { API_BASE_URL, isApiConfigured } from '@/lib/api-client'
import { cn } from '@/lib/utils'

const THEMES = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]

export function SettingsPanel() {
  const { theme, setTheme } = useTheme()
  const { demoMode, setDemoMode } = useDemoMode()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Panel>
        <PanelHeader title="Appearance" description="Choose how WeCure looks." icon={Palette} />
        <div role="radiogroup" aria-label="Theme" className="grid grid-cols-3 gap-3 p-5 sm:p-6">
          {THEMES.map((t) => {
            const active = mounted && theme === t.value
            return (
              <button
                key={t.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setTheme(t.value)}
                className={cn(
                  'flex flex-col items-center gap-2 rounded-xl border p-4 text-sm font-medium transition-colors',
                  active ? 'border-ring bg-ring/8 text-foreground' : 'border-border text-muted-foreground hover:text-foreground',
                )}
              >
                <t.icon className="size-5" aria-hidden />
                {t.label}
              </button>
            )
          })}
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Research Preferences" icon={FlaskConical} />
        <div className="flex items-center justify-between gap-4 p-5 sm:p-6">
          <div>
            <label htmlFor="settings-demo" className="text-sm font-medium">
              Demonstration mode
            </label>
            <p className="mt-0.5 text-xs text-muted-foreground">Show clearly labelled sample data across the platform for UI testing.</p>
          </div>
          <Switch id="settings-demo" checked={demoMode} onCheckedChange={setDemoMode} label="Demonstration mode" />
        </div>
      </Panel>

      <Panel className="lg:col-span-2">
        <PanelHeader
          title="Backend Connection"
          description="Python backend (FastAPI / Flask) for model inference."
          icon={Server}
          action={<Badge tone={isApiConfigured ? 'emerald' : 'amber'}>{isApiConfigured ? 'Configured' : 'Not connected'}</Badge>}
        />
        <div className="flex flex-col gap-3 p-5 text-sm sm:p-6">
          <p className="text-muted-foreground">
            Set <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">NEXT_PUBLIC_API_URL</code> in project environment variables to connect the analysis service.
          </p>
          <div className="rounded-xl bg-muted px-4 py-3 font-mono text-xs break-all">{API_BASE_URL || 'No API URL configured'}</div>
        </div>
      </Panel>
    </div>
  )
}
