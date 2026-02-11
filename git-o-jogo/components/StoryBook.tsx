'use client';

import { motion } from "framer-motion";
import { useGameStore } from "../store/gameStore";
import { useEffect } from "react";

export default function StoryBook() {
  const { connect, isConnected, getStory, getBlame } = useGameStore();
  const story = getStory();

  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <div className="w-full h-full text-[var(--color-text-main)] font-body">
        {/* Connection Pulse */}
        <div className="flex justify-center mb-6">
            <div className={`px-3 py-1 rounded-full border border-[var(--color-panel-border)] text-[10px] uppercase tracking-widest flex items-center gap-2 ${isConnected ? "bg-[var(--color-accent-green)]/10 text-[var(--color-accent-green)]" : "bg-[var(--color-accent-red)]/10 text-[var(--color-accent-red)]"}`}>
                <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-[var(--color-accent-green)] animate-pulse" : "bg-[var(--color-accent-red)]"}`} />
                {isConnected ? "Conectado à Trama" : "Desconectado da Trama"}
            </div>
        </div>

        {/* Story Content */}
        <div className="space-y-6 text-lg leading-loose text-justify px-4">
          {getBlame().map((lineInfo, index) => {
             if (!lineInfo.content.trim()) return null;
             
             return (
             <motion.div 
                key={`${lineInfo.commitId}-${index}`} 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="group relative hover:bg-[var(--color-panel)]/50 p-4 rounded-lg transition-colors border-l-2 border-transparent hover:border-[var(--color-gold-dim)]"
             >
                 {/* Blame Gutter (Visible on Hover) */}
                 <div className="absolute right-2 top-2 p-3 rounded bg-[var(--color-bg-main)] border border-[var(--color-panel-border)] shadow-xl z-10 opacity-0 group-hover:opacity-100 transition-opacity font-mono text-xs pointer-events-none w-64">
                    <div className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-1">
                        <span className="text-[var(--color-gold-dim)] font-bold text-right">Invocador:</span>
                        <span className="text-[var(--color-text-main)] truncate">{lineInfo.author}</span>
                        
                        <span className="text-[var(--color-gold-dim)] font-bold text-right">Data:</span>
                        <span className="text-[var(--color-text-muted)]">
                            {new Date(lineInfo.timestamp).toLocaleString('pt-BR', {day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit'})}
                        </span>
                        
                        <span className="text-[var(--color-gold-dim)] font-bold text-right">HashId:</span>
                        <span className="text-[var(--color-text-muted)] font-mono text-[10px]">{lineInfo.commitId}</span>
                    </div>
                 </div>
                 
                 <p className="first-letter:text-3xl first-letter:font-fantasy first-letter:text-[var(--color-gold)] first-letter:mr-1 first-letter:float-left text-[var(--color-text-main)]">
                    {lineInfo.content}
                 </p>
             </motion.div>
             );
          })}
          
          {story.length === 0 && (
              <div className="text-center text-[var(--color-text-muted)] italic mt-20">
                  O livro está vazio... aguardando o primeiro commit do Criador.
              </div>
          )}
        </div>

        {/* Manual Footer/Pagination Sim */}
        <div className="mt-12 text-center text-[10px] text-[var(--color-text-muted)] font-mono uppercase tracking-widest opacity-50 pb-8">
            - Fim do Registro Atual -
        </div>
    </div>
  );
}
