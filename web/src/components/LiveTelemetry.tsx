import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Thermometer, Gauge, Waves, Droplets, Activity, Zap } from 'lucide-react';

const Sparkline = ({ color, type, value, safetyLimit, dataPoints = 20 }: { color: string, type: 'line' | 'bar' | 'area', value: number, safetyLimit?: number, dataPoints?: number }) => {
  const [data, setData] = useState<number[]>([]);

  useEffect(() => {
    // Generate initial baseline data
    const initialData = Array.from({ length: dataPoints }, () => value);
    setData(initialData);
  }, [dataPoints]);

  useEffect(() => {
    // Push new value when it updates
    if (data.length > 0) {
      setData(prev => [...prev.slice(1), value]);
    }
  }, [value]);

  if (data.length === 0) return null;

  const maxVal = Math.max(...data, value * 1.2, safetyLimit || 0);
  const minVal = Math.min(...data, value * 0.8, safetyLimit ? safetyLimit * 0.5 : value);
  const range = (maxVal - minVal) || 1;
  const width = 200;
  const height = 60;
  
  const getY = (val: number) => {
    return height - ((val - minVal) / range) * height;
  };
  
  if (type === 'bar') {
    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible preserve-3d">
        {data.map((d, i) => (
          <motion.rect
            key={i}
            x={i * (width / data.length)}
            y={getY(d)}
            width={(width / data.length) - 2}
            height={height - getY(d)}
            fill={color}
            opacity={0.7}
            initial={{ height: 0, y: height }}
            animate={{ height: height - getY(d), y: getY(d) }}
            transition={{ duration: 0.3 }}
            className="transition-all duration-500 ease-in-out" // smooth live updates
          />
        ))}
        {safetyLimit !== undefined && (
          <line x1="0" y1={getY(safetyLimit)} x2={width} y2={getY(safetyLimit)} stroke="#ef4444" strokeDasharray="4" strokeWidth="1" opacity={0.6} />
        )}
      </svg>
    )
  }

  const points = data.map((d, i) => `${i * (width / (data.length - 1))},${getY(d)}`).join(' ');
  const areaPoints = `0,${height} ${points} ${width},${height}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
       {type === 'area' && (
         <motion.polygon 
           points={areaPoints} 
           fill={color} 
           className="transition-all duration-500 ease-in-out opacity-20"
           initial={{ opacity: 0 }}
           animate={{ opacity: 0.2 }}
           transition={{ duration: 1 }}
         />
       )}
       <motion.polyline
         points={points}
         fill="none"
         stroke={color}
         strokeWidth="2"
         className="transition-all duration-500 ease-in-out"
         initial={{ pathLength: 0 }}
         animate={{ pathLength: 1 }}
         transition={{ duration: 1.5, ease: "easeOut" }}
         style={{ filter: `drop-shadow(0 0 4px ${color})` }}
       />
       {safetyLimit !== undefined && (
         <line x1="0" y1={getY(safetyLimit)} x2={width} y2={getY(safetyLimit)} stroke="#ef4444" strokeDasharray="4" strokeWidth="1" opacity={0.6} />
       )}
    </svg>
  );
}

export default function LiveTelemetry() {
  const metrics = [
    { name: 'Temperature', icon: Thermometer, unit: '°C', baseValue: 84.2, safetyLimit: 90, color: 'var(--color-io-orange)', type: 'line' as const },
    { name: 'Pressure', icon: Gauge, unit: 'PSI', baseValue: 12.4, safetyLimit: 15, color: 'var(--color-io-blue-light)', type: 'bar' as const },
    { name: 'Flow Rate', icon: Waves, unit: 'L/m', baseValue: 450, safetyLimit: 500, color: 'var(--color-telemetry-green)', type: 'area' as const },
    { name: 'TDS Level', icon: Droplets, unit: 'ppm', baseValue: 120, safetyLimit: 150, color: 'var(--color-io-blue-light)', type: 'line' as const },
    { name: 'Motor Vibration', icon: Activity, unit: 'mm/s', baseValue: 4.2, safetyLimit: 6, color: 'var(--color-io-orange)', type: 'line' as const },
    { name: 'Energy Draw', icon: Zap, unit: 'kW', baseValue: 18.5, safetyLimit: 25, color: 'var(--color-telemetry-green)', type: 'bar' as const },
  ];

  // Live values driven by WebSocket or fallback jitter
  const [liveValues, setLiveValues] = useState(metrics.map(m => m.baseValue));

  useEffect(() => {
    let ws: WebSocket | null = null;
    
    try {
      ws = new WebSocket('ws://localhost:8000/ws/live');
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLiveValues([
            data.find((d: any) => d.id === 'TEMP')?.baseValue || metrics[0].baseValue,
            data.find((d: any) => d.id === 'PRES')?.baseValue || metrics[1].baseValue,
            data.find((d: any) => d.id === 'FLOW')?.baseValue || metrics[2].baseValue,
            data.find((d: any) => d.id === 'TDS')?.baseValue || metrics[3].baseValue,
            data.find((d: any) => d.id === 'VIBE')?.baseValue || metrics[4].baseValue,
            data.find((d: any) => d.id === 'PWR')?.baseValue || metrics[5].baseValue,
          ]);
        } catch (e) {
          console.error("Failed to parse live telemetry", e);
        }
      };
    } catch (e) {
      console.warn("WebSocket connection failed, falling back to mock data");
    }

    const interval = setInterval(() => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        // Graceful fallback: jitter values slightly for live effect if disconnected
        setLiveValues(prev => prev.map((_val, i) => {
          const jitter = (Math.random() - 0.5) * (metrics[i].baseValue * 0.02); // 2% jitter
          return Number((metrics[i].baseValue + jitter).toFixed(1));
        }));
      }
    }, 1500);

    return () => {
      if (ws) ws.close();
      clearInterval(interval);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section id="telemetry" className="relative w-full max-w-[1800px] mx-auto px-6 py-20 lg:px-16 z-10">
      
      {/* Background Decorators */}
      <div className="absolute top-0 left-16 right-16 h-[1px] bg-gradient-to-r from-transparent via-[var(--color-io-blue-light)]/30 to-transparent" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-1 bg-[var(--color-io-blue-light)]/50 shadow-[0_0_15px_rgba(0,71,155,0.8)]" />

      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.8 }}
        className="mb-12"
      >
        <h2 className="text-3xl md:text-4xl font-bold tracking-wider text-white mb-2 font-mono uppercase flex items-center gap-4">
          <div className="w-2 h-2 rounded-full bg-[var(--color-telemetry-green)] animate-pulse shadow-[0_0_10px_var(--color-telemetry-green)]" />
          Live Telemetry
        </h2>
        <p className="text-gray-400 font-mono text-sm tracking-widest border-l-2 border-[var(--color-io-orange)] pl-4 py-1">
          Real-time operational intelligence across IndianOil assets.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {metrics.map((metric, i) => (
          <motion.div
            key={metric.name}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.6, delay: i * 0.1 }}
            whileHover={{ y: -5, borderColor: metric.color, boxShadow: `0 10px 30px -15px ${metric.color}` }}
            className="glass-panel p-6 border border-gray-800 rounded-lg relative overflow-hidden group transition-all duration-300"
          >
            {/* Top right corner accent */}
            <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 opacity-30 group-hover:opacity-100 transition-opacity" style={{ borderColor: metric.color }} />
            
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-black/40 border border-gray-800 group-hover:border-transparent transition-colors" style={{ backgroundColor: `color-mix(in srgb, ${metric.color} 10%, transparent)` }}>
                  <metric.icon className="w-5 h-5" style={{ color: metric.color }} />
                </div>
                <h3 className="font-mono text-sm font-bold text-gray-300 tracking-wider uppercase">{metric.name}</h3>
              </div>
              <div className="text-right">
                <motion.div 
                  key={liveValues[i]}
                  initial={{ opacity: 0.5, y: -2 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="font-mono text-2xl font-bold text-white tracking-tight"
                >
                  {liveValues[i]}
                </motion.div>
                <div className="font-mono text-xs text-gray-500">{metric.unit}</div>
              </div>
            </div>

            <div className="w-full h-20 mt-4 relative">
               {/* Background Grid for chart */}
               <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:10px_10px]" />
               
               <div className="absolute inset-0 pt-2">
                 <Sparkline color={metric.color} type={metric.type} value={liveValues[i]} safetyLimit={metric.safetyLimit} />
               </div>
            </div>
            
            {/* Subtle glow underneath chart */}
            <div className="absolute bottom-0 left-0 right-0 h-10 blur-[20px] opacity-20 pointer-events-none" style={{ backgroundColor: metric.color }} />
          </motion.div>
        ))}
      </div>
    </section>
  );
}
