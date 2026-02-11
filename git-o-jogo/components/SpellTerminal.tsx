'use client';

import { useGameStore } from '../store/gameStore';
import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

export default function SpellTerminal() {
  const { commandLog } = useGameStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [commandLog]);

  return (
    <div className="fixed bottom-0 left-0 w-full h-48 bg-[#1a0f0a]/95 border-t-2 border-[#c5a059] font-mono text-xs z-40 shadow-[0_-5px_20px_rgba(0,0,0,0.8)] backdrop-blur">
      <div className="flex items-center gap-2 px-4 py-2 bg-[#2c1810] border-b border-[#8b5a2b]/30">
        <Terminal className="w-4 h-4 text-[#c5a059]" />
        <span className="text-[#c5a059] font-bold uppercase tracking-wider">Grimório de Comandos (Git Log)</span>
      </div>
      
      <div ref={scrollRef} className="p-4 h-[calc(100%-40px)] overflow-y-auto space-y-2">
        <AnimatePresence initial={false}>
            {commandLog.map((log) => (
            <motion.div
                key={log.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex flex-col gap-1"
            >
                <div className="flex items-baseline gap-2">
                    <span className="text-[#8b5a2b] opacity-50">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                    <span className="text-green-500 font-bold">$ {log.command}</span>
                </div>
                {log.description && (
                    <div className="text-[#f4e4bc]/70 pl-20 italic border-l-2 border-[#8b5a2b]/30 ml-2">
                        # {log.description}
                    </div>
                )}
            </motion.div>
            ))}
        </AnimatePresence>
        {commandLog.length === 0 && (
            <div className="text-[#8b5a2b]/40 italic text-center mt-10">
                Aguardando conjuração de comandos...
            </div>
        )}
      </div>
    </div>
  );
}
