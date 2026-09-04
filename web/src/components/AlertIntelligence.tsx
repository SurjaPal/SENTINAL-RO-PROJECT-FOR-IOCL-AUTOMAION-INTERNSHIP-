import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, AlertCircle, Info, Terminal, Activity } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface AlertData {
  id: string;
  timestamp: Date;
  assetId: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  description: string;
  status: string;
  theme: any;
}

const getThemeForSeverity = (severity: string) => {
  if (severity === 'CRITICAL' || severity === 'urgent' || severity === 'high') {
    return {
      text: 'text-red-500',
      border: 'border-red-500/30',
      bg: 'bg-red-500/5',
      glow: 'shadow-[0_0_15px_rgba(239,68,68,0.2)]',
      icon: AlertTriangle
    };
  } else if (severity === 'WARNING' || severity === 'medium') {
    return {
      text: 'text-[var(--color-io-orange)]',
      border: 'border-[var(--color-io-orange)]/30',
      bg: 'bg-[var(--color-io-orange)]/5',
      glow: 'shadow-[0_0_15px_rgba(243,112,33,0.1)]',
      icon: AlertCircle
    };
  } else {
    return {
      text: 'text-[var(--color-io-blue-light)]',
      border: 'border-[var(--color-io-blue-light)]/30',
      bg: 'bg-[var(--color-io-blue-light)]/5',
      glow: 'shadow-none',
      icon: Info
    };
  }
};

