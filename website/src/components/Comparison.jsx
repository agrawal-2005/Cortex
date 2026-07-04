import Reveal from './Reveal'

const ROWS = [
  ['Output', 'Text paragraphs', 'Documents + AI answers', 'Executable JSON'],
  ['Consumer', 'Humans only', 'Humans only', 'Humans + AI agents'],
  ['Knowledge source', 'Only documented', 'Searches all tools', 'Synthesizes from fragments'],
  ['Learns from corrections', 'No', 'Basic', 'Structural feedback loop'],
  ['Undocumented processes', 'Invisible', "Can't extract", 'Extracts from behavior'],
]

export default function Comparison() {
  return (
    <section className="py-24">
      <div className="max-w-5xl mx-auto px-6">
        <Reveal>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-center">
            Not another search tool
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-12 overflow-x-auto rounded-xl border border-border">
            <table className="w-full min-w-[36rem] text-sm border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left font-medium text-text-dim px-5 py-4">Feature</th>
                  <th className="text-left font-medium text-text-dim px-5 py-4">Wiki / Chatbot</th>
                  <th className="text-left font-medium text-text-dim px-5 py-4">Glean</th>
                  <th className="text-left font-medium px-5 py-4 bg-primary/[0.07] border-l border-primary/20">
                    <span className="text-text" style={{ letterSpacing: '-0.5px' }}>
                      corte<span className="text-primary">x</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {ROWS.map(([feature, wiki, glean, cortex]) => (
                  <tr key={feature} className="border-b border-border last:border-b-0">
                    <td className="px-5 py-4 font-medium">{feature}</td>
                    <td className="px-5 py-4 text-text-dim">{wiki}</td>
                    <td className="px-5 py-4 text-text-dim">{glean}</td>
                    <td className="px-5 py-4 text-text font-medium bg-primary/[0.07] border-l border-primary/20">
                      {cortex}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
