import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowLeft, Activity, ShieldAlert, CheckCircle, Flame, Database, Zap, HardDrive, BarChart2 } from 'lucide-react';

// Reusable mock sparkline component for dashboard charts
const Chart = ({ color, points }: { color: string, points: number[] }) => {
  const max = Math.max(...points) * 1.2;
  const width = 300;
  const height = 100;
  const path = points.map((p, i) => `${i * (width / (points.length - 1))},${height - (p / max) * height}`).join(' ');
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible preserve-3d">
      <motion.polyline 
        points={path} 
        fill="none" 
        stroke={color} 
        strokeWidth="2" 
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, ease: "easeOut" }}
        style={{ filter: `drop-shadow(0 0 5px ${color})` }}
      />
      <polygon points={`0,${height} ${path} ${width},${height}`} fill={color} opacity="0.1" />
    </svg>
  );
};

export default function DashboardPage() {
  const [time, setTime] = useState(new Date().toLocaleTimeString('en-US', { hour12: false }));

  useEffect(() => {
    const t = setInterval(() => setTime(new Date().toLocaleTimeString('en-US', { hour12: false })), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="min-h-screen bg-[#020408] text-white font-sans overflow-x-hidden selection:bg-[var(--color-io-orange)] selection:text-white">
      
      {/* Background Grid */}
      <div className="fixed inset-0 pointer-events-none z-0 opacity-20">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:40px_40px]" />
        <div className="absolute top-1/4 left-1/4 w-[50vw] h-[50vw] rounded-full bg-[var(--color-io-blue)]/5 blur-[120px] mix-blend-screen" />
      </div>

      {/* Top System Status Bar */}
      <header className="sticky top-0 z-50 bg-[#020408]/90 backdrop-blur-md border-b border-gray-800 flex justify-between items-center px-6 py-3">
        <div className="flex items-center gap-6">
          <Link to="/" className="text-gray-400 hover:text-white transition-colors flex items-center gap-2 font-mono text-xs uppercase tracking-widest group">
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" /> Overview
          </Link>
          <div className="h-4 w-[1px] bg-gray-800" />
          <div className="flex items-center gap-2 font-mono text-xs tracking-widest text-[var(--color-telemetry-green)]">
            <div className="w-2 h-2 rounded-full bg-[var(--color-telemetry-green)] animate-pulse shadow-[0_0_8px_var(--color-telemetry-green)]" />
            SYSTEM SECURE
          </div>
        </div>
        <div className="flex items-center gap-6 font-mono text-[10px] uppercase tracking-widest text-gray-500">
          <div className="hidden md:flex gap-2 items-center">
            LATENCY: <span className="text-white">14ms</span>
          </div>
          <div className="hidden md:flex gap-2 items-center">
            ACTIVE NODES: <span className="text-white">5,102</span>
          </div>
          <div className="bg-gray-900 px-3 py-1 text-gray-300 font-bold border border-gray-800">{time} UTC</div>
        </div>
      </header>

      <main className="relative z-10 w-full max-w-[1800px] mx-auto p-6 flex flex-col gap-6">
        
        {/* KPI Grid */}
        <div id="section-kpi" className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'TOTAL ASSETS', value: '14,204', icon: HardDrive, color: 'var(--color-io-blue-light)' },
            { label: 'ACTIVE ALERTS', value: '3', icon: ShieldAlert, color: 'var(--color-io-orange)' },
            { label: 'HEALTHY ASSETS', value: '14,198', icon: CheckCircle, color: 'var(--color-telemetry-green)' },
            { label: 'CRITICAL', value: '2', icon: Flame, color: '#ef4444' }
          ].map((kpi, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-[#050A14] border border-gray-800/80 p-4 relative overflow-hidden group hover:border-gray-700 transition-colors"
            >
              <div className="absolute top-0 left-0 w-1 h-full opacity-50" style={{ backgroundColor: kpi.color }} />
              <div className="flex justify-between items-start mb-2">
                <span className="font-mono text-[10px] text-gray-500 tracking-[0.2em]">{kpi.label}</span>
                <kpi.icon className="w-4 h-4 opacity-40" style={{ color: kpi.color }} />
              </div>
              <div className="font-mono text-3xl font-bold text-white">{kpi.value}</div>
            </motion.div>
          ))}
        </div>

        {/* Middle Tier: Charts & Live Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Main Telemetry Chart */}
          <motion.div 
            id="section-charts"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="col-span-1 lg:col-span-2 bg-[#050A14] border border-gray-800/80 p-6 flex flex-col"
          >
            <div className="flex justify-between items-center mb-6 border-b border-gray-800 pb-2">
              <h3 className="font-mono text-xs text-gray-400 tracking-[0.2em] uppercase flex items-center gap-2">
                <BarChart2 className="w-4 h-4 text-[var(--color-io-blue-light)]" /> Network Pressure & Flow
              </h3>
              <div className="flex gap-2">
                <div className="font-mono text-[10px] px-2 py-1 bg-[var(--color-io-blue-light)]/10 text-[var(--color-io-blue-light)]">PRESSURE</div>
                <div className="font-mono text-[10px] px-2 py-1 bg-[var(--color-telemetry-green)]/10 text-[var(--color-telemetry-green)]">FLOW RATE</div>
              </div>
            </div>
            <div className="flex-grow relative min-h-[250px]">
              <div className="absolute inset-0">
                <Chart color="var(--color-telemetry-green)" points={[12, 14, 15, 14.5, 18, 22, 24, 23, 25, 26, 24, 23, 25, 28, 30]} />
              </div>
              <div className="absolute inset-0 pt-4">
                <Chart color="var(--color-io-blue-light)" points={[30, 28, 25, 24, 25, 23, 22, 20, 18, 19, 17, 15, 14, 13, 14]} />
              </div>
            </div>
          </motion.div>

          {/* Live Alert Feed */}
          <motion.div 
            id="section-feed"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="col-span-1 bg-[#050A14] border border-gray-800/80 p-6 flex flex-col"
          >
            <h3 className="font-mono text-xs text-gray-400 tracking-[0.2em] uppercase mb-4 border-b border-gray-800 pb-2 flex items-center gap-2">
              <Activity className="w-4 h-4 text-[var(--color-io-orange)] animate-pulse" /> Live Event Stream
            </h3>
            <div className="flex-grow flex flex-col gap-3 overflow-hidden">
              {[
                { time: '13:54:12', msg: 'Node RO-990 connected', type: 'info' },
                { time: '13:53:44', msg: 'Pressure spike detected on RO-042', type: 'critical' },
                { time: '13:52:10', msg: 'Auto-scaling TimescaleDB clusters', type: 'info' },
                { time: '13:50:05', msg: 'Efficiency drop on RO-019', type: 'warning' },
                { time: '13:48:22', msg: 'Routine health check: Passed', type: 'info' },
                { time: '13:45:00', msg: 'Firmware OTA deployed to Sector 7', type: 'info' },
              ].map((event, i) => (
                <div key={i} className="flex gap-3 items-start border-l-2 pl-3 py-1" style={{ borderColor: event.type === 'critical' ? '#ef4444' : event.type === 'warning' ? 'var(--color-io-orange)' : 'var(--color-io-blue-light)' }}>
                  <div className="font-mono text-[10px] text-gray-500 shrink-0">{event.time}</div>
                  <div className={`text-xs ${event.type === 'critical' ? 'text-red-400 font-bold' : event.type === 'warning' ? 'text-[var(--color-io-orange)]' : 'text-gray-300'}`}>{event.msg}</div>
                </div>
              ))}
            </div>
          </motion.div>

        </div>

        {/* Bottom Tier: Matrix & Infrastructure */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Asset Health Matrix */}
          <motion.div 
            id="section-matrix"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="col-span-1 lg:col-span-2 bg-[#050A14] border border-gray-800/80 p-6"
          >
            <h3 className="font-mono text-xs text-gray-400 tracking-[0.2em] uppercase mb-4 border-b border-gray-800 pb-2">Fleet Health Matrix</h3>
            <div className="grid grid-cols-10 md:grid-cols-20 gap-1">
              {[...Array(200)].map((_, i) => {
                const rand = Math.random();
                let color = 'bg-[var(--color-telemetry-green)]';
                if (rand > 0.98) color = 'bg-red-500 animate-pulse';
                else if (rand > 0.95) color = 'bg-[var(--color-io-orange)]';
                else if (rand > 0.90) color = 'bg-gray-800'; // Offline

                return (
                  <div 
                    key={i} 
                    className={`aspect-square w-full rounded-sm opacity-80 hover:opacity-100 cursor-pointer ${color}`} 
                    title={`Asset ${i+1}`}
                  />
                )
              })}
            </div>
            <div className="flex gap-4 mt-4 font-mono text-[10px] text-gray-500 uppercase">
              <div className="flex items-center gap-1"><div className="w-2 h-2 bg-[var(--color-telemetry-green)]" /> Online</div>
              <div className="flex items-center gap-1"><div className="w-2 h-2 bg-[var(--color-io-orange)]" /> Warning</div>
              <div className="flex items-center gap-1"><div className="w-2 h-2 bg-red-500" /> Critical</div>
              <div className="flex items-center gap-1"><div className="w-2 h-2 bg-gray-800" /> Offline</div>
            </div>
            {/* Branding */}
            <div className="flex items-center gap-4 mt-6">
              <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center p-1.5 shadow-[0_0_15px_rgba(243,112,33,0.2)]">
                <img src="/iocl-logo.svg" alt="IndianOil Logo" className="w-full h-full object-contain" />
              </div>
            </div>
          </motion.div>

          {/* Infrastructure Status */}
          <motion.div 
            id="section-infrastructure"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="col-span-1 bg-[#050A14] border border-gray-800/80 p-6"
          >
            <h3 className="font-mono text-xs text-gray-400 tracking-[0.2em] uppercase mb-4 border-b border-gray-800 pb-2">Core Infrastructure</h3>
            <div className="flex flex-col gap-4">
              {[
                { name: 'KAFKA STREAM', icon: Zap, status: 'CONNECTED', metric: '14.2k msg/s' },
                { name: 'TIMESCALEDB', icon: Database, status: 'CONNECTED', metric: '4ms latency' },
                { name: 'GRAFANA UI', icon: Activity, status: 'ONLINE', metric: 'Syncing' },
              ].map((sys, i) => (
                <div key={i} className="flex items-center justify-between p-3 border border-gray-800/50 bg-[#020408]">
                  <div className="flex items-center gap-3">
                    <sys.icon className="w-4 h-4 text-[var(--color-io-blue-light)]" />
                    <div>
                      <div className="font-mono text-xs font-bold text-gray-300 uppercase">{sys.name}</div>
                      <div className="font-mono text-[10px] text-gray-500">{sys.metric}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-[10px] text-[var(--color-telemetry-green)]">
                    <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-telemetry-green)] animate-pulse" />
                    {sys.status}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

        </div>
      </main>
    </div>
  );
}
