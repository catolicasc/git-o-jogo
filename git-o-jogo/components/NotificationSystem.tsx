'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../store/gameStore';
import { X, Scroll, AlertCircle, Info } from 'lucide-react';
import { useEffect } from 'react';

export default function NotificationSystem() {
  const { notifications, removeNotification } = useGameStore();

  return (
    <div className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {notifications.map((note) => (
          <motion.div
            key={note.id}
            initial={{ opacity: 0, x: 50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.9 }}
            className="pointer-events-auto"
          >
             <div className={`
                relative min-w-[300px] max-w-md p-4 rounded-lg shadow-2xl border-l-4 
                ${note.type === 'error' ? 'bg-[#2c0b0e] border-red-600 text-red-100' : 'bg-[#1a130c] border-[#c5a059] text-[#f4e4bc]'}
                overflow-hidden
             `}>
                {/* Background Texture */}
                <div className="absolute inset-0 bg-[url('/parchment-texture.jpg')] opacity-10 mix-blend-overlay pointer-events-none" />
                
                <div className="relative flex items-start gap-3">
                    <div className={`
                        p-2 rounded-full shrink-0
                        ${note.type === 'error' ? 'bg-red-900/50 text-red-500' : 'bg-[#c5a059]/20 text-[#c5a059]'}
                    `}>
                        {note.type === 'error' ? <AlertCircle className="w-5 h-5" /> : <Scroll className="w-5 h-5" />}
                    </div>

                    <div className="flex-1 pt-0.5">
                        <h4 className={`font-fantasy text-sm font-bold mb-1 tracking-wide uppercase ${note.type === 'error' ? 'text-red-400' : 'text-[#c5a059]'}`}>
                            {note.type === 'error' ? 'Erro no Ritual' : 'Mensagem do Corvo'}
                        </h4>
                        <p className="font-serif text-sm leading-relaxed opacity-90">
                            {note.message}
                        </p>
                    </div>

                    <button 
                        onClick={() => removeNotification(note.id)}
                        className="text-white/20 hover:text-white transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
                
                {/* Progress Bar for Auto-dismiss */}
                <motion.div 
                    initial={{ width: "100%" }}
                    animate={{ width: "0%" }}
                    transition={{ duration: 5, ease: "linear" }}
                    className={`absolute bottom-0 left-0 h-1 ${note.type === 'error' ? 'bg-red-600/50' : 'bg-[#c5a059]/50'}`}
                />
             </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
