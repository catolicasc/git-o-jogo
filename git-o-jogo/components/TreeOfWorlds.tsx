'use client';

import { useGameStore } from '../store/gameStore';
import { GitCommit, GitBranch, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export default function TreeOfWorlds() {
  const { graph } = useGameStore();

  // Sort commits by timestamp (newest first for a feed)
  const commits = Object.values(graph.commits).sort((a, b) => b.timestamp - a.timestamp);

  return (
    <div className="h-full bg-[#2c1810]/95 rounded-lg border border-[#8b5a2b] shadow-xl backdrop-blur-sm flex flex-col overflow-hidden">
      
      {/* Header */}
      <div className="p-4 border-b border-[#8b5a2b]/30 bg-[#1a0f0a]/50">
        <h3 className="text-[#c5a059] font-fantasy text-xl flex items-center justify-center gap-2">
          <GitCommit className="w-5 h-5" />
          Crônicas dos Tempos (Log)
        </h3>
        <p className="text-[#f4e4bc]/40 text-xs text-center mt-1 font-mono">
           {commits.length} eventos registrados na história
        </p>
      </div>

      {/* Feed List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="relative border-l-2 border-[#8b5a2b]/20 ml-3 space-y-8">
            {commits.map((commit) => {
                // Determine if this commit is the head of any branch
                const branchesHere = Object.values(graph.branches).filter(b => b.headCommitId === commit.id);
                
                // Determine if any player is currently on this commit
                const playersHere = Object.values(graph.activePlayers || {}).filter(p => {
                    // Start simple: match branch head? Or exact commit? 
                    // Our model links players to branches, so we check if the branch they are on points to this commit.
                    // Ideally we should track exact commit per player, but this works for now.
                    const branch = graph.branches[p.branch];
                    return branch && branch.headCommitId === commit.id;
                });

                return (
                    <div key={commit.id} className="relative pl-8 group">
                        {/* Timeline Connector Dot */}
                        <div className="absolute -left-[9px] top-1 h-5 w-5 rounded-full border-4 border-[#2c1810] bg-[#8b5a2b] group-hover:bg-[#c5a059] transition-colors shadow-md" />
                        
                        {/* Card Content */}
                        <div className="flex flex-col gap-1">
                            {/* Metadata Header */}
                            <div className="flex items-center gap-2 text-xs text-[#f4e4bc]/50 font-mono">
                                <span className="text-[#c5a059] font-bold">#{commit.id.substring(0,6)}</span>
                                <span>•</span>
                                <span className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {formatDistanceToNow(commit.timestamp, { addSuffix: true, locale: ptBR })}
                                </span>
                                <span>•</span>
                                <span className="text-[#f4e4bc]">{commit.author || "Sistema"}</span>
                            </div>

                            {/* Commit Message */}
                            <div className="text-[#f4e4bc] text-sm font-serif leading-relaxed bg-[#1a0f0a]/30 p-2 rounded border border-[#8b5a2b]/10 hover:border-[#8b5a2b]/40 transition-colors">
                                {commit.message}
                            </div>
                            
                            {/* Badges: Branches & Players */}
                            <div className="flex flex-wrap gap-2 mt-1">
                                {/* Branch Badges */}
                                {branchesHere.map(branch => (
                                    <span key={branch.name} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-[#c5a059]/20 text-[#c5a059] border border-[#c5a059]/30">
                                        <GitBranch className="w-3 h-3" />
                                        {branch.name === 'main' ? 'O Destino (main)' : branch.name}
                                        {branch.name === graph.head && <span className="text-[8px] bg-[#c5a059] text-[#2c1810] px-1 rounded ml-1">HEAD</span>}
                                    </span>
                                ))}

                                {/* Player Avatars */}
                                {playersHere.map(player => (
                                    <span key={player.name} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-blue-500/20 text-blue-200 border border-blue-500/30" title={`Invocador ${player.name} está aqui`}>
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: player.color }} />
                                        {player.name}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
      </div>
    </div>
  );
}
