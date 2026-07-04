import Reveal from './Reveal'

export default function CTA() {
  return (
    <section id="cta" className="relative py-28 scroll-mt-16 overflow-hidden">
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 50% 60% at 50% 60%, rgba(108,92,231,0.12), transparent 70%)',
        }}
      />
      <div className="relative max-w-3xl mx-auto px-6 text-center">
        <Reveal>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight">
            Ready to build your company brain?
          </h2>
          <p className="mt-4 text-base text-text-dim">
            Connect your first source in 5 minutes.
          </p>
          <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="mailto:agrawalprashant906@gmail.com?subject=Cortex%20Early%20Access"
              className="w-full sm:w-auto text-sm font-medium bg-primary hover:bg-primary/85 text-white rounded-lg px-8 py-3.5 transition-colors"
            >
              Get Early Access
            </a>
            <a
              href="https://github.com/agrawal-2005/Cortex"
              target="_blank"
              rel="noreferrer"
              className="w-full sm:w-auto text-sm font-medium border border-border hover:border-primary/50 text-text rounded-lg px-8 py-3.5 transition-colors"
            >
              View on GitHub
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
