'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { PenTool, X, Save, FileText } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useGameStore } from '../store/gameStore';

interface Props {
  isOpen: boolean;
  onConfirm: (content: string, message: string) => void;
  onCancel: () => void;
}

export default function CommitModal({ isOpen, onConfirm, onCancel }: Props) {
  const { getStory, getCurrentBranchName } = useGameStore();
  
  const [content, setContent] = useState("");
  const [message, setMessage] = useState("");

  // Load content when opening
  useEffect(() => {
    if (isOpen) {
        setContent(getStory());
        setMessage("");
    }
  }, [isOpen, getStory]);

  if (!isOpen) return null;

  const handleSave = () => {
    if (!content.trim() || !message.trim()) return;
    onConfirm(content, message);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/80 flex items-center justify-center z-[100] p-4 backdrop-blur-sm"
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className="bg-[#2c1810] border-2 border-[#c5a059] rounded-lg w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl relative overflow-hidden"
        >
          {/* Header */}
          <div className="p-6 border-b border-[#c5a059]/30 flex items-center justify-between bg-[url('/parchment-texture.jpg')] bg-cover">
            <div className="absolute inset-0 bg-black/60 pointer-events-none" />
            <div className="relative z-10 flex items-center gap-4">
               <div className="p-3 bg-[#c5a059] rounded-full text-[#2c1810] shadow-[0_0_15px_#c5a059]">
                   <PenTool className="w-6 h-6" />
               </div>
               <div>
                   <h2 className="text-2xl font-fantasy text-[#c5a059] tracking-wide">Escrever Novo Capítulo</h2>
                   <p className="text-[#f4e4bc]/60 text-sm font-mono">
                       Branch atual: <span className="text-[#c5a059] font-bold">git checkout {getCurrentBranchName()}</span>
                   </p>
               </div>
            </div>
            
            <button onClick={onCancel} className="relative z-10 p-2 hover:bg-red-500/20 rounded-full transition-colors text-red-400 group">
                <X className="w-6 h-6 group-hover:scale-110 transition-transform" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-[#1a0f0a]/95">
              
              {/* Editor Area */}
              <div className="space-y-2">
                  <label className="text-[#c5a059] text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Conteúdo da História
                  </label>
                  <textarea 
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full h-96 bg-[#2c1810]/50 border border-[#8b5a2b]/30 rounded p-6 text-[#f4e4bc] font-serif text-lg leading-relaxed focus:outline-none focus:border-[#c5a059] focus:ring-1 focus:ring-[#c5a059] resize-none placeholder-[#8b5a2b]/30 shadow-inner"
                    placeholder="Escreva aqui a continuação da lenda..."
                    autoFocus
                  />
              </div>

              {/* Commit Message Input */}
              <div className="space-y-2">
                  <label className="text-[#c5a059] text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                      <span className="text-green-500 font-mono">$</span>
                      Mensagem do Commit
                  </label>
                  <div className="relative">
                      <input 
                        type="text"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        className="w-full bg-[#000]/30 border border-[#8b5a2b]/30 rounded p-4 pl-12 text-white font-mono text-sm focus:outline-none focus:border-[#c5a059] placeholder-[#8b5a2b]/50"
                        placeholder='git commit -m "Descreva suas alterações..."'
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                                handleSave();
                            }
                        }}
                      />
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#c5a059] font-mono text-xs font-bold">
                          -m
                      </span>
                  </div>
                  <p className="text-[#f4e4bc]/30 text-xs italic text-right">
                      Dica: Use Ctrl+Enter para salvar
                  </p>
              </div>

          </div>

          {/* Footer */}
          <div className="p-6 border-t border-[#c5a059]/30 bg-[#000]/40 flex justify-end gap-4 items-center backdrop-blur-md">
              <button 
                onClick={onCancel}
                className="px-6 py-3 rounded text-[#f4e4bc]/60 hover:text-[#f4e4bc] hover:bg-white/5 transition-colors font-bold uppercase tracking-wider text-xs"
              >
                  Cancelar
              </button>
              
              <button 
                onClick={handleSave}
                disabled={!content.trim() || !message.trim()}
                className="bg-[#c5a059] text-[#2c1810] px-8 py-3 rounded font-bold hover:bg-[#e0b96b] transition-all transform hover:scale-105 shadow-[0_0_20px_rgba(197,160,89,0.3)] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
              >
                  <Save className="w-5 h-5" />
                  Commit Changes
              </button>
          </div>

        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
