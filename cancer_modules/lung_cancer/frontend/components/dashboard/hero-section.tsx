import Image from 'next/image'
import Link from 'next/link'
import { ArrowRight, Layers, ScanSearch, Sparkles } from 'lucide-react'

export function HeroSection() {
  return (
    <section className="relative isolate overflow-hidden rounded-3xl bg-wc-navy text-white shadow-xl shadow-wc-navy/20">
      <Image
        src="/images/hero-dna.png"
        alt=""
        fill
        priority
        sizes="(min-width: 1024px) 1100px, 100vw"
        className="-z-10 object-cover object-right opacity-90"
      />
      <div className="absolute inset-0 -z-10 bg-gradient-to-r from-wc-navy via-wc-navy/85 to-wc-navy/10" aria-hidden />
      <div className="pointer-events-none absolute -bottom-24 -left-16 -z-10 size-72 rounded-full bg-wc-turquoise/25 blur-3xl" aria-hidden />

      <div className="flex max-w-2xl flex-col gap-6 px-6 py-10 sm:px-10 sm:py-14 lg:py-16">
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium backdrop-blur">
          <Sparkles className="size-3.5 text-wc-turquoise" aria-hidden />
          AI-Powered Multimodal Cancer Research Platform
        </span>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-balance sm:text-5xl">
            Welcome to <span className="brand-gradient-text">WeCure</span>
          </h1>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-white/75 text-pretty sm:text-lg">
            Explore the potential of Artificial Intelligence in cancer research through intelligent image analysis and multimodal insights.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link
            href="/analysis"
            className="group inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-wc-turquoise to-wc-cyan px-5 text-sm font-semibold text-wc-navy shadow-lg shadow-wc-turquoise/25 transition-transform hover:-translate-y-0.5"
          >
            <ScanSearch className="size-4" aria-hidden />
            Start Image Analysis
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
          </Link>
          <Link
            href="/modules"
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 px-5 text-sm font-semibold backdrop-blur transition-colors hover:bg-white/10"
          >
            <Layers className="size-4" aria-hidden />
            Explore Research Modules
          </Link>
        </div>
        <p className="text-xs font-semibold tracking-[0.2em] text-white/50 uppercase">Explore · Analyze · Advance</p>
      </div>
    </section>
  )
}
