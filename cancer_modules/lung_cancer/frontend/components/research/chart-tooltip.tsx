'use client'

interface TooltipEntry {
  name?: string | number
  value?: string | number
  color?: string
  payload?: { fill?: string }
}

interface ChartTooltipProps {
  active?: boolean
  label?: string | number
  payload?: TooltipEntry[]
  suffix?: string
}

export function ChartTooltip({ active, payload, label, suffix = '' }: ChartTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-lg">
      {label !== undefined && <p className="mb-1 font-semibold">{label}</p>}
      <ul className="flex flex-col gap-1">
        {payload.map((p) => (
          <li key={String(p.name)} className="flex items-center gap-2">
            <span className="size-2 rounded-full" style={{ background: p.color ?? p.payload?.fill }} aria-hidden />
            <span className="text-muted-foreground">{p.name}</span>
            <span className="ml-auto font-mono font-medium">
              {p.value}
              {suffix}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
