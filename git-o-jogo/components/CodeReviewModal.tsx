'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { GitPullRequest, Check, X, ArrowRight } from 'lucide-react';
import { useGameStore } from '../store/gameStore';

interface Props {
  targetBranch: string;
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function CodeReviewModal({ targetBranch, isOpen, onConfirm, onCancel }: Props) {
  const { graph, getCurrentBranchName, getStory } = useGameStore();

  if (!isOpen) return null;

  const currentBranchName = getCurrentBranchName();
  const currentBranch = graph.branches[currentBranchName];
  const target = graph.branches[targetBranch];

  if (!currentBranch || !target) return null;

  // Simple diff logic: 
  // Get content of current branch head
  // Get content of target branch head
  // Show side-by-side or simple diff
  
  const myContent = graph.commits[currentBranch.headCommitId]?.content || "";
  const targetContent = graph.commits[target.headCommitId]?.content || "";

  // Verify if it's the exact same content
  const isIdentical = myContent === targetContent;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/80 flex items-center justify-center z-[90] p-8"
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className="bg-[#2c1810] border-2 border-[#c5a059] rounded-lg w-full max-w-6xl h-[85vh] flex flex-col shadow-2xl relative overflow-hidden"
        >
          {/* Header */}
          <div className="p-6 border-b border-[#c5a059]/30 flex items-center justify-between bg-[url('/parchment-texture.jpg')] bg-cover">
            <div className="absolute inset-0 bg-black/60 pointer-events-none" />
            <div className="relative z-10 flex items-center gap-4">
               <div className="p-3 bg-[#c5a059] rounded-full text-[#2c1810]">
                   <GitPullRequest className="w-6 h-6" />
               </div>
               <div>
                   <h2 className="text-2xl font-fantasy text-[#c5a059]">Ritual de Revisão (Code Review)</h2>
                   <p className="text-[#f4e4bc]/60 text-sm">
                       Você está prestes a fundir 
                       <span className="text-[#c5a059] font-bold mx-1">{currentBranchName}</span> 
                       na verdade absoluta 
                       <span className="text-[#c5a059] font-bold mx-1">{targetBranch === 'main' ? 'O Destino (main)' : targetBranch}</span>.
                   </p>
               </div>
            </div>
            
            <button onClick={onCancel} className="relative z-10 p-2 hover:bg-red-500/20 rounded-full transition-colors text-red-400">
                <X className="w-6 h-6" />
            </button>
          </div>

          {/* Diffs Container */}
          <div className="flex-1 flex overflow-hidden">
             {/* Target (Left) */}
             <div className="flex-1 p-6 border-r border-[#c5a059]/30 bg-[#1a0f0a]/80 overflow-y-auto">
                 <h3 className="flex items-center gap-2 text-[#f4e4bc]/50 mb-4 font-mono text-xs uppercase tracking-widest sticky top-0 bg-[#1a0f0a] py-2">
                     <span className="w-2 h-2 rounded-full bg-blue-500" />
                     {targetBranch === 'main' ? 'O Destino (main)' : targetBranch} (Destino)
                 </h3>
                 <div className="whitespace-pre-wrap font-serif text-[#f4e4bc]/60 leading-relaxed text-justify opacity-70">
                     {targetContent}
                 </div>
             </div>

             {/* Arrow Center */}
             <div className="w-12 bg-[#2c1810] flex items-center justify-center flex-col gap-4 border-x border-[#c5a059]/30">
                 <motion.div 
                    animate={{ x: [0, 5, 0] }}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                 >
                     <ArrowRight className="w-6 h-6 text-[#c5a059]" />
                 </motion.div>
             </div>

             {/* Source (Right) */}
             <div className="flex-1 p-6 bg-[#2c1810] overflow-y-auto">
                 <h3 className="flex items-center gap-2 text-[#c5a059] mb-4 font-mono text-xs uppercase tracking-widest sticky top-0 bg-[#2c1810] py-2">
                     <span className="w-2 h-2 rounded-full bg-green-500" />
                     {currentBranchName} (Sua Versão)
                 </h3>
                 <div className="whitespace-pre-wrap font-serif text-[#f4e4bc] leading-relaxed text-justify">
                     {myContent}
                 </div>
             </div>
          </div>

          {/* Warnings */}
          {isIdentical && (
              <div className="bg-yellow-900/50 p-2 text-center text-yellow-500 text-xs border-y border-yellow-700/30">
                  ⚠️ Atenção: Nenhuma alteração detectada. O merge não terá efeito prático.
              </div>
          )}

          {/* Footer Actions */}
          <div className="p-6 border-t border-[#c5a059]/30 bg-[#1a0f0a] flex justify-end gap-4 items-center">
              <span className="text-xs text-[#f4e4bc]/40 mr-auto max-w-md">
                  Ao aprovar, a profecia "{currentBranchName}" será consumida e deixará de existir, tornando-se parte de "{targetBranch}".
              </span>
              
              <button 
                onClick={onCancel}
                className="px-6 py-3 rounded text-[#f4e4bc]/60 hover:text-[#f4e4bc] hover:bg-white/5 transition-colors font-bold uppercase tracking-wider text-xs"
              >
                  Cancelar
              </button>
              
              <button 
                onClick={onConfirm}
                className="bg-[#22c55e] text-[#052e16] px-8 py-3 rounded font-bold hover:bg-[#4ade80] transition-all transform hover:scale-105 shadow-[0_0_20px_rgba(34,197,94,0.4)] flex items-center gap-2 group"
              >
                  <Check className="w-5 h-5 group-hover:scale-110 transition-transform" />
                  Aprovar & Merge
              </button>
          </div>

        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
