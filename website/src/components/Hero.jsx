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
          The AI that knows how your company{' '}
          <span className="text-primary">actually works</span>.
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15, ease: 'easeOut' }}
          className="mt-6 text-base sm:text-lg text-text-dim max-w-2xl mx-auto leading-relaxed"
        >
          Cortex turns your team&apos;s knowledge into workflows your agents
          can run.
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

    </section>
  )
}