export default function AlertIntelligence() {
  const [alerts, setAlerts] = useState<AlertData[]>([]);

  const fetchAlerts = async () => {
    try {
      const [anomaliesRes, triageRes, dispatchRes] = await Promise.all([
        fetch(`${API_URL}/api/anomalies?limit=5`),
        fetch(`${API_URL}/api/triage-suggestions?limit=5`),
        fetch(`${API_URL}/api/dispatch-tickets?limit=5`)
      ]);

      const anomalies = await anomaliesRes.json();
      const triage = await triageRes.json();
      const dispatch = await dispatchRes.json();

      const newAlerts: AlertData[] = [];

      // Map Dispatch Tickets
      dispatch.forEach((d: any, index: number) => {
        newAlerts.push({
          id: `DISPATCH-${d.ticket_id}-${index}`,
          timestamp: new Date(d.time),
          assetId: d.ro_id,
          severity: 'INFO',
          description: `[DISPATCH TICKET: ${d.ticket_id}]\nAutomated logistics has dispatched spare part to RO.\nPart: ${d.part_name}`,
          status: d.status,
          theme: getThemeForSeverity('INFO')
        });
      });

      // Map Triage Suggestions
      triage.forEach((t: any) => {
        newAlerts.push({
          id: `TRG-${t.complaint_id}`,
          timestamp: new Date(t.time),
          assetId: t.ro_id,
          severity: t.priority === 'urgent' ? 'CRITICAL' : (t.priority === 'high' ? 'WARNING' : 'INFO'),
          description: `[TRIAGE: ${t.complaint_category.toUpperCase()}] ${t.suggested_root_cause}`,
          status: 'ACTION REQUIRED',
          theme: getThemeForSeverity(t.priority)
        });
      });

      // Map Anomalies
      anomalies.forEach((a: any, index: number) => {
        newAlerts.push({
          id: `ANM-${new Date(a.time).getTime()}-${index}`,
          timestamp: new Date(a.time),
          assetId: a.ro_id,
          severity: 'CRITICAL',
          description: `Anomaly detected on ${a.sensor_type}: ${a.reason}`,
          status: 'INVESTIGATING',
          theme: getThemeForSeverity('CRITICAL')
        });
      });

      // Sort by timestamp descending
      newAlerts.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

      setAlerts(newAlerts);
    } catch (error) {
      console.error("Failed to fetch alerts", error);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const timer = setInterval(fetchAlerts, 5000);
    return () => clearInterval(timer);
  }, []);

  return (
    <section id="anomalies" className="relative w-full max-w-[1800px] mx-auto px-6 py-20 lg:px-16 z-10">
      
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.8 }}
        className="mb-8"
      >
        <div className="flex items-center gap-4 mb-2">
          <h2 className="text-2xl md:text-3xl font-bold tracking-widest text-white font-mono uppercase">
            Alert Intelligence
          </h2>
          <div className="flex items-center gap-2 border border-red-500/30 bg-red-500/10 px-3 py-1 font-mono text-[10px] tracking-widest text-red-500 uppercase">
            <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse shadow-[0_0_5px_red]" />
            Live Monitor
          </div>
        </div>
        <p className="text-gray-400 font-mono text-sm tracking-widest border-l-2 border-[var(--color-io-blue-light)] pl-4 py-1">
          Real-time event streaming and automated severity classification.
        </p>
      </motion.div>

      {/* Console Frame */}
      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-50px" }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="w-full bg-[#03060C] border border-gray-800 relative overflow-hidden"
        style={{ clipPath: 'polygon(15px 0, 100% 0, 100% calc(100% - 15px), calc(100% - 15px) 100%, 0 100%, 0 15px)' }}
      >
        {/* Console Header Bar */}
        <div className="flex items-center justify-between border-b border-gray-800 bg-[#050a14] px-4 py-2">
          <div className="flex items-center gap-3 text-gray-500 font-mono text-xs">
            <Terminal className="w-4 h-4" />
            <span>SYS_EVENT_LOG // TAIL -F</span>
          </div>
          <div className="flex gap-2">
            <div className="w-2 h-2 rounded-full bg-gray-700" />
            <div className="w-2 h-2 rounded-full bg-gray-700" />
            <div className="w-2 h-2 rounded-full bg-gray-700" />
          </div>
        </div>

        {/* Table Headers */}
        <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-gray-800/50 bg-[#020408]/50 font-mono text-[10px] text-gray-500 uppercase tracking-widest">
          <div className="col-span-2">Timestamp</div>
          <div className="col-span-1">Asset</div>
          <div className="col-span-2">Severity</div>
          <div className="col-span-5">Description</div>
          <div className="col-span-2 text-right">Status</div>
        </div>

        {/* Alert Rows */}
        <div className="flex flex-col">
          {alerts.length === 0 && (
            <div className="px-6 py-5 text-gray-500 font-mono text-sm text-center border-b border-gray-800/50">
              NO EVENTS DETECTED
            </div>
          )}
          {alerts.map((alert, i) => {
            const timeString = alert.timestamp.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
            
            const isCritical = alert.severity === 'CRITICAL';

            return (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.15 + 0.3 }}
                className={`relative group grid grid-cols-1 md:grid-cols-12 gap-4 px-6 py-5 border-b border-gray-800/50 hover:bg-[#050A14] transition-colors duration-300 ${alert.theme.bg}`}
              >
                {/* Left Active Pulse Line */}
                <div className={`absolute left-0 top-0 bottom-0 w-[2px] ${isCritical ? 'bg-red-500 shadow-[0_0_10px_red]' : 'bg-transparent'}`} />
                {isCritical && (
                  <motion.div 
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="absolute inset-0 bg-[radial-gradient(ellipse_at_left,rgba(239,68,68,0.05)_0%,transparent_50%)] pointer-events-none" 
                  />
                )}

                {/* Timestamp & ID (Mobile stacking handling) */}
                <div className="col-span-2 font-mono text-xs text-gray-400 flex items-center gap-2">
                  <Activity className={`w-3 h-3 ${isCritical ? 'text-red-500 animate-pulse' : 'text-gray-600'}`} />
                  {timeString}
                </div>
                
                <div className="col-span-1 font-mono text-xs font-bold text-white flex items-center">
                  {alert.assetId}
                </div>

                {/* Severity Badge */}
                <div className="col-span-2 flex items-center">
                  <span className={`inline-flex items-center gap-2 px-2.5 py-1 border font-mono text-[10px] tracking-widest uppercase ${alert.theme.text} ${alert.theme.border} bg-black/40 ${alert.theme.glow}`}>
                    <alert.theme.icon className="w-3 h-3" />
                    {alert.severity}
                  </span>
                </div>

                {/* Description */}
                <div className="col-span-5 font-sans text-sm text-gray-300 flex items-center leading-relaxed whitespace-pre-wrap">
                  {alert.description}
                </div>

                {/* Status */}
                <div className="col-span-2 flex md:justify-end items-center font-mono text-[10px] tracking-widest text-gray-500 uppercase">
                  <div className="flex items-center gap-2">
                    {alert.status}
                    <div className="w-1.5 h-1.5 rounded-full bg-gray-600 group-hover:bg-gray-400 transition-colors" />
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
        
        {/* Footer Scanning Line */}
        <div className="w-full h-1 bg-[#020408] relative overflow-hidden">
          <motion.div 
            animate={{ x: ['-100%', '100%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            className="absolute top-0 bottom-0 w-1/4 bg-gradient-to-r from-transparent via-[var(--color-telemetry-green)]/30 to-transparent"
          />
        </div>
      </motion.div>
    </section>
  );
}
