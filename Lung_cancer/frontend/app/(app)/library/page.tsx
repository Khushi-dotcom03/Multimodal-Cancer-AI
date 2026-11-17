import type { Metadata } from 'next'
import { PageHeader } from '@/components/common/primitives'
import { LibraryBrowser } from '@/components/library/library-browser'

export const metadata: Metadata = { title: 'Research Library' }

export default function LibraryPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Research Library"
        title="Research Library"
        description="Curated slots for articles, publications, datasets and tools. Entries are placeholders until verified references are added."
      />
      <LibraryBrowser />
    </div>
  )
}
