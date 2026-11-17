import {
  BarChart3,
  BookOpen,
  FileText,
  Info,
  LayoutDashboard,
  Layers,
  ScanSearch,
  Settings,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  description: string
}

export const MAIN_NAV: NavItem[] = [
  { label: 'Overview', href: '/', icon: LayoutDashboard, description: 'Home dashboard and quick actions' },
  { label: 'Cancer Research Modules', href: '/modules', icon: Layers, description: 'Browse all research modules' },
  { label: 'Image Analysis', href: '/analysis', icon: ScanSearch, description: 'Skin cancer image analysis workspace' },
  { label: 'Research Dashboard', href: '/dashboard', icon: BarChart3, description: 'Model evaluation and analytics' },
  { label: 'Reports', href: '/reports', icon: FileText, description: 'Research report management' },
  { label: 'Research Library', href: '/library', icon: BookOpen, description: 'Articles, publications and resources' },
  { label: 'About WeCure', href: '/about', icon: Info, description: 'Mission, objectives and team' },
]

export const SECONDARY_NAV: NavItem[] = [
  { label: 'Settings', href: '/settings', icon: Settings, description: 'Profile, theme and preferences' },
]

export function isActivePath(pathname: string, href: string) {
  if (href === '/') return pathname === '/'
  return pathname === href || pathname.startsWith(`${href}/`)
}
