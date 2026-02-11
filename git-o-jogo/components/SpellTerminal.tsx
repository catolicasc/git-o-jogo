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
    <div className="w-full h-full bg-[#0a0505] flex flex-col font-mono text-xs">
      {/* Terminal Title Bar */}
      <div className="flex items-center gap-2 px-6 py-2 bg-[var(--color-panel)] border-b border-[var(--color-panel-border)]">
        <Terminal className="w-3 h-3 text-[var(--color-gold)]" />
        <span className="text-[var(--color-gold)] font-bold uppercase tracking-wider text-[10px]">Grimório de Comandos (Git Log)</span>
        <div className="ml-auto flex gap-2">
            <div className="w-2 h-2 rounded-full bg-[var(--color-panel-border)]" />
            <div className="w-2 h-2 rounded-full bg-[var(--color-panel-border)]" />
        </div>
      </div>
      
      {/* Terminal Content */}
      <div ref={scrollRef} className="flex-1 p-4 overflow-y-auto space-y-1.5 scrollbar-thin scrollbar-thumb-[var(--color-panel-border)] scrollbar-track-transparent">
        <AnimatePresence initial={false}>
            {commandLog.map((log) => (
            <motion.div
                key={log.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex flex-col gap-0.5"
            >
                <div className="flex items-baseline gap-3 group">
                    <span className="text-[var(--color-text-muted)] opacity-30 select-none w-16 text-right">
                        {new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                    </span>
                    <div className="flex-1 flex gap-2">
                        <span className="text-[var(--color-accent-green)] select-none">$</span>
                        <span className="text-[var(--color-text-main)] font-medium tracking-wide">{log.command}</span>
                    </div>
                </div>
                {log.description && (
                    <div className="text-[var(--color-text-muted)]/50 pl-24 italic text-[10px]">
                        # {log.description}
                    </div>
                )}
            </motion.div>
            ))}
        </AnimatePresence>
        {commandLog.length === 0 && (
            <div className="text-[var(--color-text-muted)]/20 italic text-center mt-10">
                Aguardando conjuração...
            </div>
        )}
      </div>
    </div>
  );
}
