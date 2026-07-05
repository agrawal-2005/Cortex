import Reveal from './Reveal'
import SkillShowcase from './SkillShowcase'
import { DashboardMock, SourcesMock, QueryMock, ReviewMock, DataOverviewMock } from './AppMockups'

/* All demo frames are live mockups rendered from static data - no screenshots. */
const SHOTS = [
  {
    title: 'Dashboard',
    caption:
      'Stats at a glance: documents ingested, skills extracted, review queue, confidence distribution.',
    component: DashboardMock,
  },
  {
    title: 'Data Sources',
    caption:
      'App grid with live connection status. Connect Slack, GitHub, Discord, or upload files.',
    component: SourcesMock,
  },
  {
    title: 'Skill Detail',
    caption:
      'Every step with tools, edge cases, and links back to the exact source message or PR. This is real output: scroll inside the frame, or flip to Raw JSON.',
    component: SkillShowcase,
  },
  {
    title: 'Query',
    caption:
      'Ask in natural language. Cortex matches the best skill and cites its sources. Chats are stored, and follow-ups stay on topic.',
    component: QueryMock,
  },
  {
    title: 'Review Queue',
    caption: 'Domain experts approve, edit, or reject. Corrections feed back into extraction.',
    component: ReviewMock,
  },
  {
    title: 'Your Data',
    caption:
      'Full transparency: every document Cortex has ingested, per source, with date ranges, sample content, and the skills extracted from it. Nothing beyond this is accessed.',
    component: DataOverviewMock,
  },
]

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
                  <shot.component />
                </div>
                <div className="[direction:ltr]">
                  <h3 className="text-xl sm:text-2xl font-semibold">{shot.title}</h3>
                  <p className="mt-3 text-base text-text-dim leading-relaxed">{shot.caption}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
