'use client';

import React, { useEffect } from 'react';
import { DotLottieReact } from '@lottiefiles/dotlottie-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../store/gameStore';

export default function MergeHandAnimation() {
  const { showMergeAnimation, setMergeAnimation } = useGameStore();

  useEffect(() => {
    if (showMergeAnimation) {
      // Auto hide after animation duration (approx 3-4s usually, let's say 4s)
      const timer = setTimeout(() => {
        setMergeAnimation(false);
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [showMergeAnimation, setMergeAnimation]);

  return (
    <AnimatePresence>
      {showMergeAnimation && (
        <motion.div
          initial={{ opacity: 0, scale: 0.5, y: 100 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.5, y: 100 }}
          className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none"
        >
           <div className="w-[500px] h-[500px] drop-shadow-2xl">
             <DotLottieReact
               src="https://lottie.host/ca5b728e-ce7c-4507-a9de-37bd411fc5fc/Rl6pB0QcKm.lottie"
               loop={false}
               autoplay
             />
           </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
