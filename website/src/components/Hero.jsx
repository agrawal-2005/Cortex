import { motion } from 'framer-motion'

export default function Hero() {
  return (
    <section className="relative pt-40 pb-24 overflow-hidden">
      {/* Subtle radial purple glow behind hero text */}
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-[36rem] pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 60% 50% at 50% 20%, rgba(108,92,231,0.14), transparent 70%)',
        }}
      />

      <div className="relative max-w-4xl mx-auto px-6 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className="text-4xl sm:text-5xl md:text-6xl font-semibold tracking-tight leading-[1.1]"
        >
          Extract how your company actually works.
          <span className="block text-primary mt-2">
            Turn it into workflows AI agents can run.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15, ease: 'easeOut' }}
          className="mt-6 text-base sm:text-lg text-text-dim max-w-2xl mx-auto leading-relaxed"
        >
          Cortex reads your Slack, GitHub, and internal tools — finds the
          processes nobody documented — and packages them for AI agents to
          execute.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3, ease: 'easeOut' }}
          className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3"
        >
          <a
            href="#cta"
            className="w-full sm:w-auto text-sm font-medium bg-primary hover:bg-primary/85 text-white rounded-lg px-6 py-3 transition-colors"
          >
            Get Early Access
          </a>
          <a
            href="#how-it-works"
            className="w-full sm:w-auto text-sm font-medium border border-border hover:border-primary/50 text-text rounded-lg px-6 py-3 transition-colors"
          >
            See How It Works
          </a>
        </motion.div>
      </div>

      {/* Floating dashboard screenshot placeholder */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.45, ease: 'easeOut' }}
        className="relative max-w-5xl mx-auto px-6 mt-20"
      >
        <div
          aria-hidden
          className="absolute inset-x-12 -top-8 bottom-0 pointer-events-none"
          style={{
            background:
              'radial-gradient(ellipse 50% 50% at 50% 40%, rgba(108,92,231,0.18), transparent 70%)',
          }}
        />
        <div className="relative rounded-xl border border-border bg-surface overflow-hidden shadow-2xl shadow-primary/10">
          <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border">
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
            <span className="w-2.5 h-2.5 rounded-full bg-border" />
          </div>
          <div className="aspect-[1200/750] flex items-center justify-center bg-bg/60">
            <p className="text-sm text-text-dim">
              Placeholder — replace with real screenshots
            </p>
          </div>
        </div>
      </motion.div>
    </section>
  )
}
