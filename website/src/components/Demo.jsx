import Reveal from './Reveal'

const SHOTS = [
  {
    title: 'Dashboard',
    caption: 'Stats at a glance — documents ingested, skills extracted, review queue, confidence distribution.',
  },
  {
    title: 'Data Sources',
    caption: 'App grid with live connection status. Connect Slack, GitHub, Discord, or upload files.',
  },
  {
    title: 'Skill Detail',
    caption: 'Every step with tools, edge cases, and links back to the exact source message or PR.',
  },
  {
    title: 'Query',
    caption: 'Ask in natural language — Cortex matches the best skill and cites its sources.',
  },
  {
    title: 'Review Queue',
    caption: 'Domain experts approve, edit, or reject. Corrections feed back into extraction.',
  },
]

function BrowserFrame({ title }) {
  return (
    <div className="rounded-xl border border-border bg-surface overflow-hidden">
      <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border">
        <span className="w-2.5 h-2.5 rounded-full bg-border" />
        <span className="w-2.5 h-2.5 rounded-full bg-border" />
        <span className="w-2.5 h-2.5 rounded-full bg-border" />
        <span className="ml-3 text-[11px] text-text-dim">{title}</span>
      </div>
      <div className="aspect-[1200/750] flex items-center justify-center bg-bg/60">
        <p className="text-sm text-text-dim">Placeholder — replace with real screenshots</p>
      </div>
    </div>
  )
}

export default function Demo() {
  return (
    <section id="demo" className="py-24 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-center">
            See it in action
          </h2>
        </Reveal>

        <div className="mt-14 space-y-16">
          {SHOTS.map((shot, i) => (
            <Reveal key={shot.title}>
              <div
                className={`grid lg:grid-cols-[minmax(0,3fr)_minmax(0,1fr)] gap-6 items-center ${
                  i % 2 === 1 ? 'lg:[direction:rtl]' : ''
                }`}
              >
                <div className="[direction:ltr]">
                  <BrowserFrame title={shot.title} />
                </div>
                <div className="[direction:ltr]">
                  <h3 className="text-base font-semibold">{shot.title}</h3>
                  <p className="mt-2 text-sm text-text-dim leading-relaxed">{shot.caption}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
