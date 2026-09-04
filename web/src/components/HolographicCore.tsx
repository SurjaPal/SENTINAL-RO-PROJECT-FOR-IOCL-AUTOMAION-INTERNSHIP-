import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, Hexagon, Cpu, CheckCircle2 } from 'lucide-react';

const MODULES = [
  'MODULE 1: MANUALS',
  'MODULE 2: TRIAGE',
  'MODULE 3: MAINTENANCE',
  'MODULE 4: LOGISTICS'
];

export default function HolographicCore() {
  const [activeModule, setActiveModule] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveModule((prev) => (prev + 1) % MODULES.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative w-full h-full min-h-[400px] flex items-center justify-center perspective-[1500px]">
      
      {/* Module Navigation */}
      <div className="absolute -top-4 left-0 w-full flex justify-center gap-8 z-40 p-4">
        {MODULES.map((mod, idx) => {
          const isActive = activeModule === idx;
          return (
            <div 
              key={mod}
              className="relative cursor-pointer flex flex-col items-center group"
              onClick={() => setActiveModule(idx)}
            >
              <span className={`font-mono text-xs font-bold tracking-widest mb-2 transition-colors duration-500 ${isActive ? 'text-[var(--color-io-orange)]' : 'text-gray-600 group-hover:text-gray-400'}`} style={isActive ? { textShadow: '0 0 10px rgba(243, 112, 33, 0.5)' } : {}}>
                {mod}
              </span>
              {isActive && (
                <motion.div 
                  layoutId="module-indicator"
                  className="absolute bottom-0 w-full h-[2px] bg-[var(--color-io-orange)] shadow-[0_0_10px_var(--color-io-orange)]"
                  initial={false}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Container that floats up and down */}
      <motion.div
        animate={{ y: [-15, 15, -15] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
        className="relative w-full max-w-[500px] aspect-square flex items-center justify-center transform-style-3d z-10"
      >
        
        {/* Glowing Aura (Cyan/Orange/Green mix) */}
        <div className="absolute inset-0 rounded-full bg-[var(--color-io-blue-light)]/20 blur-[80px] pointer-events-none" />
        <div className="absolute top-1/4 left-1/4 w-1/2 h-1/2 rounded-full bg-[var(--color-telemetry-green)]/10 blur-[60px] pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-1/2 h-1/2 rounded-full bg-[var(--color-io-orange)]/10 blur-[60px] pointer-events-none" />

        {/* SVG Technical Curves (2D Overlay overlaying the 3D scene) */}
        <div className="absolute inset-[-20%] pointer-events-none z-20">
          <svg className="w-full h-full" viewBox="0 0 500 500" fill="none">
            <motion.path 
              d="M 50 250 Q 150 100 250 250 T 450 250" 
              stroke="var(--color-io-blue-light)" 
              strokeWidth="2" 
              strokeDasharray="8 8"
              animate={{ strokeDashoffset: [0, -100] }}
              transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
              className="opacity-50"
            />
            <motion.path 
              d="M 50 280 Q 150 430 250 280 T 450 280" 
              stroke="var(--color-io-orange)" 
              strokeWidth="1.5"
              strokeDasharray="15 15"
              animate={{ strokeDashoffset: [100, 0] }}
              transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
              className="opacity-60"
            />
            <motion.path 
              d="M 250 50 L 250 450" 
              stroke="var(--color-telemetry-green)" 
              strokeWidth="1"
              strokeDasharray="4 8"
              animate={{ strokeDashoffset: [0, 50] }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              className="opacity-30"
            />
          </svg>
        </div>

        {/* 3D Rotated Base */}
        <motion.div 
          className="relative w-[90%] h-[90%] flex items-center justify-center transform-style-3d"
          style={{ rotateX: 65, rotateZ: -10 }}
        >
          
          {/* Ring 1 - Outer Blue Dashed */}
          <motion.div 
            animate={{ rotateZ: 360 }}
            transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
            className="absolute w-full h-full rounded-full border-2 border-[var(--color-io-blue-light)]/30"
            style={{ borderStyle: 'dashed', transformStyle: 'preserve-3d' }}
          >
             <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-[var(--color-io-blue-light)] rounded-full shadow-[0_0_15px_var(--color-io-blue-light)]" style={{ transform: 'rotateX(-65deg)' }} />
          </motion.div>

          {/* Ring 2 - Middle Orange Dotted */}
          <motion.div 
            animate={{ rotateZ: -360 }}
            transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
            className="absolute w-[75%] h-[75%] rounded-full border-[3px] border-[var(--color-io-orange)]/40"
            style={{ borderStyle: 'dotted', transformStyle: 'preserve-3d' }}
          >
             <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-4 h-4 bg-[var(--color-io-orange)] rounded-full shadow-[0_0_20px_var(--color-io-orange)] flex items-center justify-center" style={{ transform: 'rotateX(-65deg)' }}>
               <div className="w-1 h-1 bg-white rounded-full animate-ping" />
             </div>
          </motion.div>

          {/* Ring 3 - Inner Green Double */}
          <motion.div 
            animate={{ rotateZ: 360 }}
            transition={{ duration: 12, repeat: Infinity, ease: "linear" }}
            className="absolute w-[55%] h-[55%] rounded-full border-[4px] border-double border-[var(--color-telemetry-green)]/40"
            style={{ transformStyle: 'preserve-3d' }}
          >
            <div className="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 bg-[var(--color-telemetry-green)] rounded-full shadow-[0_0_10px_var(--color-telemetry-green)]" style={{ transform: 'rotateX(-65deg)' }} />
            <div className="absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2 w-2 h-2 bg-[var(--color-telemetry-green)] rounded-full shadow-[0_0_10px_var(--color-telemetry-green)]" style={{ transform: 'rotateX(-65deg)' }} />
          </motion.div>

          {/* Subtle Green Telemetry Pulse */}
          <motion.div
            animate={{ scale: [0.5, 1.5], opacity: [0.6, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
            className="absolute w-[50%] h-[50%] rounded-full bg-[var(--color-telemetry-green)]/10 border border-[var(--color-telemetry-green)]/30"
          />

          {/* Floating Glass Frame & Inner Core */}
          <div 
            className="absolute w-[40%] h-[40%] rounded-full border-4 border-t-[var(--color-io-blue-light)] border-r-[var(--color-io-orange)] border-b-[var(--color-telemetry-green)] border-l-[var(--color-io-blue-light)]/20 bg-[var(--color-io-navy-dark)]/80 backdrop-blur-xl shadow-[0_0_50px_rgba(0,45,98,0.7)] flex items-center justify-center transform-style-3d relative"
            style={{ transform: 'translateZ(30px)' }}
          >
             {/* Center Sensor Representation - Upright */}
             <div 
               className="relative flex items-center justify-center w-[80%] h-[80%] rounded-full overflow-hidden border border-[var(--color-io-blue-light)]/50 bg-[#020408]"
               style={{ transform: 'rotateX(-65deg) rotateZ(10deg)' }}
             >
                {/* Vertical Scan Effect */}
                <motion.div 
                  animate={{ top: ['-20%', '120%'] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
                  className="absolute left-0 w-full h-[3px] bg-[var(--color-telemetry-green)] shadow-[0_0_15px_var(--color-telemetry-green)] z-20"
                />

                <div className="absolute inset-0 bg-gradient-to-br from-[var(--color-io-navy)] to-[#011226]" />
                <Hexagon className="absolute w-[80%] h-[80%] text-[var(--color-io-blue-light)]/20" strokeWidth={1} />
                <motion.div 
                  animate={{ scale: [1, 1.1, 1], filter: ['brightness(1)', 'brightness(1.5)', 'brightness(1)'] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="z-10 text-[var(--color-telemetry-green)]"
                >
                  <Cpu className="w-10 h-10" />
                </motion.div>
                
                {/* Data streaming lines inside core */}
                <div className="absolute right-2 top-2 bottom-2 w-1 flex flex-col gap-1 overflow-hidden z-10">
                   {[1,2,3,4,5].map(i => (
                     <motion.div 
                       key={i}
                       className="w-full bg-[var(--color-io-orange)]"
                       initial={{ height: '0%' }}
                       animate={{ height: ['0%', '100%', '0%'] }}
                       transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
                     />
                   ))}
                </div>
             </div>
          </div>
          
        </motion.div>

        {/* Floating Info Panel - Top Right */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 1, duration: 1 }}
          className="absolute top-[10%] right-[-20%] glass-panel p-4 border border-[var(--color-telemetry-green)]/40 rounded-sm backdrop-blur-md hidden lg:flex items-center gap-4 shadow-[0_10px_30px_rgba(0,0,0,0.5)] z-30"
        >
          <div className="w-8 h-8 rounded-full bg-[var(--color-telemetry-green)]/10 flex items-center justify-center border border-[var(--color-telemetry-green)]/30">
            <CheckCircle2 className="w-4 h-4 text-[var(--color-telemetry-green)]" />
          </div>
          <div className="font-mono text-xs">
            <div className="text-[var(--color-telemetry-green)] font-bold tracking-wider mb-1">SYSTEM OPTIMAL</div>
            <div className="text-gray-400 flex justify-between gap-4"><span>Var:</span> <span className="text-white">0.0034</span></div>
          </div>
        </motion.div>

        {/* Floating Info Panel - Bottom Left */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 1.5, duration: 1 }}
          className="absolute bottom-[20%] left-[-20%] glass-panel p-4 border border-[var(--color-io-orange)]/40 rounded-sm backdrop-blur-md hidden lg:flex items-center gap-4 shadow-[0_10px_30px_rgba(0,0,0,0.5)] z-30"
        >
          <div className="w-8 h-8 rounded-full bg-[var(--color-io-orange)]/10 flex items-center justify-center border border-[var(--color-io-orange)]/30">
            <Activity className="w-4 h-4 text-[var(--color-io-orange)]" />
          </div>
          <div className="font-mono text-xs">
            <div className="text-[var(--color-io-orange)] font-bold tracking-wider mb-1">DATA STREAM</div>
            <div className="text-gray-400 flex justify-between gap-4"><span>Flow:</span> <span className="text-white">Active</span></div>
          </div>
        </motion.div>

      </motion.div>
    </div>
  );
}
