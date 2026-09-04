import React from 'react';
import { motion } from 'framer-motion';
import { Factory, Cpu, Radio, Zap, Database, Brain, Settings, Monitor, Network } from 'lucide-react';

const NODES = [
  { id: '1', name: 'INDIANOIL ASSETS', icon: Factory, color: 'var(--color-io-orange)' },
  { id: '2', name: 'IoT SENSORS', icon: Cpu, color: 'var(--color-telemetry-green)' },
  { id: '3', name: 'MQTT', icon: Radio, color: 'var(--color-io-blue-light)' },
  { id: '4', name: 'KAFKA', icon: Zap, color: 'var(--color-io-orange)' },
  { id: '5', name: 'TIMESCALEDB', icon: Database, color: 'var(--color-io-blue-light)' },
  { id: '6', name: 'AI ANOMALY ENGINE', icon: Brain, color: 'var(--color-telemetry-green)' },
  { id: '7', name: 'AUTOMATION ENGINE', icon: Settings, color: 'var(--color-io-orange)' },
  { id: '8', name: 'SENTINEL DASHBOARD', icon: Monitor, color: 'var(--color-telemetry-green)' },
];

const HWire = ({ dir, color }: { dir: 'right' | 'left', color: string }) => {
  return (
    <div className="relative w-8 md:w-16 xl:w-24 h-[2px] bg-gray-800/80 overflow-hidden mx-1">
      <motion.div
        animate={dir === 'right' ? { left: ['-50%', '150%'] } : { right: ['-50%', '150%'] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'linear', delay: Math.random() * 0.5 }}
        className={`absolute top-0 bottom-0 ${dir === 'right' ? 'w-[40%]' : 'w-[40%]'}`}
        style={{
          background: dir === 'right'
            ? `linear-gradient(90deg, transparent, ${color})`
            : `linear-gradient(270deg, transparent, ${color})`
        }}
      />
      {/* Small dot at the head of the packet */}
      <motion.div
        animate={dir === 'right' ? { left: ['-50%', '150%'] } : { right: ['-50%', '150%'] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'linear', delay: Math.random() * 0.5 }} // keep delay synced if wanted, but simpler to just use CSS trail
        className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full hidden" 
      />
    </div>
  );
};

const VWire = ({ color }: { color: string }) => {
  return (
    <div className="relative w-[2px] h-12 lg:h-16 bg-gray-800/80 overflow-hidden my-1">
      <motion.div
        animate={{ top: ['-50%', '150%'] }}
        transition={{ duration: 1.2, repeat: Infinity, ease: 'linear', delay: Math.random() * 0.5 }}
        className="absolute left-0 right-0 h-[40%]"
        style={{
          background: `linear-gradient(180deg, transparent, ${color})`
        }}
      />
    </div>
  );
};

const NodeBlock = ({ node }: { node: typeof NODES[0] }) => {
  return (
    <motion.div
      whileHover={{ scale: 1.05, borderColor: node.color, boxShadow: `0 0 20px ${node.color}30` }}
      className="relative z-10 bg-[#020408]/80 backdrop-blur border border-gray-800 p-4 w-32 md:w-40 xl:w-48 text-center flex flex-col items-center justify-center transition-colors duration-300 group"
      style={{
        clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)'
      }}
    >
      <div className="absolute top-0 left-0 w-full h-[1px] opacity-0 group-hover:opacity-100 transition-opacity" style={{ backgroundColor: node.color }} />
      <node.icon className="mb-3 w-6 h-6 transition-colors duration-300" style={{ color: node.color }} />
      <span className="font-mono text-[10px] md:text-xs font-bold text-gray-300 tracking-wider">
        {node.name}
      </span>
      {/* Background glow on hover */}
      <div 
        className="absolute inset-0 opacity-0 group-hover:opacity-10 pointer-events-none transition-opacity duration-300" 
        style={{ backgroundColor: node.color }} 
      />
    </motion.div>
  );
};

export default function SystemArchitecture() {
  return (
    <section className="relative w-full max-w-[1800px] mx-auto px-6 py-20 lg:px-16 z-10 border-t border-gray-900 mt-10">
      
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.8 }}
        className="mb-16 text-center"
      >
        <div className="inline-flex items-center gap-2 font-mono text-[10px] text-[var(--color-io-orange)] tracking-[0.3em] mb-2 uppercase border border-[var(--color-io-orange)]/30 bg-[var(--color-io-orange)]/5 px-3 py-1">
          <Network className="w-3 h-3" /> Topology
        </div>
        <h2 className="text-2xl md:text-3xl font-bold tracking-widest text-white font-mono uppercase">
          System Architecture
        </h2>
      </motion.div>

      <div className="w-full flex justify-center">
        
        {/* DESKTOP LAYOUT (U-Shape Pipeline) */}
        <div className="hidden lg:flex flex-col items-center">
          
          {/* ROW 1: Nodes 0 to 3 */}
          <div className="flex items-center">
            <NodeBlock node={NODES[0]} />
            <HWire dir="right" color={NODES[1].color} />
            <NodeBlock node={NODES[1]} />
            <HWire dir="right" color={NODES[2].color} />
            <NodeBlock node={NODES[2]} />
            <HWire dir="right" color={NODES[3].color} />
            <NodeBlock node={NODES[3]} />
          </div>

          {/* VERTICAL DROP (Aligns under Node 3 / 4th item) */}
          <div className="w-full flex justify-end pr-[4rem] xl:pr-[6rem]">
            <VWire color={NODES[4].color} />
          </div>

          {/* ROW 2: Nodes 4 to 7 (Reversed Visual Order) */}
          <div className="flex items-center flex-row-reverse">
            <NodeBlock node={NODES[4]} />
            <HWire dir="left" color={NODES[5].color} />
            <NodeBlock node={NODES[5]} />
            <HWire dir="left" color={NODES[6].color} />
            <NodeBlock node={NODES[6]} />
            <HWire dir="left" color={NODES[7].color} />
            <NodeBlock node={NODES[7]} />
          </div>

        </div>

        {/* MOBILE / TABLET LAYOUT (Vertical Pipeline) */}
        <div className="flex flex-col items-center lg:hidden">
          {NODES.map((node, i) => (
            <React.Fragment key={node.id}>
              <NodeBlock node={node} />
              {i < NODES.length - 1 && <VWire color={NODES[i + 1].color} />}
            </React.Fragment>
          ))}
        </div>

      </div>
    </section>
  );
}
