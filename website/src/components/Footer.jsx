import Logo from './Logo'
import Wordmark from './Wordmark'

function GitHubIcon({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.55 0-.27-.01-1.17-.02-2.12-3.2.7-3.87-1.36-3.87-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.19 1.76 1.19 1.03 1.75 2.69 1.25 3.34.95.1-.74.4-1.25.72-1.53-2.55-.29-5.23-1.28-5.23-5.68 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11.04 11.04 0 015.78 0c2.2-1.49 3.16-1.18 3.16-1.18.63 1.59.23 2.76.12 3.05.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.39-5.25 5.67.41.35.77 1.05.77 2.12 0 1.53-.01 2.76-.01 3.14 0 .3.2.66.8.55A11.5 11.5 0 0023.5 12C23.5 5.65 18.35.5 12 .5z" />
    </svg>
  )
}

function LinkedInIcon({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden>
      <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.03-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.47-.9 1.63-1.85 3.36-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 110-4.12 2.06 2.06 0 010 4.12zM7.12 20.45H3.56V9h3.56v11.45z" />
    </svg>
  )
}

function MailIcon({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </svg>
  )
}

const SOCIALS = [
  { href: 'https://linkedin.com/in/pr-shant26', label: 'LinkedIn', Icon: LinkedInIcon },
  { href: 'https://github.com/agrawal-2005', label: 'GitHub', Icon: GitHubIcon },
  { href: 'mailto:agrawalprashant906@gmail.com', label: 'Email', Icon: MailIcon },
]

export default function Footer() {
  return (
    <footer className="border-t border-border py-12">
      <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2.5">
          <Logo size={26} />
          <Wordmark size={20} />
        </div>

        <div className="flex items-center gap-6 text-sm text-text-dim">
          <a
            href="https://github.com/agrawal-2005/Cortex"
            target="_blank"
            rel="noreferrer"
            className="hover:text-text transition-colors"
          >
            GitHub
          </a>
          <a
            href="https://github.com/agrawal-2005/Cortex#readme"
            target="_blank"
            rel="noreferrer"
            className="hover:text-text transition-colors"
          >
            Documentation
          </a>
          <a
            href="mailto:agrawalprashant906@gmail.com"
            className="hover:text-text transition-colors"
          >
            Contact
          </a>
        </div>

        <div className="flex flex-col items-center sm:items-end gap-3">
          <div className="flex items-center gap-3">
            {SOCIALS.map(({ href, label, Icon }) => (
              <a
                key={label}
                href={href}
                target={href.startsWith('mailto:') ? undefined : '_blank'}
                rel="noreferrer"
                title={label}
                aria-label={label}
                className="w-8 h-8 rounded-lg border border-border bg-surface flex items-center justify-center text-text-dim hover:text-text hover:border-primary/40 transition-colors"
              >
                <Icon size={15} />
              </a>
            ))}
          </div>
          <div className="text-xs text-text-dim text-center sm:text-right">
            <p>
              Built by{' '}
              <a
                href="https://linkedin.com/in/pr-shant26"
                target="_blank"
                rel="noreferrer"
                className="text-text hover:text-primary transition-colors"
              >
                Prashant Agrawal
              </a>
            </p>
            <p className="mt-1">© 2026 cortex</p>
          </div>
        </div>
      </div>
    </footer>
  )
}
