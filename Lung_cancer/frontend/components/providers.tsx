'use client'

import { ThemeProvider } from 'next-themes'
import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const DEMO_STORAGE_KEY = 'wecure-demo-mode'

interface DemoModeContextValue {
  demoMode: boolean
  setDemoMode: (value: boolean) => void
}

const DemoModeContext = createContext<DemoModeContextValue | null>(null)

function DemoModeProvider({ children }: { children: React.ReactNode }) {
  const [demoMode, setDemoModeState] = useState(false)

  useEffect(() => {
    setDemoModeState(localStorage.getItem(DEMO_STORAGE_KEY) === 'true')
  }, [])

  const setDemoMode = useCallback((value: boolean) => {
    setDemoModeState(value)
    localStorage.setItem(DEMO_STORAGE_KEY, String(value))
  }, [])

  return <DemoModeContext.Provider value={{ demoMode, setDemoMode }}>{children}</DemoModeContext.Provider>
}

export function useDemoMode() {
  const ctx = useContext(DemoModeContext)
  if (!ctx) throw new Error('useDemoMode must be used within Providers')
  return ctx
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem storageKey="wecure-theme">
      <DemoModeProvider>{children}</DemoModeProvider>
    </ThemeProvider>
  )
}
