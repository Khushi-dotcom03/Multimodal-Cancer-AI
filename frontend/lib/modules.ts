import type { ModuleAccent, ResearchModule } from '@/types'

export const RESEARCH_MODULES: ResearchModule[] = [
  {
    id: 'skin-cancer',
    name: 'Skin Cancer',
    shortName: 'Skin',
    description: 'AI-assisted skin lesion image analysis and research.',
    status: 'available',
    statusLabel: 'Initial Research Prototype',
    category: 'Dermatology Imaging',
    imaging: 'Dermoscopic images',
    image: '/images/module-skin.png',
    accent: 'teal',
    href: '/analysis',
  },
  {
    id: 'breast-cancer',
    name: 'Breast Cancer',
    shortName: 'Breast',
    description: 'Future research module for breast imaging and multimodal analysis.',
    status: 'coming-soon',
    statusLabel: 'Coming Soon',
    category: 'Radiology Imaging',
    imaging: 'Mammography & ultrasound',
    image: '/images/module-breast.png',
    accent: 'pink',
    href: '/modules',
  },
  {
    id: 'lung-cancer',
    name: 'Lung Cancer',
    shortName: 'Lung',
    description: 'Future research module for lung imaging and AI-based research.',
    status: 'coming-soon',
    statusLabel: 'Coming Soon',
    category: 'Radiology Imaging',
    imaging: 'CT & chest X-ray',
    image: '/images/module-lung.png',
    accent: 'blue',
    href: '/modules',
  },
  {
    id: 'brain-tumour',
    name: 'Brain Tumour',
    shortName: 'Brain',
    description: 'Future research module for brain imaging and tumour-related research.',
    status: 'coming-soon',
    statusLabel: 'Coming Soon',
    category: 'Neuro Imaging',
    imaging: 'MRI',
    image: '/images/module-brain.png',
    accent: 'violet',
    href: '/modules',
  },
]

export const MODULE_CATEGORIES = Array.from(new Set(RESEARCH_MODULES.map((m) => m.category)))

export function getModule(id: string) {
  return RESEARCH_MODULES.find((m) => m.id === id)
}

export const ACCENT_STYLES: Record<ModuleAccent, { text: string; bg: string; ring: string; dot: string }> = {
  teal: { text: 'text-wc-teal dark:text-wc-turquoise', bg: 'bg-wc-turquoise/10', ring: 'ring-wc-turquoise/30', dot: 'bg-wc-turquoise' },
  pink: { text: 'text-wc-pink', bg: 'bg-wc-pink/10', ring: 'ring-wc-pink/30', dot: 'bg-wc-pink' },
  blue: { text: 'text-wc-blue', bg: 'bg-wc-blue/10', ring: 'ring-wc-blue/30', dot: 'bg-wc-blue' },
  violet: { text: 'text-wc-violet', bg: 'bg-wc-violet/10', ring: 'ring-wc-violet/30', dot: 'bg-wc-violet' },
}
