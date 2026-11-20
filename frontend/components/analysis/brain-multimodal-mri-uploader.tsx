'use client'

/* eslint-disable @next/next/no-img-element -- local uploaded image preview */
import { useEffect, useId, useState } from 'react'
import { AlertCircle, Brain, RefreshCw, Trash2, UploadCloud } from 'lucide-react'
import { Panel, PanelHeader } from '@/components/common/primitives'
import { cn } from '@/lib/utils'

const MAX_FILES = 48
const MAX_FILE_BYTES = 15 * 1024 * 1024

interface Props {
  files: File[]
  previewUrl: string | null
  onFilesChange: (files: File[]) => void
  disabled?: boolean
}

export function BrainMultimodalMRIUploader({ files, previewUrl, onFilesChange, disabled }: Props) {
  const inputId = useId()
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const preventFileNavigation = (event: DragEvent) => {
      if (Array.from(event.dataTransfer?.types ?? []).includes('Files')) event.preventDefault()
    }
    window.addEventListener('dragover', preventFileNavigation)
    window.addEventListener('drop', preventFileNavigation)
    return () => {
      window.removeEventListener('dragover', preventFileNavigation)
      window.removeEventListener('drop', preventFileNavigation)
    }
  }, [])

  const acceptFiles = (selection: FileList | File[]) => {
    const candidates = Array.from(selection)
    if (!candidates.length) return
    if (candidates.length > MAX_FILES) { setError(`Choose no more than ${MAX_FILES} slices for one patient.`); return }
    const invalid = candidates.find((file) => {
      const extensionOk = /\.(jpe?g|png)$/i.test(file.name)
      const typeOk = !file.type || ['image/jpeg', 'image/jpg', 'image/pjpeg', 'image/png', 'application/octet-stream'].includes(file.type.toLowerCase())
      return !extensionOk || !typeOk || file.size === 0 || file.size > MAX_FILE_BYTES
    })
    if (invalid) {
      setError(invalid.size > MAX_FILE_BYTES ? `${invalid.name} exceeds the 15 MB per-slice limit.` : `Unsupported or empty image: ${invalid.name}. Choose PNG, JPG, or JPEG slices.`)
      return
    }
    if (candidates.reduce((total, file) => total + file.size, 0) > 100 * 1024 * 1024) { setError('Combined slice size must be 100 MB or smaller.'); return }
    setError(null)
    onFilesChange(candidates)
  }

  return <Panel className="h-full">
    <PanelHeader title="Brain MRI Upload" description="Every selected slice runs through MRI screening; all selected T1CE slices are also sent to the IDH model." icon={Brain} />
    <div className="relative p-5 sm:p-6">
      <input id={inputId} type="file" multiple accept=".png,.jpg,.jpeg,image/png,image/jpeg" aria-label="Choose T1CE brain MRI slices" className="peer sr-only" disabled={disabled} onChange={(event) => { if (event.currentTarget.files) acceptFiles(event.currentTarget.files); event.currentTarget.value = '' }} />
      {files.length > 0 ? <div className="flex flex-col gap-4">
        {previewUrl && <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-xl border border-border bg-muted"><img src={previewUrl} alt={`Preview of ${files[0].name}`} className="max-h-full max-w-full object-contain" /></div>}
        <p className="text-sm text-muted-foreground"><span className="font-medium text-foreground">{files.length} slice{files.length === 1 ? '' : 's'} selected</span> · previewing {files[0].name}</p>
        <ul className="max-h-28 space-y-1 overflow-auto rounded-lg border border-border p-3 text-xs text-muted-foreground" aria-label="Selected MRI slices">{files.map((file) => <li key={`${file.name}-${file.lastModified}`} className="truncate" title={file.name}>{file.name}</li>)}</ul>
        <div className="flex flex-wrap gap-2">
          <label htmlFor={inputId} className={`inline-flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-medium hover:bg-muted ${disabled ? 'pointer-events-none opacity-50' : ''}`}><RefreshCw className="size-4" /> Replace slices</label>
          <button type="button" onClick={() => { setError(null); onFilesChange([]) }} disabled={disabled} className="inline-flex h-10 items-center gap-2 rounded-xl border border-red-500/30 px-4 text-sm font-medium text-red-600 hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400"><Trash2 className="size-4" /> Remove slices</button>
        </div>
      </div> : <label htmlFor={inputId} onDragEnter={(event) => { event.preventDefault(); setDragging(true) }} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={(event) => { event.preventDefault(); if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false) }} onDrop={(event) => { event.preventDefault(); event.stopPropagation(); setDragging(false); acceptFiles(event.dataTransfer.files) }} className={cn('relative flex aspect-[4/3] cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed px-6 text-center outline-none peer-focus-visible:ring-3 peer-focus-visible:ring-ring/40', dragging ? 'border-wc-violet bg-wc-violet/8' : 'border-border hover:border-wc-violet/60 hover:bg-muted/50')}>
        <span className="flex size-14 items-center justify-center rounded-2xl bg-wc-violet/10 text-wc-violet"><UploadCloud className="size-7" /></span>
        <div><p className="text-base font-semibold">{dragging ? 'Drop T1CE slices to upload' : 'Drag and drop T1CE slices here'}</p><p className="mt-1 text-sm text-muted-foreground">or</p></div>
        <span className="inline-flex h-10 items-center rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground">Browse Files</span>
        <p className="text-xs text-muted-foreground">PNG, JPG, JPEG · up to {MAX_FILES} slices · same patient only</p>
      </label>}
      {error && <p role="alert" className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/8 px-3 py-2.5 text-sm text-red-700 dark:text-red-300"><AlertCircle className="mt-0.5 size-4 shrink-0" />{error}</p>}
    </div>
  </Panel>
}
