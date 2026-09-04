import { motion } from 'framer-motion';
import { Database, Filter, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const ASSETS = [
  { 
    id: 'RO-001', 
    status: 'ACTIVE', 
    statusColor: 'var(--color-telemetry-green)', 
    pressure: '12.4 PSI', 
    flow: '450.2 L/M', 
    temp: '82.4°C', 
    health: '99.2%', 
    lastEvent: 'T-00:04:12 // SYNC_OK' 
  },
  { 
    id: 'RO-002', 
    status: 'ACTIVE', 
    statusColor: 'var(--color-telemetry-green)', 
    pressure: '11.8 PSI', 
    flow: '445.8 L/M', 
    temp: '81.9°C', 
    health: '98.5%', 
    lastEvent: 'T-00:15:40 // CALIBRATE_REQ' 
  },
  { 
    id: 'RO-003', 
    status: 'WARNING', 
    statusColor: 'var(--color-io-orange)', 
    pressure: '14.2 PSI', 
    flow: '412.0 L/M', 
    temp: '86.1°C', 
    health: '82.4%', 
    lastEvent: 'T-00:02:10 // FLOW_DEGRADE' 
  },
  { 
    id: 'RO-004', 
    status: 'CRITICAL', 
    statusColor: '#ef4444', 
    pressure: '17.1 PSI', 
    flow: '310.5 L/M', 
    temp: '92.4°C', 
    health: '64.1%', 
    lastEvent: 'T-00:00:12 // PRESSURE_SPIKE' 
  },
  { 
    id: 'RO-005', 
    status: 'STANDBY', 
    statusColor: 'var(--color-io-blue-light)', 
    pressure: '0.0 PSI', 
    flow: '0.0 L/M', 
    temp: '45.0°C', 
    health: '100.0%', 
    lastEvent: 'T-02:14:00 // IDLE_STATE' 
  },
];

export default function AssetMonitoring() {
  return (
    <section id="assets" className="relative w-full max-w-[1800px] mx-auto px-6 py-20 lg:px-16 z-10">
      
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, x: -30 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.8 }}
        className="mb-8 flex items-center justify-between"
      >
        <div>
          <div className="font-mono text-[10px] text-[var(--color-io-blue-light)] tracking-[0.3em] mb-2 uppercase flex items-center gap-2">
            <Filter className="w-3 h-3" /> Filtration Nodes
          </div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-widest text-white font-mono uppercase">
            Asset Monitoring
          </h2>
        </div>
        
        <Link to="/dashboard">
          <button className="hidden md:flex items-center gap-2 font-mono text-xs border border-[var(--color-io-blue-light)]/40 px-4 py-2 hover:bg-[var(--color-io-blue-light)]/10 hover:border-[var(--color-io-blue-light)] transition-colors text-gray-300">
            VIEW ALL SYSTEMS <ArrowRight className="w-3 h-3" />
          </button>
        </Link>
      </motion.div>

      {/* Table Container */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-50px" }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="relative bg-[#020408]/80 backdrop-blur-sm border border-[var(--color-io-blue-light)]/20 p-1 md:p-4 shadow-none"
        style={{ clipPath: 'polygon(15px 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%, 0 15px)' }}
      >
        {/* Decorative brackets */}
        <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-[var(--color-io-orange)]" />
        <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-[var(--color-telemetry-green)]" />

        <div className="w-full overflow-x-auto">
          <table className="w-full text-left font-mono">
            <thead>
              <tr className="border-b border-gray-800 text-[10px] text-gray-500 tracking-[0.2em] uppercase">
                <th className="py-4 px-4 font-normal">Asset ID</th>
                <th className="py-4 px-4 font-normal">Status</th>
                <th className="py-4 px-4 font-normal text-right">Pressure</th>
                <th className="py-4 px-4 font-normal text-right">Flow</th>
                <th className="py-4 px-4 font-normal text-right">Temp</th>
                <th className="py-4 px-4 font-normal text-right">Health</th>
                <th className="py-4 px-4 font-normal pl-8">Last Event</th>
              </tr>
            </thead>
            <tbody>
              {ASSETS.map((asset, index) => {
                const isCritical = asset.status === 'CRITICAL';
                return (
                  <motion.tr 
                    key={asset.id}
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: index * 0.1 + 0.4 }}
                    className={`group border-b border-gray-800/50 cursor-pointer transition-all duration-300 hover:bg-[var(--color-io-navy)] ${isCritical ? 'hover:bg-red-950/20' : ''}`}
                    style={{
                      '--hover-glow': isCritical 
                        ? 'inset 0 0 20px rgba(239, 68, 68, 0.1)' 
                        : 'inset 0 0 20px rgba(243,112,33,0.05), inset 0 0 10px rgba(0,71,155,0.1)'
                    } as any}
                  >
                    {/* Hover Glow via absolute pseudo-element logic injected via style hack or tailwind peer/group */}
                    {/* We can just use hover:shadow inline via Tailwind arbitrary values but inset is tricky with table rows. We'll rely on the row bg color and a subtle left border instead. */}
                    
                    <td className="py-5 px-4 relative">
                      {/* Interactive Left Border Accent */}
                      <div className={`absolute left-0 top-0 bottom-0 w-[2px] opacity-0 group-hover:opacity-100 transition-opacity duration-300 ${isCritical ? 'bg-red-500' : 'bg-[var(--color-io-orange)]'}`} />
                      
                      <div className="flex items-center gap-3 text-white font-bold text-sm">
                        <Database className="w-4 h-4 text-gray-600 group-hover:text-[var(--color-io-blue-light)] transition-colors" />
                        {asset.id}
                      </div>
                    </td>
                    
                    <td className="py-5 px-4 text-xs tracking-wider">
                      <div className="flex items-center gap-2">
                        <div 
                          className={`w-1.5 h-1.5 rounded-full ${asset.status === 'ACTIVE' || asset.status === 'CRITICAL' ? 'animate-pulse' : ''}`}
                          style={{ backgroundColor: asset.statusColor, boxShadow: `0 0 8px ${asset.statusColor}` }}
                        />
                        <span style={{ color: asset.statusColor }}>{asset.status}</span>
                      </div>
                    </td>
                    
                    <td className="py-5 px-4 text-right text-gray-300 text-sm">
                      {asset.pressure}
                    </td>
                    
                    <td className="py-5 px-4 text-right text-gray-300 text-sm">
                      {asset.flow}
                    </td>
                    
                    <td className="py-5 px-4 text-right text-gray-300 text-sm">
                      <span className={Number(asset.temp.split('°')[0]) > 90 ? 'text-red-400 font-bold' : ''}>
                        {asset.temp}
                      </span>
                    </td>
                    
                    <td className="py-5 px-4 text-right text-sm">
                      <span style={{ color: asset.statusColor }} className="font-bold">
                        {asset.health}
                      </span>
                    </td>
                    
                    <td className="py-5 px-4 pl-8 text-xs text-gray-500 group-hover:text-gray-300 transition-colors">
                      {asset.lastEvent}
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </motion.div>
    </section>
  );
}
