'use client';

import { useGameStore } from '../store/gameStore';
import { GitBranch, Check } from 'lucide-react';
import { motion } from 'framer-motion';

export default function BranchNavigator() {
  const { graph, getCurrentBranchName, checkoutBranch, openReviewModal } = useGameStore();
  const currentBranch = getCurrentBranchName();
  // Only show active branches
  const branches = Object.values(graph.branches).filter(b => b.status !== 'merged');

  const handleMergeClick = (targetBranch: string) => {
      openReviewModal(targetBranch);
  };

  return (
    <>
    <div className="bg-[var(--color-bg-main)]/50 rounded-sm border border-[var(--color-panel-border)] p-2">
      
      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-[var(--color-gold-dim)] scrollbar-track-transparent">
        {branches.map((branch) => {
           const isActive = branch.name === currentBranch;
           
           return (
             <motion.div
               key={branch.name}
               whileHover={{ x: 4 }}
               className={`p-3 rounded-sm border transition-all cursor-pointer flex items-center justify-between group ${
                   isActive 
                   ? 'bg-[var(--color-gold)]/10 border-[var(--color-gold)] text-[var(--color-gold)] shadow-[0_0_10px_rgba(197,160,89,0.1)]' 
                   : 'bg-transparent border-transparent hover:border-[var(--color-panel-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'
               }`}
               onClick={() => !isActive && checkoutBranch(branch.name)}
             >
                <div className="flex items-center gap-3">
                    <GitBranch className={`w-4 h-4 ${isActive ? 'fill-[var(--color-gold)]/20' : ''}`} />
                    <span className={`font-mono text-sm ${isActive ? 'font-bold' : ''}`}>
                        {branch.name === 'main' ? 'O Destino (main)' : branch.name}
                    </span>
                    {isActive && <span className="text-[9px] border border-[var(--color-gold)] text-[var(--color-gold)] px-1 rounded uppercase tracking-wider">HEAD</span>}
                </div>
                
                <div className="flex items-center gap-2">
                    {!isActive && currentBranch !== 'main' && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handleMergeClick(branch.name);
                            }}
                            className="bg-[var(--color-accent-green)]/10 hover:bg-[var(--color-accent-green)]/20 text-[var(--color-accent-green)] p-1.5 rounded opacity-0 group-hover:opacity-100 transition-opacity border border-[var(--color-accent-green)]/30"
                            title={`Fundir (Merge) atual em ${branch.name}`}
                        >
                             <Check className="w-3 h-3" />
                        </button>
                    )}

                    {isActive && (
                        <div className="w-2 h-2 rounded-full bg-[var(--color-gold)] shadow-[0_0_5px_var(--color-gold)]" />
                    )}
                </div>
             </motion.div>
           );
        })}
      </div>
      
      <div className="mt-4 text-[10px] text-[var(--color-text-muted)] text-center font-mono opacity-50">
          Clique para mudar sua visão.
      </div>
    </div>

    </>
  );
}
