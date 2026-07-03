import { useState } from 'react'
import {
  MessageSquare, GitBranch, FileText, Database, Plug, Mail,
  MessagesSquare, BookOpen, FileUp, ListTodo, HelpCircle,
} from 'lucide-react'

// Slack was removed from simple-icons (CDN 404s), so its mark is inlined.
function SlackMark({ size, className }) {
  return (
    <svg viewBox="0 0 122.8 122.8" width={size} height={size} className={className} aria-label="slack logo">
      <path d="M25.8 77.6c0 7.1-5.8 12.9-12.9 12.9S0 84.7 0 77.6s5.8-12.9 12.9-12.9h12.9v12.9zM32.3 77.6c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9v32.3c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V77.6z" fill="#E01E5A" />
      <path d="M45.2 25.8c-7.1 0-12.9-5.8-12.9-12.9S38.1 0 45.2 0s12.9 5.8 12.9 12.9v12.9H45.2zM45.2 32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H12.9C5.8 58.1 0 52.3 0 45.2s5.8-12.9 12.9-12.9h32.3z" fill="#36C5F0" />
      <path d="M97 45.2c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9-5.8 12.9-12.9 12.9H97V45.2zM90.5 45.2c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V12.9C64.7 5.8 70.5 0 77.6 0s12.9 5.8 12.9 12.9v32.3z" fill="#2EB67D" />
      <path d="M77.6 97c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9-12.9-5.8-12.9-12.9V97h12.9zM77.6 90.5c-7.1 0-12.9-5.8-12.9-12.9s5.8-12.9 12.9-12.9h32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H77.6z" fill="#ECB22E" />
    </svg>
  )
}

// Brand slugs + colors on cdn.simpleicons.org; lucide fallback if the CDN
// is unreachable (offline demo) or the slug is missing.
const BRANDS = {
  slack: { slug: null, inline: SlackMark, fallback: MessageSquare },
  github: { slug: 'github', color: 'E8E8ED', fallback: GitBranch },
  discord: { slug: 'discord', color: '5865F2', fallback: MessagesSquare },
  jira: { slug: 'jira', color: '0052CC', fallback: ListTodo },
  notion: { slug: 'notion', color: 'E8E8ED', fallback: BookOpen },
  confluence: { slug: 'confluence', color: '172B4D', fallback: BookOpen },
  gmail: { slug: 'gmail', color: 'EA4335', fallback: Mail },
  teams: { slug: null, color: null, fallback: MessagesSquare },
  linear: { slug: 'linear', color: '5E6AD2', fallback: ListTodo },
  api: { slug: null, fallback: Plug },
  file: { slug: null, fallback: FileUp },
  database: { slug: null, fallback: Database },
}

// Map Document.source_type values to brand keys.
const SOURCE_TYPE_MAP = {
  slack: 'slack',
  github_issue: 'github',
  github_pr: 'github',
  github_doc: 'github',
  github_discussion: 'github',
  discord: 'discord',
  jira: 'jira',
  notion: 'notion',
}

export default function SourceIcon({ name, size = 20, className = '' }) {
  const [failed, setFailed] = useState(false)
  const key = BRANDS[name] ? name : SOURCE_TYPE_MAP[name]
  const brand = BRANDS[key]

  if (!brand) {
    return <FileText size={size} className={`text-text-dim ${className}`} />
  }
  if (brand.inline) {
    const Inline = brand.inline
    return <Inline size={size} className={className} />
  }
  const Fallback = brand.fallback || HelpCircle
  if (!brand.slug || failed) {
    return <Fallback size={size} className={`text-text-dim ${className}`} />
  }
  return (
    <img
      src={`https://cdn.simpleicons.org/${brand.slug}/${brand.color}`}
      alt={`${key} logo`}
      width={size}
      height={size}
      className={className}
      onError={() => setFailed(true)}
      loading="lazy"
    />
  )
}
