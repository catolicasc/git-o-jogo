'use client';

import { useGameStore } from '../store/gameStore';
import { GitBranch, ArrowRight, Check } from 'lucide-react';
import { motion } from 'framer-motion';

import { useState } from 'react';
import CodeReviewModal from './CodeReviewModal';

export default function BranchNavigator() {
  const { graph, getCurrentBranchName, checkoutBranch, mergeProposal } = useGameStore();
  const currentBranch = getCurrentBranchName();
  const branches = Object.values(graph.branches);

  const [isReviewOpen, setIsReviewOpen] = useState(false);
  const [mergeTarget, setMergeTarget] = useState<string | null>(null);

  const handleMergeClick = (targetBranch: string) => {
      setMergeTarget(targetBranch);
      setIsReviewOpen(true);
  };

  const confirmMerge = () => {
      if (mergeTarget) {
          mergeProposal(mergeTarget);
      }
      setIsReviewOpen(false);
      setMergeTarget(null);
  };

  return (
    <>
    <div className="bg-[#2c1810]/90 rounded-lg border border-[#8b5a2b] p-4 shadow-xl backdrop-blur-sm">
      <h3 className="text-[#c5a059] font-fantasy text-lg mb-4 text-center border-b border-[#8b5a2b]/30 pb-2 flex items-center justify-center gap-2">
        <GitBranch className="w-5 h-5" />
        Profecias Ativas (Branches)
      </h3>
      
      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
        {branches.map((branch) => {
           const isActive = branch.name === currentBranch;
           const isMain = branch.name === 'main';
           
           // Show merge button if we are NOT on this branch, AND this branch is 'main' (or generic target logic)
           // Simplify: allow merging CURRENT branch INTO this branch (if this branch is not current)
           const canMergeInto = !isActive; 

           return (
             <motion.div
               key={branch.name}
               whileHover={{ scale: 1.02 }}
               className={`p-3 rounded border transition-colors cursor-pointer flex items-center justify-between group ${
                   isActive 
                   ? 'bg-[#c5a059]/20 border-[#c5a059] text-[#c5a059]' 
                   : 'bg-[#1a0f0a]/50 border-[#8b5a2b]/30 text-[#f4e4bc]/70 hover:bg-[#8b5a2b]/20 hover:text-[#f4e4bc]'
               }`}
               onClick={() => !isActive && checkoutBranch(branch.name)}
             >
                <div className="flex items-center gap-2">
                    <span className={`font-mono text-sm ${isActive ? 'font-bold' : ''}`}>
                        {branch.name === 'main' ? 'O Destino (main)' : branch.name}
                    </span>
                    {isActive && <span className="text-[10px] bg-[#c5a059] text-[#2c1810] px-1 rounded font-bold">HEAD</span>}
                </div>
                
                <div className="flex items-center gap-2">
                    {/* Merge Button logic: If I am on a feature branch, and I hover over 'main', show Merge Button? 
                        Or just separate button? 
                        Let's add a small 'Pull Request' button on the branch item 
                    */}
                    {/* Merge Button: Only show if I am NOT on main (can't merge main into others) */}
                    {!isActive && currentBranch !== 'main' && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handleMergeClick(branch.name);
                            }}
                            className="bg-purple-900/50 hover:bg-purple-600 text-purple-200 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                            title={`Fundir (Merge) atual em ${branch.name}`}
                        >
                             <Check className="w-3 h-3" />
                        </button>
                    )}

                    {isActive ? (
                        <Check className="w-4 h-4" />
                    ) : (
                        <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100" />
                    )}
                </div>
             </motion.div>
           );
        })}
      </div>
      
      <div className="mt-4 text-[10px] text-[#f4e4bc]/40 text-center font-mono italic">
          Clique para mudar sua visão. <br/> Botão roxo = Iniciar Merge
      </div>
    </div>

    {/* Code Review Modal */}
    {mergeTarget && (
        <CodeReviewModal 
            targetBranch={mergeTarget}
            isOpen={isReviewOpen}
            onConfirm={confirmMerge}
            onCancel={() => setIsReviewOpen(false)}
        />
    )}
    </>
  );
}
