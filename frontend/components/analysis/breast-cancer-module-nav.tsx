'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Bot, FileImage, Layers3, Stethoscope } from 'lucide-react'
import { cn } from '@/lib/utils'

const MODULES = [
  { href: '/breast-image', label: 'Image Analysis', icon: FileImage },
  { href: '/breast-clinical', label: 'Clinical Analysis', icon: Stethoscope },
  { href: '/breast-evidence-review', label: 'Combined Analysis', icon: Layers3 },
  { href: '/breast-ai-assistant', label: 'Breast Cancer AI Assistant', icon: Bot },
]

export function BreastCancerModuleNav() {
  const pathname = usePathname()

  return (
    <nav aria-label="Breast Cancer modules" className="-mx-1 overflow-x-auto px-1">
      <ul className="flex min-w-max gap-2 border-b border-border">
        {MODULES.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'inline-flex min-h-10 items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors',
                  active ? 'border-wc-turquoise text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                <Icon className="size-4" aria-hidden />
                {label}
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
