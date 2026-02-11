'use client';

import { useState } from 'react';
import { useGameStore } from '../store/gameStore';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, Sparkles } from 'lucide-react';

export default function VisionCreator() {
  const { createBranch, getCurrentBranchName } = useGameStore();
  // const currentBranch = getCurrentBranchName(); // Not currently displayed but available
  const [isOpen, setIsOpen] = useState(false);
  const [branchName, setBranchName] = useState('');

  const handleCreate = () => {
    if (!branchName.trim()) return;
    createBranch(branchName);
    setBranchName('');
    setIsOpen(false);
  };

  return (
    <div className="fixed bottom-56 right-8 z-50">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="absolute bottom-16 right-0 bg-[#2c1810] p-6 rounded-lg text-[#f4e4bc] w-80 shadow-2xl border border-[#c5a059]"
          >
            <h3 className="text-xl font-fantasy text-[#c5a059] mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5" />
              Tecer Nova Profecia
            </h3>
            <p className="text-sm text-[#f4e4bc]/80 mb-4">
              Criar uma nova profecia permite explorar uma linha do tempo alternativa sem afetar a história principal.
            </p>
            <input
              type="text"
              value={branchName}
              onChange={(e) => setBranchName(e.target.value)}
              placeholder="Nome da Profecia (Branch)..."
              className="w-full bg-[#1a0f0a] border border-[#8b5a2b] rounded px-3 py-2 text-[#f4e4bc] focus:outline-none focus:border-[#c5a059] mb-4"
            />
            <button
              onClick={handleCreate}
              className="w-full bg-[#c5a059] text-[#2c1810] font-bold py-2 rounded hover:bg-[#d4b06a] transition-colors shadow-md"
            >
              Iniciar Profecia
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-col gap-4 items-end">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsOpen(!isOpen)}
            className={`w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-colors ${
            isOpen ? 'bg-[#c5a059] text-[#2c1810]' : 'bg-[#2c1810] text-[#c5a059] border-2 border-[#c5a059]'
            }`}
          >
            <GitBranch className="w-8 h-8" />
          </motion.button>
      </div>
    </div>
  );
}
