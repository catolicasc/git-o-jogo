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
    const userId = localStorage.getItem("userId") || uuidv4();
    localStorage.setItem("userId", userId);
    connect();
  }, [connect]);

  return (
    <main className="h-screen w-screen overflow-hidden flex flex-col bg-[var(--color-bg-main)] text-[var(--color-text-main)] font-body">
      
      {/* Background Ambience */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,#1a1110_0%,#0f0a0a_100%)] -z-10" />
      <div className="absolute inset-0 bg-[url('/magic-particles.png')] opacity-10 animate-pulse pointer-events-none -z-10" />

      {/* Header */}
      <header className="shrink-0 h-16 border-b border-[var(--color-panel-border)] bg-[var(--color-panel)] flex items-center justify-between px-6 z-20 shadow-lg">
         <div className="flex items-center gap-4">
            <h1 className="text-2xl font-fantasy text-[var(--color-text-main)] tracking-widest drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]">
              As Crônicas de Aetheria
            </h1>
            <span className="text-xs text-[var(--color-text-muted)] uppercase tracking-wider border border-[var(--color-panel-border)] px-2 py-0.5 rounded">
                Sessão Ativa
            </span>
         </div>

         <div className="flex items-center gap-4 text-sm">
             {/* Connected Users Count */}
             <div className="flex items-center gap-2 px-3 py-1 rounded border border-[var(--color-panel-border)] bg-[var(--color-bg-main)]/50 text-[var(--color-gold)] font-mono text-xs" title="Cronistas Conectados">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-accent-green)] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--color-accent-green)]"></span>
                </span>
                <span>{Object.keys(useGameStore.getState().graph.activePlayers || {}).length} Online</span>
             </div>

             {playerId && (
                <div className="text-[var(--color-text-muted)] font-mono">
                    <span className="text-[var(--color-gold-dim)]">Invocador:</span> {playerId.substring(0,8)}...
                </div>
             )}
             <div className="w-8 h-8 rounded-full bg-[var(--color-gold)] text-[var(--color-bg-main)] flex items-center justify-center font-bold font-fantasy border border-[var(--color-gold-dim)]">
                D
             </div>
         </div>
      </header>

      {/* Main Layout Grid */}
      <div className="flex-1 min-h-0 grid grid-cols-12 gap-0 relative z-10">
        
        {/* Left Panel: Timeline (20%) */}
        <aside className="col-span-3 border-r border-[var(--color-panel-border)] bg-[var(--color-bg-main)]/50 flex flex-col min-h-0">
             <div className="p-3 border-b border-[var(--color-panel-border)] bg-[var(--color-panel)]">
                <h3 className="text-[var(--color-gold)] font-fantasy text-sm uppercase tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[var(--color-gold)] shadow-[0_0_8px_var(--color-gold)]"></span>
                    Linha do Tempo
                </h3>
             </div>
             <div className="flex-1 overflow-hidden relative">
                <TreeOfWorlds />
             </div>
        </aside>

        {/* Center Panel: Story (55%) */}
        <section className="col-span-6 flex flex-col min-h-0 relative bg-[#0f0a0a]">
            {/* Story Header/Title Area */}
            <div className="p-8 pb-4 text-center">
                 <div className="inline-block px-4 py-1 border border-[var(--color-gold-dim)] rounded-full text-[var(--color-gold)] text-xs font-fantasy mb-4 opacity-70">
                    Capítulo I
                 </div>
                 <h2 className="text-4xl font-fantasy text-[var(--color-text-main)] mb-2 drop-shadow-lg">
                    As Crônicas de Aetheria
                 </h2>
                 <div className="h-px w-32 bg-gradient-to-r from-transparent via-[var(--color-gold-dim)] to-transparent mx-auto"></div>
            </div>

            {/* Scrollable Story Content */}
            <div className="flex-1 overflow-y-auto px-12 pb-20 scrollbar-thin scrollbar-thumb-[var(--color-gold-dim)] scrollbar-track-transparent">
                 <StoryBook />
            </div>

             {/* Action Bar (Floating at bottom of center) */}
             <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4">
                 <button 
                    onClick={() => useGameStore.getState().openCommitModal()}
                    className="bg-[var(--color-gold)] text-[var(--color-bg-main)] px-8 py-3 rounded-sm font-fantasy font-bold hover:bg-[#d4b06a] transition-all shadow-[0_0_20px_rgba(197,160,89,0.2)] flex items-center gap-2 hover:scale-105 active:scale-95 uppercase tracking-wide"
                 >
                    <span>✎</span> Escrever (Commit)
                 </button>
             </div>
        </section>

        {/* Right Panel: Navigator (25%) */}
        <aside className="col-span-3 border-l border-[var(--color-panel-border)] bg-[var(--color-panel)]/30 flex flex-col min-h-0">
            <div className="p-3 border-b border-[var(--color-panel-border)] bg-[var(--color-panel)]">
                <h3 className="text-[var(--color-gold)] font-fantasy text-sm uppercase tracking-widest">
                    Profecias Ativas
                </h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
                <BranchNavigator />
            
                <div className="mt-8 pt-6 border-t border-[var(--color-panel-border)]">
                    <h4 className="text-[var(--color-gold)] font-fantasy text-sm mb-3">
                        Tecer Nova Profecia
                    </h4>
                    <VisionCreator />
                </div>
            </div>
        </aside>

      </div>

      {/* Footer / Terminal */}
      <footer className="shrink-0 h-48 border-t border-[var(--color-panel-border)] bg-[#0a0505] relative z-20">
          <SpellTerminal />
      </footer>

      {/* Modals & Overlays */}
      <OnboardingModal />
      <ConflictDuel />
      <MagicalLottie />
      <MergeHandAnimation />
      
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
      
    </main>
  );
}
