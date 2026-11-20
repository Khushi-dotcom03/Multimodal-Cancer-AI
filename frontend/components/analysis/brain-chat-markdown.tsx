import type { ReactNode } from 'react'

const LINK = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/

function inline(text: string): ReactNode[] {
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g
  return text.split(pattern).filter(Boolean).map((part, index) => {
    const key = `inline-${index}`
    const link = LINK.exec(part)
    if (link) return <a key={key} href={link[2]} target="_blank" rel="noreferrer" className="text-wc-violet underline underline-offset-2">{link[1]}</a>
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={key}>{part.slice(2, -2)}</strong>
    if (part.startsWith('`') && part.endsWith('`')) return <code key={key} className="rounded bg-muted px-1 py-0.5 font-mono text-[0.9em]">{part.slice(1, -1)}</code>
    if (part.startsWith('*') && part.endsWith('*')) return <em key={key}>{part.slice(1, -1)}</em>
    return part
  })
}

function blockStart(line: string) {
  return /^(#{1,3}\s|```|[-*]\s|\d+\.\s|>\s)/.test(line)
}

export function BrainChatMarkdown({ content }: { content: string }) {
  const lines = content.split(/\r?\n/)
  const blocks: ReactNode[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i].trimEnd()
    if (!line.trim()) { i++; continue }
    if (line.startsWith('```')) {
      const code: string[] = []; i++
      while (i < lines.length && !lines[i].startsWith('```')) code.push(lines[i++])
      if (i < lines.length) i++
      blocks.push(<pre key={`code-${i}`} className="my-2 overflow-x-auto rounded-lg bg-muted p-3 text-xs"><code>{code.join('\n')}</code></pre>)
      continue
    }
    const heading = /^(#{1,3})\s+(.*)$/.exec(line)
    if (heading) {
      const text = inline(heading[2]); const level = heading[1].length
      const className = level === 1 ? 'text-base font-bold' : 'text-sm font-semibold'
      blocks.push(level === 1 ? <h3 key={`h-${i}`} className={className}>{text}</h3> : <h4 key={`h-${i}`} className={className}>{text}</h4>)
      i++; continue
    }
    if (/^[-*]\s/.test(line)) {
      const items: ReactNode[] = []
      while (i < lines.length && /^[-*]\s/.test(lines[i].trim())) items.push(<li key={`li-${i}`}>{inline(lines[i++].trim().replace(/^[-*]\s+/, ''))}</li>)
      blocks.push(<ul key={`ul-${i}`} className="my-2 list-disc space-y-1 pl-5">{items}</ul>); continue
    }
    if (/^\d+\.\s/.test(line)) {
      const items: ReactNode[] = []
      while (i < lines.length && /^\d+\.\s/.test(lines[i].trim())) items.push(<li key={`oli-${i}`}>{inline(lines[i++].trim().replace(/^\d+\.\s+/, ''))}</li>)
      blocks.push(<ol key={`ol-${i}`} className="my-2 list-decimal space-y-1 pl-5">{items}</ol>); continue
    }
    if (line.startsWith('> ')) {
      blocks.push(<blockquote key={`quote-${i}`} className="my-2 border-l-2 border-wc-cyan pl-3 text-muted-foreground">{inline(line.slice(2))}</blockquote>); i++; continue
    }
    const paragraph = [line]; i++
    while (i < lines.length && lines[i].trim() && !blockStart(lines[i].trim())) paragraph.push(lines[i++].trim())
    blocks.push(<p key={`p-${i}`} className="my-2 leading-6">{paragraph.map((part, index) => <span key={index}>{index > 0 && <br />}{inline(part)}</span>)}</p>)
  }
  return <div className="break-words">{blocks}</div>
}
