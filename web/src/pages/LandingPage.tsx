import { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, ShieldCheck, Cpu, Database, Play, Menu, X } from 'lucide-react';
import HolographicCore from '../components/HolographicCore';
import CinematicEffects from '../components/CinematicEffects';
import LiveTelemetry from '../components/LiveTelemetry';
import AutomationModules from '../components/AutomationModules';
import AlertIntelligence from '../components/AlertIntelligence';
import AssetMonitoring from '../components/AssetMonitoring';
import SystemArchitecture from '../components/SystemArchitecture';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Animation generators for precise timeline
  const fadeUp = (delay: number) => ({
    hidden: { opacity: 0, y: 30 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.8, delay, ease: "easeOut" as any }
    }
  });

  const slideRight = (delay: number) => ({
    hidden: { opacity: 0, x: -30 },
    visible: { 
      opacity: 1, 
      x: 0,
      transition: { duration: 0.8, delay, ease: "easeOut" as any }
    }
  });

  const fade = (delay: number) => ({
    hidden: { opacity: 0 },
    visible: { 
      opacity: 1, 
      transition: { duration: 1.2, delay, ease: "easeInOut" as any }
    }
  });

  const fadeScale = (delay: number) => ({
    hidden: { opacity: 0, scale: 0.95 },
    visible: { 
      opacity: 1, 
      scale: 1,
      transition: { duration: 1.2, delay, ease: "easeOut" as any }
    }
  });

  const rootVariant = { hidden: {}, visible: {} };

  return (
    <div ref={containerRef} className="relative min-h-screen bg-[var(--color-io-navy-dark)] text-white overflow-x-hidden font-sans">
      <CinematicEffects />
      
      {/* Top Navigation */}
      <motion.nav 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.5 }}
        className="fixed top-0 left-0 right-0 z-[100] border-b border-gray-800/50 bg-[#020408]/80 backdrop-blur-md px-6 lg:px-16 py-4 flex justify-between items-center"
      >
        <div className="font-bold text-[var(--color-io-orange)] tracking-widest text-sm flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[var(--color-io-orange)] animate-pulse" />
          INDIANOIL | SENTINEL
        </div>
        <ul className="hidden md:flex gap-8 font-mono text-[10px] font-bold tracking-[0.2em] uppercase">
          <li><a href="#overview" className="text-gray-400 hover:text-white transition-colors">Overview</a></li>
          <li><a href="#telemetry" className="text-gray-400 hover:text-[var(--color-telemetry-green)] transition-colors">Telemetry</a></li>
          <li><a href="#automation" className="text-gray-400 hover:text-[var(--color-io-orange)] transition-colors">Automation</a></li>
          <li><a href="#assets" className="text-gray-400 hover:text-[var(--color-io-blue-light)] transition-colors">Assets</a></li>
          <li><a href="#anomalies" className="text-gray-400 hover:text-red-500 transition-colors">Anomalies</a></li>
        </ul>
        <button 
          className="md:hidden text-[var(--color-io-orange)]"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </motion.nav>

      {/* Mobile Menu Dropdown */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-[60px] left-0 right-0 bg-[#020408]/95 backdrop-blur-xl border-b border-gray-800 z-[90] p-6 md:hidden"
          >
            <ul className="flex flex-col gap-6 font-mono text-sm font-bold tracking-[0.2em] uppercase">
              <li><a href="#overview" onClick={() => setMobileMenuOpen(false)} className="text-gray-400 hover:text-white transition-colors block">Overview</a></li>
              <li><a href="#telemetry" onClick={() => setMobileMenuOpen(false)} className="text-gray-400 hover:text-[var(--color-telemetry-green)] transition-colors block">Telemetry</a></li>
              <li><a href="#automation" onClick={() => setMobileMenuOpen(false)} className="text-gray-400 hover:text-[var(--color-io-orange)] transition-colors block">Automation</a></li>
              <li><a href="#assets" onClick={() => setMobileMenuOpen(false)} className="text-gray-400 hover:text-[var(--color-io-blue-light)] transition-colors block">Assets</a></li>
              <li><a href="#anomalies" onClick={() => setMobileMenuOpen(false)} className="text-gray-400 hover:text-red-500 transition-colors block">Anomalies</a></li>
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Background radial glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute top-1/4 left-1/4 w-[40vw] h-[40vw] rounded-full bg-[var(--color-io-blue)]/5 blur-[120px] mix-blend-screen" />
        <div className="absolute bottom-1/4 right-1/4 w-[30vw] h-[30vw] rounded-full bg-[var(--color-io-orange)]/5 blur-[120px] mix-blend-screen" />
      </div>

      {/* Abstract Background Elements (Delay 2.0s) */}
      <motion.div 
        variants={fade(2.0)}
        initial="hidden" animate="visible"
        className="absolute inset-0 overflow-hidden pointer-events-none z-0"
      >
        <motion.div 
          animate={{ opacity: [0.3, 0.5, 0.3], scale: [1, 1.05, 1] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
          className="absolute -top-[20%] -left-[10%] w-[50vw] h-[50vw] rounded-full bg-[var(--color-io-blue-light)]/10 blur-[150px]" 
        />
        <motion.div 
          animate={{ opacity: [0.1, 0.3, 0.1], scale: [1, 1.2, 1] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut", delay: 2 }}
          className="absolute top-[20%] -right-[10%] w-[40vw] h-[40vw] rounded-full bg-[var(--color-io-orange)]/5 blur-[120px]" 
        />
        
        {/* Perspective Digital Grid Floor */}
        <div className="absolute bottom-0 left-0 right-0 h-[45vh] overflow-hidden pointer-events-none z-0">
          <div className="absolute inset-[-50%] bg-floor-grid opacity-15 md:opacity-40 shadow-[0_0_15px_rgba(200,107,60,0.1)]" />
          
          {/* Subtle animated floor reflection */}
          <motion.div 
            animate={{ x: ['-100%', '100%'] }}
            transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
            className="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--color-io-orange)]/5 to-transparent skew-x-12 mix-blend-screen opacity-50"
          />

          <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-io-navy-dark)] via-[var(--color-io-navy-dark)]/90 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-io-navy-dark)] via-transparent to-[var(--color-io-navy-dark)]" />
        </div>
        </motion.div>

      <main id="overview" className="relative z-10 flex-grow flex flex-col lg:flex-row min-h-screen w-full max-w-[1800px] mx-auto px-6 pt-24 pb-8 lg:px-16 lg:pt-28 lg:pb-12">
        
        {/* LEFT SIDE - Content */}
        <motion.div 
          variants={rootVariant}
          initial="hidden"
          animate="visible"
          className="w-full lg:w-5/12 flex flex-col justify-center h-full min-h-[calc(100vh-6rem)] z-20 pt-8 lg:pt-0"
        >
          {/* IndianOil Branding (0.2s) */}
          <motion.div variants={fadeUp(0.2)} className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(243,112,33,0.3)] bg-white p-1.5">
               <img src="/iocl-logo.svg" alt="IndianOil Logo" className="w-full h-full object-contain drop-shadow-sm" />
            </div>
            <div className="h-6 w-[1px] bg-gray-600/50" />
            <span className="font-mono text-sm tracking-widest text-gray-400 uppercase">INDIANOIL | SENTINEL-RO</span>
          </motion.div>
          
          <motion.div variants={fadeUp(0.2)} className="mb-10 text-gray-400 text-sm tracking-widest font-mono">
            ENTERPRISE IoT & AUTOMATION ANALYTICS
          </motion.div>

          {/* Technical Label (0.4s slide right) */}
          <motion.div variants={slideRight(0.4)} className="mb-6">
            <span className="font-mono text-xs font-bold tracking-widest text-[var(--color-telemetry-green)] border border-[var(--color-telemetry-green)]/30 bg-[var(--color-telemetry-green)]/10 px-3 py-1.5 flex inline-flex items-center gap-2 shadow-[0_0_10px_rgba(0,255,102,0.1)]">
              <Activity className="w-3 h-3" /> IOCL PIPELINE & RO ASSET MONITORING Â· 2026
            </span>
          </motion.div>

          {/* Hero Title (0.6s) */}
          <motion.h1 variants={fadeUp(0.6)} className="text-6xl lg:text-[6.5rem] font-bold tracking-tighter text-white mb-8 leading-[0.9]">
            Sentinel<br/>
            <span className="text-[var(--color-io-orange)] block mt-4 font-mono tracking-[0.2em] text-3xl lg:text-5xl text-shadow-md">RO CORE</span>
          </motion.h1>

          {/* Description (0.8s) */}
          <motion.p variants={fadeUp(0.8)} className="text-gray-300 text-lg leading-relaxed max-w-lg mb-6 font-sans border-l border-gray-700 pl-4">
            Industrial-grade predictive health monitoring, real-time telemetry ingestion, and automated situational intelligence for IndianOil fleet RO assets.
          </motion.p>
          
          <motion.p variants={fadeUp(0.8)} className="text-gray-400 text-base leading-relaxed max-w-lg mb-10 font-sans border-l-2 border-[var(--color-io-orange)] pl-4 italic">
            Zero downtime through TimescaleDB time-series intelligence.
          </motion.p>

          {/* Metric Boxes (1.0s) */}
          <motion.div variants={fadeUp(1.0)} className="grid grid-cols-3 gap-4 mb-12 max-w-lg">
            {[
              { icon: ShieldCheck, label: 'MQTT', value: '1863', color: 'var(--color-telemetry-green)' },
              { icon: Database, label: 'TIMESCALE', value: '5432', color: 'var(--color-io-orange)' },
              { icon: Cpu, label: 'GRAFANA', value: '3000', color: 'var(--color-io-blue-light)' },
            ].map((metric, i) => (
              <motion.div 
                key={i} 
                whileHover={{ y: -5, boxShadow: `0 10px 20px -10px ${metric.color}` }}
                className="glass-panel p-4 group transition-all duration-300"
              >
                <div className="absolute top-0 left-0 w-full h-[2px] opacity-70 group-hover:opacity-100 transition-opacity" style={{ backgroundColor: metric.color }} />
                <metric.icon className="w-5 h-5 mb-3 opacity-70" style={{ color: metric.color }} />
                <div className="font-mono text-[10px] text-gray-500 uppercase tracking-wider mb-1">{metric.label}</div>
                <div className="font-mono text-sm md:text-base font-bold text-white">{metric.value}</div>
              </motion.div>
            ))}
          </motion.div>

          {/* CTAs (1.2s) */}
          <motion.div variants={fadeUp(1.2)} className="flex flex-wrap items-center gap-6">
            <Link to="/dashboard">
              <motion.div 
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="bg-[var(--color-io-orange)] text-white px-8 py-4 font-mono text-sm uppercase tracking-[0.2em] flex items-center gap-3 relative overflow-hidden group shadow-none transition-shadow"
                style={{ clipPath: 'polygon(15px 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%, 0 15px)' }}
              >
                <div className="absolute inset-0 bg-white/20 translate-y-[100%] group-hover:translate-y-0 transition-transform duration-300" />
                <span className="relative z-10 font-bold text-black group-hover:text-white transition-colors">LAUNCH DASHBOARD &rarr;</span>
              </motion.div>
            </Link>

            <motion.a 
              href="#telemetry"
              whileHover={{ scale: 1.05, color: '#fff' }}
              whileTap={{ scale: 0.95 }}
              className="text-gray-300 px-6 py-4 font-mono text-sm uppercase tracking-wider flex items-center gap-3 hover:text-white transition-colors group"
            >
              <div className="w-10 h-10 rounded-full border border-[var(--color-io-blue-light)] flex items-center justify-center group-hover:bg-[var(--color-io-blue-light)]/20 transition-colors shadow-[0_0_10px_rgba(0,71,155,0.2)]">
                <Play className="w-3 h-3 ml-1 text-[var(--color-io-blue-light)] group-hover:text-[var(--color-io-orange)] transition-colors" />
              </div>
              <span className="group-hover:text-[var(--color-io-blue-light)] transition-colors">VIEW TELEMETRY</span>
            </motion.a>
          </motion.div>
        </motion.div>

        {/* RIGHT SIDE - Holographic Visualization (1.0s) */}
        <motion.div 
          variants={fadeScale(1.0)}
          initial="hidden"
          animate="visible"
          className="w-full lg:w-7/12 relative flex items-center justify-center min-h-[50vh] lg:min-h-full mt-12 lg:mt-0 z-10"
        >
          <HolographicCore />
        </motion.div>
      </main>

      {/* HUD Telemetry Labels (1.5s) */}
      
      {/* Top Right */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 1.2, delay: 1.5, ease: "easeOut" }}
        className="absolute top-8 right-8 lg:right-16 z-30 font-mono text-[10px] text-gray-500 tracking-[0.2em] uppercase hidden md:flex items-center gap-2"
      >
        <span>PIPELINE :</span>
        <motion.span 
          animate={{ opacity: [1, 0.5, 1] }} 
          transition={{ duration: 2, repeat: Infinity }}
          className="text-[var(--color-telemetry-green)] font-bold"
        >
          LIVE (200 OK)
        </motion.span>
      </motion.div>

      {/* Left Vertical */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 1.2, delay: 1.5, ease: "easeOut" }}
        className="absolute top-1/2 left-8 z-30 font-mono text-[10px] text-gray-500 tracking-[0.2em] uppercase hidden xl:flex items-center gap-2"
        style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg) translateY(50%)' }}
      >
        <span>SYSTEM LATENCY :</span>
        <span className="text-[var(--color-telemetry-green)] font-bold">42ms</span>
      </motion.div>

      {/* Right Vertical */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 1.2, delay: 1.5, ease: "easeOut" }}
        className="absolute top-1/2 right-8 z-30 font-mono text-[10px] text-gray-500 tracking-[0.2em] uppercase hidden xl:flex items-center gap-2"
        style={{ writingMode: 'vertical-rl', transform: 'translateY(-50%)' }}
      >
        <span>NODE HEALTH :</span>
        <span className="text-[var(--color-telemetry-green)] font-bold">98.7%</span>
      </motion.div>

      {/* Bottom Left & Right */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1.2, delay: 1.5, ease: "easeOut" }}
        className="absolute bottom-6 left-0 right-0 z-30 flex justify-between px-8 lg:px-16 font-mono text-[10px] text-gray-500 tracking-[0.2em] uppercase hidden md:flex"
      >
        <div className="flex items-center gap-2">
          <span>KAFKA CLUSTER :</span>
          <span className="text-[var(--color-io-orange)] font-bold">9082</span>
        </div>
        
        <div className="flex items-center gap-2">
          <motion.div 
            animate={{ rotate: 360 }} 
            transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
            className="w-3 h-3 border border-dashed border-[var(--color-io-orange)] rounded-full mr-1 opacity-70"
          />
          <span>ACTIVE RO TELEMETRY STREAMS :</span>
          <span className="text-[var(--color-io-orange)] font-bold text-glow">10,608+</span>
        </div>
      </motion.div>
      
      <LiveTelemetry />
      <AutomationModules />
      <AlertIntelligence />
      <AssetMonitoring />
      <SystemArchitecture />
    </div>
  );
}
