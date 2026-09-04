import { motion } from 'framer-motion';
import { Settings, Search, GitBranch, Cpu, Activity } from 'lucide-react';

const modules = [
  {
    id: '01',
    title: 'RAG REPAIR MANUALS',
    description: 'AI-powered context retrieval from OEM PDF manuals for instant technician guidance.',
    icon: Settings,
    status: 'ACTIVE',
    statusColor: 'var(--color-telemetry-green)'
  },
  {
    id: '02',
    title: 'AUTOMATED TRIAGE',
    description: 'Real-time telemetry correlation that detects anomalies and dispatches Jira tickets instantly.',
    icon: Search,
    status: 'ACTIVE',
    statusColor: 'var(--color-telemetry-green)'
  },
  {
    id: '03',
    title: 'PREDICTIVE MAINTENANCE',
    description: 'Time-series forecasting models predicting asset degradation before operational failure.',
    icon: GitBranch,
    status: 'ACTIVE',
    statusColor: 'var(--color-telemetry-green)'
  },
  {
    id: '04',
    title: 'AUTOMATED LOGISTICS',
    description: 'Zero-touch supply chain integration that orders spare parts autonomously when failure risk peaks.',
    icon: Cpu,
    status: 'ACTIVE',
    statusColor: 'var(--color-telemetry-green)'
  }
];

export default function AutomationModules() {
  return (
    <section id="automation" className="relative w-full max-w-[1800px] mx-auto px-6 py-20 lg:px-16 z-10">
      
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, x: -30 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.8 }}
        className="mb-12 flex flex-col md:flex-row md:items-end justify-between border-b border-gray-800 pb-4"
      >
        <div>
          <div className="font-mono text-[10px] text-[var(--color-io-orange)] tracking-[0.3em] mb-2 uppercase flex items-center gap-2">
            <Activity className="w-3 h-3" /> System Intelligence
          </div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-widest text-white font-mono uppercase">
            Automation Modules
          </h2>
        </div>
        <div className="font-mono text-xs text-gray-500 tracking-widest mt-4 md:mt-0 uppercase">
          CORE LOGIC <span className="text-[var(--color-telemetry-green)]">ONLINE</span>
        </div>
      </motion.div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {modules.map((mod, i) => (
          <motion.div
            key={mod.id}
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6, delay: i * 0.1 }}
            whileHover={{ y: -8 }}
            className="group relative bg-[#020408]/60 backdrop-blur-sm border border-gray-800 hover:border-[var(--color-io-orange)]/60 p-6 flex flex-col justify-between min-h-[280px] transition-colors duration-300 shadow-none hover:shadow-[0_0_30px_rgba(243,112,33,0.15)] rounded-none"
          >
            {/* HUD Corner Accents */}
            <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-gray-600 group-hover:border-[var(--color-io-orange)] transition-colors duration-300" />
            <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-gray-600 group-hover:border-[var(--color-io-orange)] transition-colors duration-300" />
            <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-gray-600 group-hover:border-[var(--color-io-orange)] transition-colors duration-300" />
            <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-gray-600 group-hover:border-[var(--color-io-orange)] transition-colors duration-300" />

            {/* Top Bar: Number & Animation */}
            <div className="flex justify-between items-start mb-8">
              <div className="font-mono text-3xl font-bold text-gray-800 group-hover:text-[var(--color-io-orange)]/30 transition-colors duration-300">
                {mod.id}
              </div>
              
              {/* Telemetry Animation */}
              <div className="flex items-end gap-[2px] h-4">
                {[0, 1, 2].map((bar) => (
                  <motion.div 
                    key={bar}
                    className="w-1 bg-[var(--color-io-blue-light)]/50 group-hover:bg-[var(--color-io-orange)] group-hover:shadow-[0_0_8px_var(--color-io-orange)] transition-colors duration-300"
                    animate={{ height: ['4px', '16px', '4px'] }}
                    transition={{ 
                      duration: 1.5, 
                      repeat: Infinity, 
                      delay: bar * 0.2,
                      ease: 'easeInOut' 
                    }}
                    style={{ transformOrigin: 'bottom' }}
                  />
                ))}
              </div>
            </div>

            {/* Content */}
            <div className="mb-6 flex-grow">
              <div className="flex items-center gap-3 mb-3">
                <mod.icon className="w-5 h-5 text-gray-500 group-hover:text-[var(--color-io-orange)] transition-colors duration-300" />
                <h3 className="font-mono text-sm font-bold text-gray-300 tracking-wider group-hover:text-white transition-colors duration-300">
                  {mod.title}
                </h3>
              </div>
              <p className="text-gray-400 font-sans text-sm leading-relaxed mb-12">
                {mod.description}
              </p>
            </div>

            {/* Footer Status */}
            <div className="flex justify-between items-center pt-4 border-t border-gray-800 group-hover:border-[var(--color-io-orange)]/30 transition-colors duration-300">
              <div className="font-mono text-[10px] tracking-widest text-gray-600 uppercase group-hover:text-gray-400">
                Module Status
              </div>
              <div className="flex items-center gap-2 font-mono text-xs font-bold tracking-widest uppercase">
                <div 
                  className="w-1.5 h-1.5 rounded-full shadow-[0_0_5px_currentColor]"
                  style={{ color: mod.statusColor, backgroundColor: mod.statusColor }} 
                />
                <span style={{ color: mod.statusColor }}>{mod.status}</span>
              </div>
            </div>

            {/* Background Glow Overlay */}
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(243,112,33,0.05)_0%,transparent_70%)] opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
          </motion.div>
        ))}
      </div>
    </section>
  );
}
