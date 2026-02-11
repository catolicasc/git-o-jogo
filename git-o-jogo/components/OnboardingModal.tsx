'use client';

import { useState, useEffect } from 'react';
import { useGameStore } from '../store/gameStore';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export default function OnboardingModal() {
  const { setPlayerName, playerId } = useGameStore();
  const [name, setName] = useState('');
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    // Check if name is already stored
    const storedName = localStorage.getItem('invocadorName');
    if (storedName) {
        setPlayerName(storedName);
        // setIsVisible(false); // Removed to avoid sync state update warning, handle visibility via state init or layout effect if needed. 
        // Better yet, just don't show it if we have a name.
        setIsVisible(false); 
    }
  }, [setPlayerName]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    localStorage.setItem('invocadorName', name);
    setPlayerName(name);
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center bg-[#000000e0] backdrop-blur-md"
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          className="bg-[#2c1810] border-2 border-[#c5a059] p-8 rounded-lg max-w-md w-full shadow-2xl relative overflow-hidden"
        >
          {/* Decorative Elements */}
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-transparent via-[#c5a059] to-transparent" />
          
          <div className="text-center mb-8">
            <Sparkles className="w-12 h-12 text-[#c5a059] mx-auto mb-4 animate-pulse" />
            <h2 className="text-3xl font-fantasy text-[#f4e4bc] mb-2">Bem-vindo a Aetheria</h2>
            <p className="text-[#f4e4bc]/60 text-sm">Antes de moldar o destino, revele sua identidade.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="invocador" className="block text-[#c5a059] text-sm font-bold mb-2 uppercase tracking-wide">
                Nome de Invocador
              </label>
              <input
                id="invocador"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-[#1a0f0a] border border-[#8b5a2b] rounded px-4 py-3 text-[#f4e4bc] focus:outline-none focus:border-[#c5a059] text-lg text-center font-fantasy placeholder-[#8b5a2b]/50"
                placeholder="Ex: Gandalf, o Cinzento"
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={!name.trim()}
              className="w-full bg-[#c5a059] text-[#2c1810] font-bold py-3 rounded hover:bg-[#d4b06a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-lg border-b-4 border-[#8b5a2b]"
            >
              Entrar no Reino
            </button>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
