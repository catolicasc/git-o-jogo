'use client';

import StoryBook from "../components/StoryBook";
import VisionCreator from "../components/VisionCreator";
import TreeOfWorlds from '@/components/TreeOfWorlds';
import OnboardingModal from "../components/OnboardingModal";
import SpellTerminal from '@/components/SpellTerminal';
import ConflictDuel from "../components/ConflictDuel";
import BranchNavigator from '@/components/BranchNavigator';
import MagicalLottie from '@/components/MagicalLottie';
import MergeHandAnimation from '@/components/MergeHandAnimation';
import CodeReviewModal from '@/components/CodeReviewModal';
import CommitModal from '@/components/CommitModal';
import NotificationSystem from '@/components/NotificationSystem';
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
    <main className="h-screen max-h-screen relative overflow-hidden flex flex-col items-center pt-20 pb-52 font-fantasy">
      
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

      <h1 className="text-6xl font-fantasy text-[#4a1c40] mb-4 drop-shadow-lg z-10 shrink-0">
        As Crônicas de Aetheria
      </h1>

      {/* Lottie Animation Layers */}
      <MagicalLottie />
      <MergeHandAnimation />
      
      {/* Global Modals (High Z-Index) */}
      <CodeReviewModal 
        isOpen={useGameStore((s) => s.reviewModal.isOpen)}
        targetBranch={useGameStore((s) => s.reviewModal.targetBranch) || ""}
        onConfirm={() => {
            const { reviewModal, mergeProposal, closeReviewModal } = useGameStore.getState();
            if (reviewModal.targetBranch) {
                mergeProposal(reviewModal.targetBranch);
            }
            closeReviewModal();
        }}
        onCancel={() => useGameStore.getState().closeReviewModal()}
      />

      <CommitModal
        isOpen={useGameStore((s) => s.commitModal.isOpen)}
        onConfirm={(content, message) => {
            useGameStore.getState().commitChange(content, message);
            useGameStore.getState().closeCommitModal();
        }}
        onCancel={() => useGameStore.getState().closeCommitModal()}
      />

      <NotificationSystem />

      {/* Main Content (Z-Index > 0) */}
      <div className="relative z-10 w-full max-w-[98vw] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0 p-2">
        
        {/* Left Panel: Git Graph Visualization (Timeline) - Expanded */}
        <div className="lg:col-span-4 h-full overflow-hidden">
            <TreeOfWorlds />
        </div>

        {/* Center Panel: The Main Story */}
        <div className="lg:col-span-5 h-full overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-[#c5a059] scrollbar-track-[#2c1810]">
            <StoryBook />
        </div>

        {/* Right Panel: Branch Navigation (Active Prophecies) */}
        <div className="lg:col-span-3 h-full">
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
