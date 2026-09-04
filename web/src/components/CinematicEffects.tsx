import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export default function CinematicEffects() {
  const [dimensions, setDimensions] = useState({ width: 1000, height: 1000 });

  useEffect(() => {
    // Only access window on client
    setDimensions({
      width: window.innerWidth,
      height: window.innerHeight
    });
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-[100] overflow-hidden">
      
      {/* 1. Subtle horizontal scanline */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px] opacity-30 mix-blend-overlay" />
      
      {/* 2. Very subtle film grain using SVG fractal noise */}
      <div 
        className="absolute inset-0 mix-blend-overlay opacity-20" 
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} 
      />

      {/* 3. Dark vignette */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,rgba(2,4,8,0.95)_100%)] mix-blend-multiply opacity-80" />

      {/* 6. Holographic bloom overlay (very slight global contrast/brightness lift at edges) */}
      <div className="absolute inset-0 shadow-[inset_0_0_100px_rgba(0,71,155,0.1)] pointer-events-none mix-blend-screen" />

      {/* 4. Floating particles (Sparse & Professional) */}
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-[2px] h-[2px] rounded-full"
          style={{ 
            backgroundColor: i % 3 === 0 ? 'var(--color-io-orange)' : i % 2 === 0 ? 'var(--color-telemetry-green)' : 'white',
            boxShadow: `0 0 8px ${i % 3 === 0 ? 'var(--color-io-orange)' : i % 2 === 0 ? 'var(--color-telemetry-green)' : 'white'}` 
          }}
          initial={{ 
            x: Math.random() * dimensions.width, 
            y: dimensions.height + 20 
          }}
          animate={{
            y: -20,
            x: `+=${Math.random() * 100 - 50}`, // slight drift
            opacity: [0, 0.4, 0]
          }}
          transition={{
            duration: Math.random() * 15 + 15,
            repeat: Infinity,
            ease: "linear",
            delay: Math.random() * 20
          }}
        />
      ))}

      {/* 7. HUD corner decorations */}
      <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-[var(--color-io-blue-light)]/40 opacity-70" />
      <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-[var(--color-io-blue-light)]/40 opacity-70" />
      <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-[var(--color-io-blue-light)]/40 opacity-70" />
      <div className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-[var(--color-io-blue-light)]/40 opacity-70" />

      {/* Decorative Target Reticles */}
      <div className="absolute top-12 left-12 w-2 h-2 border border-[var(--color-telemetry-green)]/30 rounded-full flex items-center justify-center opacity-50">
        <div className="w-[1px] h-3 bg-[var(--color-telemetry-green)]/40 absolute" />
        <div className="h-[1px] w-3 bg-[var(--color-telemetry-green)]/40 absolute" />
      </div>
      <div className="absolute bottom-12 right-12 w-2 h-2 border border-[var(--color-io-orange)]/30 rounded-full flex items-center justify-center opacity-50">
        <div className="w-[1px] h-3 bg-[var(--color-io-orange)]/40 absolute" />
        <div className="h-[1px] w-3 bg-[var(--color-io-orange)]/40 absolute" />
      </div>
    </div>
  );
}
