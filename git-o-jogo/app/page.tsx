'use client';

import StoryBook from "../components/StoryBook";
import VisionCreator from "../components/VisionCreator";
import TreeOfWorlds from "../components/TreeOfWorlds";
import OnboardingModal from "../components/OnboardingModal";
import SpellTerminal from "../components/SpellTerminal";
import ConflictDuel from "../components/ConflictDuel";
import BranchNavigator from "../components/BranchNavigator";
import { useGameStore } from "../store/gameStore";
import { useEffect } from "react";
import { v4 as uuidv4 } from 'uuid';

export default function Home() {
  const { connect, playerId } = useGameStore();

  useEffect(() => {
    // Generate a temporary user ID
    const userId = localStorage.getItem("userId") || uuidv4();
    localStorage.setItem("userId", userId);
    
    // Connect to game
    connect();
  }, [connect]);

  return (
    <main className="min-h-screen relative overflow-hidden flex flex-col items-center pt-20 pb-48 font-fantasy">
      
      {/* Background Elements */}
      <div className="absolute inset-0 bg-[#2c1810]" />
      <div className="absolute inset-0 bg-[url('/magic-particles.png')] opacity-20 animate-pulse pointer-events-none" />

      {/* Overlays */}
      <OnboardingModal />
      <ConflictDuel />

      {/* Connection Status Indicator */}
      {playerId && (
          <div className="absolute top-4 left-8 text-[#c5a059] text-sm opacity-50 z-10">
              Invocador: {playerId.substring(0,8)}...
          </div>
      )}

      <h1 className="text-6xl font-fantasy text-[#4a1c40] mb-8 drop-shadow-lg z-10">
        As Crônicas de Aetheria
      </h1>

      <div className="flex w-full max-w-7xl mx-auto px-4 gap-8">
        
        {/* Left Panel: Git Graph Visualization */}
        <div className="hidden lg:block w-1/4">
            <TreeOfWorlds />
        </div>

        {/* Center Panel: The Main Story */}
        <div className="flex-1 z-10">
            <StoryBook />
        </div>

        {/* Right Panel: Branch Navigation */}
        <div className="hidden lg:block w-1/4">
             <BranchNavigator />
        </div>
      
      </div>

      {/* Floating Action Button for Branching */}
      <VisionCreator />

      {/* Git Command Terminal */}
      <SpellTerminal />
      
    </main>
  );
}
