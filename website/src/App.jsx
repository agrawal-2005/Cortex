import Navbar from './components/Navbar'
import Hero from './components/Hero'
import Problem from './components/Problem'
import HowItWorks from './components/HowItWorks'
import Demo from './components/Demo'
import Features from './components/Features'
import SyncLoop from './components/SyncLoop'
import Integrations from './components/Integrations'
import Comparison from './components/Comparison'
import Security from './components/Security'
import Stats from './components/Stats'
import CTA from './components/CTA'
import Footer from './components/Footer'

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <Navbar />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <Demo />
        <Features />
        <SyncLoop />
        <Integrations />
        <Comparison />
        <Security />
        <Stats />
        {/* Pricing lands on the early-access CTA until plans exist */}
        <div id="pricing" className="scroll-mt-16" />
        <CTA />
      </main>
      <Footer />
    </div>
  )
}
