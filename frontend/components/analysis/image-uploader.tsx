'use client'

/* eslint-disable @next/next/no-img-element -- previews are local object URLs */
import { useRef, useState } from 'react'
import { AlertCircle, ImagePlus, RefreshCw, Trash2, UploadCloud } from 'lucide-react'
import { Panel, PanelHeader } from '@/components/common/primitives'
import { cn } from '@/lib/utils'
import { ACCEPTED_EXTENSIONS, MAX_IMAGE_SIZE_MB, validateImageFile } from '@/services/analysis-service'

interface ImageUploaderProps {
  file: File | null
  previewUrl: string | null
  onFileChange: (file: File | null) => void
  disabled?: boolean
}

export function ImageUploader({ file, previewUrl, onFileChange, disabled }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const accept = (candidate: File | undefined) => {
    if (!candidate) return
    const message = validateImageFile(candidate)
    if (message) {
      setError(message)
      return
    }
    setError(null)
    onFileChange(candidate)
  }

  const openPicker = () => inputRef.current?.click()

  return (
    <Panel className="h-full">
      <PanelHeader title="Image Upload" description="Dermoscopic or clinical skin lesion image." icon={ImagePlus} />
      <div className="p-5 sm:p-6">
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(',') + ',image/jpeg,image/png'}
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          onChange={(e) => {
            accept(e.target.files?.[0])
            e.target.value = ''
          }}
        />

        {file && previewUrl ? (
          <div className="flex flex-col gap-4">
            <div className="relative flex aspect-[4/3] items-center justify-center overflow-hidden rounded-xl border border-border bg-[repeating-conic-gradient(var(--muted)_0_25%,transparent_0_50%)] bg-[length:20px_20px]">
              <img src={previewUrl} alt={`Preview of ${file.name}`} className="max-h-full max-w-full object-contain" />
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={openPicker}
                disabled={disabled}
                className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-50"
              >
                <RefreshCw className="size-4" aria-hidden />
                Upload another image
              </button>
              <button
                type="button"
                onClick={() => {
                  setError(null)
                  onFileChange(null)
                }}
                disabled={disabled}
                className="inline-flex h-10 items-center gap-2 rounded-xl border border-red-500/30 px-4 text-sm font-medium text-red-600 transition-colors hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400"
              >
                <Trash2 className="size-4" aria-hidden />
                Remove image
              </button>
            </div>
          </div>
        ) : (
          <div
            role="button"
            tabIndex={0}
            aria-label="Upload image: drag and drop or press Enter to browse files"
            onClick={openPicker}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                openPicker()
              }
            }}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              accept(e.dataTransfer.files?.[0])
            }}
            className={cn(
              'flex aspect-[4/3] cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed px-6 text-center transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/40',
              dragging ? 'border-wc-turquoise bg-wc-turquoise/8' : 'border-border hover:border-wc-turquoise/60 hover:bg-muted/50',
            )}
          >
            <span className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-wc-turquoise/20 to-wc-violet/20 text-wc-teal dark:text-wc-turquoise">
              <UploadCloud className="size-7" aria-hidden />
            </span>
            <div>
              <p className="text-base font-semibold">{dragging ? 'Drop image to upload' : 'Drag and drop your image here'}</p>
              <p className="mt-1 text-sm text-muted-foreground">or</p>
            </div>
            <span className="inline-flex h-10 items-center rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground">Browse Files</span>
            <p className="text-xs text-muted-foreground">
              Supported formats: <span className="font-medium text-foreground">JPG, JPEG, PNG</span> · Max {MAX_IMAGE_SIZE_MB} MB
            </p>
          </div>
        )}

        {error && (
          <p role="alert" className="mt-4 flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/8 px-3 py-2.5 text-sm text-red-700 dark:text-red-300">
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            {error}
          </p>
        )}
      </div>
    </Panel>
  )
}
