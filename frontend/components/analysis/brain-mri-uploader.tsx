'use client'

/* eslint-disable @next/next/no-img-element -- previews use local object URLs */
import { useEffect, useId, useState } from 'react'
import { AlertCircle, Brain, RefreshCw, Trash2, UploadCloud } from 'lucide-react'
import { Panel, PanelHeader } from '@/components/common/primitives'
import { cn } from '@/lib/utils'
import { MAX_IMAGE_SIZE_BYTES, MAX_IMAGE_SIZE_MB } from '@/services/analysis-service'

interface Props {
  file: File | null
  previewUrl: string | null
  onFileChange: (file: File | null) => void
  disabled?: boolean
}

export function BrainMRIUploader({ file, previewUrl, onFileChange, disabled }: Props) {
  const inputId = useId()
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Keep the browser from navigating to a dropped file when the drop lands
    // outside the dropzone. The dropzone still owns selection and validation.
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

  const accept = (candidate?: File) => {
    if (!candidate) return
    const extensionAllowed = /\.(jpe?g|png)$/i.test(candidate.name)
    const typeAllowed = !candidate.type || ['image/jpeg', 'image/jpg', 'image/pjpeg', 'image/png', 'application/octet-stream'].includes(candidate.type.toLowerCase())
    if (!extensionAllowed || !typeAllowed) { setError('Unsupported file format. Please choose a JPG, JPEG, or PNG image.'); return }
    if (candidate.size === 0) { setError('The selected file is empty.'); return }
    if (candidate.size > MAX_IMAGE_SIZE_BYTES) { setError(`File is too large. Maximum size is ${MAX_IMAGE_SIZE_MB} MB.`); return }
    setError(null); onFileChange(candidate)
  }

  return <Panel className="h-full">
    <PanelHeader title="Brain MRI Upload" description="Upload a brain MRI image for image-based research analysis." icon={Brain} />
    <div className="relative p-5 sm:p-6">
      <input id={inputId} type="file" accept=".png,.jpg,.jpeg,image/png,image/jpeg" aria-label="Choose a brain MRI image" className="peer sr-only" onChange={(event) => { accept(event.currentTarget.files?.[0] ?? undefined); event.currentTarget.value = '' }} />
      {file && previewUrl ? <div className="flex flex-col gap-4">
        <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-xl border border-border bg-muted"><img src={previewUrl} alt={`Preview of ${file.name}`} className="max-h-full max-w-full object-contain" /></div>
        <p className="truncate text-sm text-muted-foreground" title={file.name}>Selected image: <span className="font-medium text-foreground">{file.name}</span></p>
        <div className="flex flex-wrap gap-2">
          <label htmlFor={inputId} className={`inline-flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-medium hover:bg-muted ${disabled ? 'pointer-events-none opacity-50' : ''}`}><RefreshCw className="size-4" /> Replace image</label>
          <button type="button" onClick={() => { setError(null); onFileChange(null) }} disabled={disabled} className="inline-flex h-10 items-center gap-2 rounded-xl border border-red-500/30 px-4 text-sm font-medium text-red-600 hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400"><Trash2 className="size-4" /> Remove image</button>
        </div>
      </div> : <label htmlFor={inputId} onDragEnter={(event) => { event.preventDefault(); setDragging(true) }} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={(event) => { event.preventDefault(); if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false) }} onDrop={(event) => { event.preventDefault(); event.stopPropagation(); setDragging(false); accept(event.dataTransfer.files?.[0]) }} className={cn('relative flex aspect-[4/3] cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed px-6 text-center outline-none peer-focus-visible:ring-3 peer-focus-visible:ring-ring/40', dragging ? 'border-wc-violet bg-wc-violet/8' : 'border-border hover:border-wc-violet/60 hover:bg-muted/50')}>
        <span className="flex size-14 items-center justify-center rounded-2xl bg-wc-violet/10 text-wc-violet"><UploadCloud className="size-7" /></span>
        <div><p className="text-base font-semibold">{dragging ? 'Drop MRI image to upload' : 'Drag and drop your brain MRI here'}</p><p className="mt-1 text-sm text-muted-foreground">or</p></div>
        <span className="inline-flex h-10 items-center rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground">Browse Files</span>
        <p className="text-xs text-muted-foreground">Supported formats: <span className="font-medium text-foreground">JPG, JPEG, PNG</span> · Max {MAX_IMAGE_SIZE_MB} MB</p>
      </label>}
      {error && <p role="alert" className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/8 px-3 py-2.5 text-sm text-red-700 dark:text-red-300"><AlertCircle className="mt-0.5 size-4 shrink-0" />{error}</p>}
    </div>
  </Panel>
}
