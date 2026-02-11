'use client';

import { motion } from "framer-motion";
import { useGameStore } from "../store/gameStore";
import { useEffect } from "react";

export default function StoryBook() {
  const { connect, isConnected, getStory } = useGameStore();
  const story = getStory();

  useEffect(() => {
    connect();
  }, [connect]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] p-8">
      <motion.div
        initial={{ opacity: 0, scale: 0.9, rotateX: 20 }}
        animate={{ opacity: 1, scale: 1, rotateX: 0 }}
        transition={{ duration: 0.8, type: "spring" }}
        className="relative bg-[#fdf6e3] text-[#2c1810] p-12 rounded-lg shadow-2xl max-w-4xl w-full border-8 border-[#8b5a2b] shadow-[#000000a0]"
        style={{
            backgroundImage: "url('/parchment-texture.jpg')", // Ensure this asset exists or is placeholder
            boxShadow: "0 20px 50px rgba(0,0,0,0.5), inset 0 0 60px rgba(139, 90, 43, 0.3)"
        }}
      >
        {/* Book Header */}
        <div className="absolute top-0 left-0 w-full h-12 bg-gradient-to-b from-[#00000010] to-transparent pointer-events-none" />
        
        <h2 className="text-4xl font-bold mb-8 text-center text-fantasy text-[#8b5a2b] drop-shadow-sm border-b-2 border-[#8b5a2b]/30 pb-4">
            As Crônicas de Aetheria
        </h2>

        {/* Status Indicator */}
        <div className="absolute top-4 right-4 flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${isConnected ? "bg-green-500 shadow-[0_0_10px_#22c55e]" : "bg-red-500"}`} />
            <span className="text-xs text-[#8b5a2b]/70 font-mono uppercase tracking-widest">{isConnected ? "Conectado" : "Desconectado"}</span>
        </div>

        {/* Story Content */}
        <div className="story-content text-lg leading-relaxed text-fantasy font-serif text-justify min-h-[300px]">
          {story.split('\n').map((paragraph, index) => {
             // Mocking "Blame" - in a real app we would map line numbers to commits.
             // Here we just alternate or use a hash of the content to pick an author "color/name" simulation
             // if we don't have granular metadata.
             // BUT, we can try to improve this by inspecting the commit history? 
             // Too complex for now, let's just make it look like it.
             
             return (
             <div key={index} className="group relative hover:bg-[#8b5a2b]/10 p-2 rounded transition-colors -mx-2">
                 {/* Blame Gutter */}
                 <div className="absolute left-[-120px] top-2 w-[110px] text-[10px] text-right text-[#8b5a2b]/60 opacity-0 group-hover:opacity-100 transition-opacity font-mono hidden md:block border-r border-[#8b5a2b]/30 pr-2">
                    <span className="font-bold block text-[#c5a059]">Git Blame</span>
                     {/* Deterministic mock blame based on paragraph length/index */}
                     {index === 0 ? "Initial Commit" : `Commit ${((index * 999) % 0xFFFFFF).toString(16).padEnd(6, '0')}`}
                 </div>
                 
                 <motion.p 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.2 }}
                    className="mb-4 first-letter:text-5xl first-letter:font-bold first-letter:text-[#8b5a2b] first-letter:mr-2 first-letter:float-left"
                 >
                    {paragraph}
                 </motion.p>
             </div>
             );
          })}
        </div>

        {/* Edit / Commit Controls */}
        <div className="absolute bottom-4 right-4 flex gap-2">
            <button 
                onClick={() => useGameStore.getState().openCommitModal()}
                className="bg-[#c5a059] text-[#2c1810] px-4 py-2 rounded font-bold hover:bg-[#d4b06a] transition-all shadow-md flex items-center gap-2 hover:scale-105 active:scale-95"
            >
                <div className="w-2 h-2 rounded-full bg-[#2c1810] animate-pulse" />
                Escrever (Commit)
            </button>
        </div>

        {/* Book Footer */}
        <div className="mt-8 pt-4 border-t-2 border-[#8b5a2b]/30 text-center text-sm text-[#8b5a2b]/60 italic font-fantasy">
            Página {Math.floor(story.length / 500) + 1}
        </div>
      </motion.div>
    </div>
  );
}
