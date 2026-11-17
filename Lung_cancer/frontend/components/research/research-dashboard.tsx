'use client'

import { BarChart3, Cpu, Database, Grid3x3, LineChart as LineIcon, PieChart as PieIcon, Target } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DemoBanner } from '@/components/common/brand'
import { Badge, EmptyState, Panel, PanelHeader } from '@/components/common/primitives'
import { useDemoMode } from '@/components/providers'
import {
  DEMO_ACTIVITY,
  DEMO_CLASS_DISTRIBUTION,
  DEMO_DATASET_SPLIT,
  DEMO_METRICS,
  DEMO_MODEL_COMPARISON,
  DEMO_MODEL_INFO,
  PENDING_MODEL_INFO,
} from '@/lib/demo-data'
import { cn } from '@/lib/utils'
import { ChartTooltip } from './chart-tooltip'

const CHART_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)', 'var(--chart-5)']
const AXIS = { stroke: 'var(--muted-foreground)', fontSize: 12, tickLine: false, axisLine: false } as const

export function ResearchDashboard() {
  const { demoMode } = useDemoMode()
  const model = demoMode ? DEMO_MODEL_INFO : PENDING_MODEL_INFO

  const metrics = [
    { label: 'Accuracy', value: DEMO_METRICS.accuracy, color: 'text-wc-blue', bar: 'bg-wc-blue' },
    { label: 'Precision', value: DEMO_METRICS.precision, color: 'text-wc-violet', bar: 'bg-wc-violet' },
    { label: 'Recall', value: DEMO_METRICS.recall, color: 'text-wc-teal dark:text-wc-turquoise', bar: 'bg-wc-turquoise' },
    { label: 'F1-Score', value: DEMO_METRICS.f1, color: 'text-wc-pink', bar: 'bg-wc-pink' },
  ]

  const pendingChart = (icon: typeof BarChart3, title: string) => (
    <EmptyState icon={icon} title={title} description="Available after model evaluation results are connected." className="h-64" />
  )

  return (
    <div className="flex flex-col gap-6">
      {demoMode && <DemoBanner message="All charts and metrics below are illustrative placeholders, not real model performance." />}

      <section aria-label="Model metrics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((m) => (
          <Panel key={m.label} className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">{m.label}</p>
              <Target className={cn('size-4', m.color)} aria-hidden />
            </div>
            <p className="mt-2 font-mono text-3xl font-bold tracking-tight">{demoMode ? `${(m.value * 100).toFixed(0)}%` : '—'}</p>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
              <div className={cn('h-full rounded-full transition-all', m.bar)} style={{ width: demoMode ? `${m.value * 100}%` : '0%' }} />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">{demoMode ? 'Demo value' : 'Pending evaluation'}</p>
          </Panel>
        ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-3">
        <Panel>
          <PanelHeader title="Model Information" icon={Cpu} action={<Badge tone={demoMode ? 'violet' : 'amber'}>{demoMode ? 'Demo' : 'Pending'}</Badge>} />
          <dl className="flex flex-col divide-y divide-border px-5 sm:px-6">
            {(
              [
                ['Model name', model.name],
                ['Architecture', model.architecture],
                ['Dataset', model.dataset],
                ['Training status', model.trainingStatus],
                ['Evaluation status', model.evaluationStatus],
                ['Version', model.version],
                ['Last updated', model.lastUpdated],
              ] as const
            ).map(([k, v]) => (
              <div key={k} className="flex items-start justify-between gap-4 py-3 text-sm">
                <dt className="text-muted-foreground">{k}</dt>
                <dd className="text-right font-medium">{v}</dd>
              </div>
            ))}
          </dl>
        </Panel>

        <Panel className="xl:col-span-2">
          <PanelHeader title="Research Activity" description="Analyses and reports over time." icon={LineIcon} />
          <div className="p-5 sm:p-6">
            {demoMode ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={DEMO_ACTIVITY} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
                    <XAxis dataKey="month" {...AXIS} />
                    <YAxis {...AXIS} />
                    <Tooltip content={<ChartTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line type="monotone" dataKey="analyses" name="Analyses" stroke="var(--chart-1)" strokeWidth={2.5} dot={false} />
                    <Line type="monotone" dataKey="reports" name="Reports" stroke="var(--chart-4)" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              pendingChart(LineIcon, 'No activity data yet')
            )}
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel>
          <PanelHeader title="Model Comparison" description="Metric comparison across candidate models." icon={BarChart3} />
          <div className="p-5 sm:p-6">
            {demoMode ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={DEMO_MODEL_COMPARISON} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
                    <XAxis dataKey="metric" {...AXIS} />
                    <YAxis {...AXIS} domain={[0, 100]} />
                    <Tooltip content={<ChartTooltip suffix="%" />} cursor={{ fill: 'var(--muted)' }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="modelA" name="Model A" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="modelB" name="Model B" fill="var(--chart-2)" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="modelC" name="Model C" fill="var(--chart-3)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              pendingChart(BarChart3, 'No models to compare')
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="Confusion Matrix" description="Predicted vs. actual class counts." icon={Grid3x3} />
          <div className="p-5 sm:p-6">{demoMode ? <ConfusionMatrix /> : pendingChart(Grid3x3, 'Confusion matrix pending')}</div>
        </Panel>

        <Panel>
          <PanelHeader title="Dataset Split" description="Training, validation and test partitions." icon={PieIcon} />
          <div className="p-5 sm:p-6">
            {demoMode ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={DEMO_DATASET_SPLIT} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="85%" paddingAngle={3} stroke="var(--card)">
                      {DEMO_DATASET_SPLIT.map((d, i) => (
                        <Cell key={d.name} fill={CHART_COLORS[i]} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip suffix="%" />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              pendingChart(PieIcon, 'Dataset split unavailable')
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="Class Distribution" description="Image counts per class in the dataset." icon={Database} />
          <div className="p-5 sm:p-6">
            {demoMode ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={DEMO_CLASS_DISTRIBUTION} layout="vertical" margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="var(--chart-grid)" horizontal={false} />
                    <XAxis type="number" {...AXIS} />
                    <YAxis type="category" dataKey="name" {...AXIS} width={64} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--muted)' }} />
                    <Bar dataKey="count" name="Images" radius={[0, 6, 6, 0]}>
                      {DEMO_CLASS_DISTRIBUTION.map((d, i) => (
                        <Cell key={d.name} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              pendingChart(Database, 'Class distribution unavailable')
            )}
          </div>
        </Panel>
      </div>
    </div>
  )
}

function ConfusionMatrix() {
  const { labels, matrix } = DEMO_METRICS.confusionMatrix
  const max = Math.max(...matrix.flat())
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-1.5 text-center text-sm">
        <caption className="sr-only">Demo confusion matrix</caption>
        <thead>
          <tr>
            <th scope="col" className="text-xs font-medium text-muted-foreground">
              Actual \ Predicted
            </th>
            {labels.map((l) => (
              <th key={l} scope="col" className="text-xs font-medium text-muted-foreground">
                {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, r) => (
            <tr key={labels[r]}>
              <th scope="row" className="text-xs font-medium whitespace-nowrap text-muted-foreground">
                {labels[r]}
              </th>
              {row.map((v, c) => (
                <td
                  key={c}
                  className={cn('h-16 rounded-lg font-mono font-semibold', v / max > 0.5 ? 'text-white' : 'text-foreground')}
                  style={{ background: `color-mix(in oklab, ${r === c ? 'var(--chart-3)' : 'var(--chart-4)'} ${Math.round((v / max) * 85 + 10)}%, transparent)` }}
                >
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
