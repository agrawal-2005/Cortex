import Reveal from './Reveal'

const STATS = [
  { value: '206', label: 'automated tests' },
  { value: '10', label: 'LLM failure modes handled' },
  { value: '32ms', label: 'average query response' },
  { value: '454 → 28', label: 'documents → skills extracted' },
]

export default function Stats() {
  return (
    <section className="py-16 border-y border-border bg-surface/40">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {STATS.map((s, i) => (
            <Reveal key={s.label} delay={i * 0.08}>
              <div className="text-center">
                <p className="text-3xl font-semibold tracking-tight text-text tabular-nums">
                  {s.value}
                </p>
                <p className="mt-1.5 text-sm text-text-dim">{s.label}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
