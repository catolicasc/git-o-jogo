'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../store/gameStore';
import { AlertTriangle, GitMerge } from 'lucide-react';
import { useState, useEffect } from 'react';

// We need to add conflict state to the store first, but for now assuming it's passed or local
// Actually, let's make it subscribing to the store event listener? 
// Better: Store handles the event and sets "conflictState".

export default function ConflictDuel() {
  const { socket, addCommand } = useGameStore();
  const [conflictData, setConflictData] = useState<{
      sourceBranch: string, 
      targetBranch: string, 
      baseContent: string, 
      myContent: string 
  } | null>(null);

  useEffect(() => {
    if (!socket) return;
    
    // Listen for conflict event
    socket.on('merge_conflict', (data: any) => {
        setConflictData(data);
    });

    return () => {
        socket.off('merge_conflict');
    };
  }, [socket]);

  const handleResolve = (resolution: 'mine' | 'theirs' | 'union') => {
      if (!conflictData || !socket) return;
      
      let finalContent = "";
      let commitMsg = "";

      if (resolution === 'mine') {
          finalContent = conflictData.myContent;
          commitMsg = `Merge branch '${conflictData.sourceBranch}' (JPA Strategy: Ours)`;
          addCommand(`git merge -s ours ${conflictData.targetBranch}`, "Resolvendo conflito mantendo nossa versão.");
      } else if (resolution === 'theirs') {
          finalContent = conflictData.baseContent;
          commitMsg = `Merge branch '${conflictData.sourceBranch}' (JPA Strategy: Theirs)`;
          addCommand(`git merge -s theirs ${conflictData.targetBranch}`, "Aceitando a verdade existente (descartando mudanças).");
      } else {
          finalContent = conflictData.baseContent + "\n\n" + conflictData.myContent;
          commitMsg = `Merge branch '${conflictData.sourceBranch}' (Union)`;
          addCommand(`git merge ${conflictData.targetBranch}`, "Fundindo ambas as histórias manualmente.");
      }

      // Emit resolved merge
      // We need a specific event for this force merge
      socket.emit('resolve_conflict', {
           target: conflictData.targetBranch,
           content: finalContent,
           message: commitMsg,
           author: localStorage.getItem('invocadorName') || 'Unknown'
      });

      setConflictData(null);
  };

  return (
    <AnimatePresence>
      {conflictData && (
        <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm"
        >
          <div className="bg-[#2c1810] border-4 border-red-500 rounded-lg p-8 max-w-4xl w-full shadow-[0_0_50px_rgba(239,68,68,0.5)]">
            <div className="flex items-center gap-4 mb-6 border-b border-red-500/30 pb-4">
                <AlertTriangle className="w-10 h-10 text-red-500 animate-pulse" />
                <div>
                    <h2 className="text-3xl font-fantasy text-red-500">Duelo de Narrativas (Merge Conflict)</h2>
                    <p className="text-[#f4e4bc]/60 font-mono text-sm">
                        ERRO: A verdade mudou enquanto você escrevia. Git não pode mesclar automaticamente.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-2 gap-8 mb-8">
                <div className="bg-red-900/20 p-4 rounded border border-red-500/50">
                    <h3 className="text-red-400 font-bold mb-2 font-mono">HEAD (Verdade Atual)</h3>
                    <div className="text-[#f4e4bc] text-sm h-48 overflow-y-auto font-serif">
                        {conflictData.baseContent}
                    </div>
                </div>
                <div className="bg-green-900/20 p-4 rounded border border-green-500/50">
                    <h3 className="text-green-400 font-bold mb-2 font-mono">{conflictData.sourceBranch} (Sua Versão)</h3>
                    <div className="text-[#f4e4bc] text-sm h-48 overflow-y-auto font-serif">
                        {conflictData.myContent}
                    </div>
                </div>
            </div>

            <div className="flex justify-center gap-4">
                <button
                    onClick={() => handleResolve('theirs')}
                    className="px-6 py-3 bg-red-900/50 border border-red-500 text-red-200 rounded hover:bg-red-800 transition-colors"
                >
                    Aceitar Verdade Atual (Descartar meu)
                </button>
                <button
                    onClick={() => handleResolve('union')}
                    className="px-6 py-3 bg-[#c5a059] text-black font-bold rounded shadow-lg hover:bg-[#d4b06a] transition-colors flex items-center gap-2"
                >
                    <GitMerge className="w-5 h-5" />
                    Combinar Ambos
                </button>
                <button
                    onClick={() => handleResolve('mine')}
                    className="px-6 py-3 bg-green-900/50 border border-green-500 text-green-200 rounded hover:bg-green-800 transition-colors"
                >
                    Impor Minha Verdade (Sobrescrever)
                </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
