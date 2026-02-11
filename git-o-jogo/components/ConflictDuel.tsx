'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../store/gameStore';
import { AlertTriangle, ArrowRight, ArrowLeft, X, Save } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function ConflictDuel() {
  const { socket, addCommand } = useGameStore();
  const [conflictData, setConflictData] = useState<{
      sourceBranch: string, 
      targetBranch: string, 
      baseContent: string, 
      myContent: string 
  } | null>(null);

  const [finalContent, setFinalContent] = useState("");

  useEffect(() => {
    if (!socket) return;
    
    // Listen for conflict event
    socket.on('merge_conflict', (data: { sourceBranch: string; targetBranch: string; baseContent: string; myContent: string }) => {
        setConflictData(data);
        // Initialize with base content? Or empty?
        // Let's initialize with base content as a starting point, or maybe empty to force construction?
        // Let's go with empty to encourage "building" the new truth.
        setFinalContent(""); 
    });

    return () => {
        socket.off('merge_conflict');
    };
  }, [socket]);

  const handleInsert = (text: string) => {
      setFinalContent(prev => {
          const prefix = prev ? prev + "\n" : "";
          return prefix + text;
      });
  };

  const handleResolve = () => {
      if (!conflictData || !socket) return;
      
      const commitMsg = `Merge branch '${conflictData.sourceBranch}' (Manual Resolution)`;
      addCommand(`git merge ${conflictData.targetBranch}`, "Conflito resolvido manualmente no Editor do Destino.");

      // Emit resolved merge
      socket.emit('resolve_conflict', {
           target: conflictData.targetBranch,
           content: finalContent,
           message: commitMsg,
           author: localStorage.getItem('invocadorName') || 'Unknown'
      });

      setConflictData(null);
      setFinalContent("");
  };

  const handleCancel = () => {
      setConflictData(null);
      setFinalContent("");
      // Ideally we should maybe abort the merge? 
      // For now just closing the modal.
  };

  if (!conflictData) return null;

  const theirBlocks = conflictData.baseContent.split('\n').filter(line => line.trim() !== "");
  const myBlocks = conflictData.myContent.split('\n').filter(line => line.trim() !== "");

  return (
    <AnimatePresence>
        <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[110] flex items-center justify-center bg-black/90 backdrop-blur-md p-4"
        >
          <div className="bg-[#1a0f0a] border-2 border-red-500 rounded-lg w-full max-w-7xl h-[90vh] flex flex-col shadow-[0_0_50px_rgba(239,68,68,0.3)] overflow-hidden">
            
            {/* Header */}
            <div className="p-4 border-b border-red-500/30 flex items-center justify-between bg-red-900/10">
                <div className="flex items-center gap-3">
                    <AlertTriangle className="w-8 h-8 text-red-500 animate-pulse" />
                    <div>
                        <h2 className="text-2xl font-fantasy text-red-500">Editor do Destino (Conflict Resolution)</h2>
                        <p className="text-[#f4e4bc]/60 font-mono text-xs">
                            Construa a Nova Verdade combinando as realidades conflitantes.
                        </p>
                    </div>
                </div>
                <button onClick={handleCancel} className="text-red-400 hover:text-red-300">
                    <X className="w-6 h-6" />
                </button>
            </div>

            {/* 3-Column Editor */}
            <div className="flex-1 grid grid-cols-12 divide-x divide-red-500/20 overflow-hidden">
                
                {/* Left: Theirs (Base) */}
                <div className="col-span-3 flex flex-col bg-[#2c1810]/50">
                    <div className="p-2 bg-red-900/20 border-b border-red-500/20 text-center">
                        <h3 className="text-red-400 font-bold font-mono text-sm uppercase">Verdade Atual (Theirs)</h3>
                        <span className="text-[10px] text-[#f4e4bc]/40">{conflictData.targetBranch}</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-2">
                        {theirBlocks.map((block, i) => (
                            <div key={i} className="group relative bg-[#1a0f0a] p-3 rounded border border-red-900/30 hover:border-red-500 transition-colors text-[#f4e4bc]/70 text-sm font-serif">
                                {block}
                                <button 
                                    onClick={() => handleInsert(block)}
                                    className="absolute right-[-12px] top-1/2 -translate-y-1/2 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-lg z-10 hover:scale-110"
                                    title="Inserir na Nova Verdade"
                                >
                                    <ArrowRight className="w-3 h-3" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Center: Result (New Truth) */}
                <div className="col-span-6 flex flex-col bg-[#1a0f0a]">
                    <div className="p-2 bg-[#c5a059]/10 border-b border-[#c5a059]/20 text-center">
                        <h3 className="text-[#c5a059] font-bold font-mono text-sm uppercase">Nova Verdade (Result)</h3>
                        <span className="text-[10px] text-[#f4e4bc]/40">Edite livremente o resultado final</span>
                    </div>
                    <div className="flex-1 p-4">
                        <textarea 
                            value={finalContent}
                            onChange={(e) => setFinalContent(e.target.value)}
                            className="w-full h-full bg-[#2c1810] border border-[#8b5a2b]/30 rounded p-4 text-[#f4e4bc] font-serif text-lg leading-relaxed focus:outline-none focus:border-[#c5a059] resize-none placeholder-[#8b5a2b]/30"
                            placeholder="Selecione blocos das laterais ou escreva aqui..."
                        />
                    </div>
                </div>

                {/* Right: Ours (My Version) */}
                <div className="col-span-3 flex flex-col bg-[#2c1810]/50">
                    <div className="p-2 bg-green-900/20 border-b border-green-500/20 text-center">
                        <h3 className="text-green-400 font-bold font-mono text-sm uppercase">Sua Versão (Ours)</h3>
                        <span className="text-[10px] text-[#f4e4bc]/40">{conflictData.sourceBranch}</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-2">
                        {myBlocks.map((block, i) => (
                            <div key={i} className="group relative bg-[#1a0f0a] p-3 rounded border border-green-900/30 hover:border-green-500 transition-colors text-[#f4e4bc]/70 text-sm font-serif">
                                {block}
                                <button 
                                    onClick={() => handleInsert(block)}
                                    className="absolute left-[-12px] top-1/2 -translate-y-1/2 bg-green-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity shadow-lg z-10 hover:scale-110"
                                    title="Inserir na Nova Verdade"
                                >
                                    <ArrowLeft className="w-3 h-3" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

            </div>

            {/* Footer Actions */}
            <div className="p-4 border-t border-red-500/30 bg-[#1a0f0a] flex justify-between items-center">
                <div className="text-xs text-[#f4e4bc]/40 font-mono">
                    {finalContent.length} caracteres | {finalContent.split('\n').length} parágrafos
                </div>
                <div className="flex gap-3">
                    <button 
                        onClick={handleCancel}
                        className="px-6 py-2 rounded text-red-400 hover:text-red-300 hover:bg-red-900/20 transition-colors uppercase font-bold text-xs tracking-wider"
                    >
                        Cancelar
                    </button>
                    <button 
                        onClick={handleResolve}
                        disabled={!finalContent.trim()}
                        className="px-8 py-2 bg-[#c5a059] disabled:opacity-50 disabled:cursor-not-allowed text-[#2c1810] font-bold rounded shadow-[0_0_15px_rgba(197,160,89,0.3)] hover:bg-[#d4b06a] hover:shadow-[0_0_25px_rgba(197,160,89,0.5)] transition-all flex items-center gap-2"
                    >
                        <Save className="w-4 h-4" />
                        Selar o Destino (Confirm Merge)
                    </button>
                </div>
            </div>

          </div>
        </motion.div>
    </AnimatePresence>
  );
}
