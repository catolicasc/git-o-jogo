'use client';

import React, { useEffect, useState, useRef } from 'react';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { motion, useAnimation } from 'framer-motion';

export default function MagicalLottie() {
  const controls = useAnimation();
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const mousePos = useRef({ x: 0, y: 0 });
  const dragonPos = useRef({ x: 0, y: 0 });
  const isFleeing = useRef(false);

  useEffect(() => {
    // Set initial window dimensions safely
    const updateDimensions = () => {
        setDimensions({
            width: window.innerWidth,
            height: window.innerHeight
        });
    };
    
    // Initial set
    updateDimensions();

    window.addEventListener('resize', updateDimensions);
    
    const handleMouseMove = (e: MouseEvent) => {
        mousePos.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener('mousemove', handleMouseMove);

    return () => {
        window.removeEventListener('resize', updateDimensions);
        window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  useEffect(() => {
    if (dimensions.width === 0) return;

    const checkDistance = () => {
        if (isFleeing.current) return;

        const dx = dragonPos.current.x - mousePos.current.x;
        const dy = dragonPos.current.y - mousePos.current.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < 200) { // Flee radius
             flee();
        }
    };

    const interval = setInterval(checkDistance, 100);

    const flyRandomly = async () => {
        if (isFleeing.current) return;

        // Random position
        const x = Math.random() * (dimensions.width - 200); 
        const y = Math.random() * (dimensions.height - 200);
        
        dragonPos.current = { x, y }; // Update ref for distance check

        const duration = 5 + Math.random() * 10; 

        // We use a promise wrapper to allow cancellation/interruption logic if we wanted,
        // but framer motion's controls.start returns a promise that resolves when animation completes.
        try {
            await controls.start({
                x,
                y,
                transition: { 
                    duration: duration, 
                    ease: "easeInOut" 
                }
            });
        } catch (e) {
            // Animation stopped
        }

        if (!isFleeing.current) {
            flyRandomly();
        }
    };

    // Flee function
    const flee = async () => {
        isFleeing.current = true;
        controls.stop();

        // Calculate vector away from mouse
        const dx = dragonPos.current.x - mousePos.current.x;
        const dy = dragonPos.current.y - mousePos.current.y;
        
        // Normalize and scale
        const angle = Math.atan2(dy, dx);
        const fleeDistance = 300;
        let targetX = dragonPos.current.x + Math.cos(angle) * fleeDistance;
        let targetY = dragonPos.current.y + Math.sin(angle) * fleeDistance;

        // Bound to screen
        targetX = Math.max(0, Math.min(targetX, dimensions.width - 200));
        targetY = Math.max(0, Math.min(targetY, dimensions.height - 200));

        dragonPos.current = { x: targetX, y: targetY };

        await controls.start({
            x: targetX,
            y: targetY,
            transition: { duration: 0.5, ease: "backOut" } // Fast flee
        });

        isFleeing.current = false;
        flyRandomly(); // Resume normal flight
    };

    flyRandomly();

    return () => clearInterval(interval);
  }, [controls, dimensions]);

  return (
    <div className="fixed inset-0 z-50 pointer-events-none overflow-hidden">
        <motion.div 
            animate={controls}
            className="w-48 h-48 absolute top-0 left-0 opacity-80 drop-shadow-[0_0_15px_rgba(197,160,89,0.5)]"
        >
            <DotLottieReact
                src="https://lottie.host/890e5c87-7cb3-4a14-aa70-800e18649b3e/xGhkHpnGnD.lottie"
                loop
                autoplay
                className="w-full h-full object-contain"
            />
        </motion.div>
    </div>
  );
}
