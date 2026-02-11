'use client';

import { useGameStore } from '../store/gameStore';
import { Gitgraph, templateExtend, TemplateName, Orientation } from '@gitgraph/react';
import { useMemo } from 'react';

export default function TreeOfWorlds() {
  const { graph } = useGameStore();

  // Define Fantasy Theme Template
  const fantasyTemplate = templateExtend(TemplateName.Metro, {
    colors: ['#c5a059', '#22c55e', '#ef4444', '#3b82f6', '#a855f7'],
    branch: {
      lineWidth: 3,
      label: {
        font: 'normal 10px "Cinzel", serif',
        borderRadius: 4,
        color: '#2c1810',
      },
    },
    commit: {
      spacing: 50,
      dot: {
        size: 8,
        strokeWidth: 2,
        color: '#c5a059',
      },
      message: {
        displayAuthor: true,
        displayHash: true,
        font: 'normal 12px "MedievalSharp", serif',
        color: '#f4e4bc',
      },
    },
  });

  return (
    <div className="h-full bg-[#2c1810]/95 rounded-lg border border-[#8b5a2b] shadow-xl backdrop-blur-sm flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-2 border-b border-[#8b5a2b]/30 bg-[#1a0f0a]/50 shrink-0 z-20 text-center">
        <h3 className="text-[#c5a059] font-fantasy text-lg">
          Linha do Tempo
        </h3>
      </div>

      <div className="flex-1 overflow-auto p-4 scrollbar-thin scrollbar-thumb-[#c5a059] scrollbar-track-[#2c1810]">
        <Gitgraph key={Object.keys(graph.commits).length} options={{
          template: fantasyTemplate,
          orientation: Orientation.VerticalReverse, // Newest at top
          author: 'Invocador', // Default author fallbacks
        }}>
          {(gitgraph) => {
            // 1. Sort commits chronologically
            const sortedCommits = Object.values(graph.commits).sort((a, b) => a.timestamp - b.timestamp);

            // 2. Branch Affinity Calculation
            // We identify which branch every commit belongs to efficiently.
            const commitAffinity: Record<string, string> = {};
            const visitedForAffinity = new Set<string>();

            // Helper: Trace back from a commit to root, assigning the branch name
            // Stop if we hit a node already assigned to a *different* priority branch
            const traceAffinity = (commitId: string | null, branchName: string) => {
                const queue = [commitId];
                while (queue.length > 0) {
                    const currId = queue.shift();
                    if (!currId || !graph.commits[currId]) continue;
                    
                    if (visitedForAffinity.has(currId)) {
                        // Collision? If it's already Main, we stop.
                        // Ideally Main traces first, so it claims everything it owns.
                        continue; 
                    }

                    commitAffinity[currId] = branchName;
                    visitedForAffinity.add(currId);
                    
                    // Only trace Primary Parent for linear affinity
                    // Secondary parents (merges) are jump-off points, not the branch history itself
                    queue.push(graph.commits[currId].parentId);
                }
            };

            // A. PRIORITY: Claim Main History First
            // This ensures the "Spine" is contiguous
            if (graph.branches['main']) {
                traceAffinity(graph.branches['main'].headCommitId, 'main');
            }

            // B. Claim Other Branches
            Object.values(graph.branches).forEach(branch => {
                if (branch.name !== 'main') {
                    traceAffinity(branch.headCommitId, branch.name);
                }
            });

            // 3. Render Initialization
            const branchVisuals: Record<string, any> = {};
            
            // ALWAYS initialize Main first to ensure it takes the first "lane"
            const mainBranch = gitgraph.branch({
                name: 'O Destino (main)',
                style: {
                    color: '#c5a059',
                    lineWidth: 5, // Extra thick spine
                    spacing: 40,
                    label: {
                        color: '#c5a059',
                        strokeColor: '#2c1810',
                        font: 'bold 12pt "Cinzel", serif'
                    }
                }
            });
            branchVisuals['main'] = mainBranch;

            // 4. Render Loop
            sortedCommits.forEach((commit) => {
                const affinity = commitAffinity[commit.id] || 'detached';
                const dateStr = new Date(commit.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const displayMessage = `[${dateStr}] ${commit.message}`;

                // Ensure Branch Exists
                let branchVisual = branchVisuals[affinity];
                if (!branchVisual) {
                    // We need to branch off from somewhere. 
                    // Find the parent's branch visual.
                    const parentId = commit.parentId;
                    const parentAffinity = parentId ? (commitAffinity[parentId] || 'main') : 'main';
                    
                    const parentVisual = branchVisuals[parentAffinity] || mainBranch;
                    
                    branchVisual = parentVisual.branch({
                        name: affinity === 'detached' ? '?' : affinity,
                        style: {
                            lineWidth: 3,
                            spacing: 40,
                        }
                    });
                    branchVisuals[affinity] = branchVisual;
                }

                // Handle Merges (Secondary Parent)
                if (commit.secondaryParentId) {
                    const incomingAffinity = commitAffinity[commit.secondaryParentId];
                    const incomingBranch = branchVisuals[incomingAffinity];
                    
                    if (incomingBranch && incomingAffinity !== affinity) {
                        branchVisual.merge({
                            branch: incomingBranch,
                            commitOptions: {
                                hash: commit.id,
                                subject: displayMessage,
                                author: commit.author,
                                dotText: commit.id === graph.head ? '👑' : '⚡',
                                style: {
                                    message: { font: 'bold 12px "MedievalSharp"' },
                                    dot: { size: 10, strokeWidth: 3 }
                                }
                            }
                        });
                        return; // Merge handled the commit
                    }
                }

                // Regular Commit
                branchVisual.commit({
                    hash: commit.id,
                    subject: displayMessage,
                    author: commit.author,
                    dotText: commit.id === graph.head ? '👑' : '📜',
                    style: {
                         dot: {
                             color: affinity === 'main' ? '#c5a059' : undefined,
                         }
                    }
                });
            });


          }}
        </Gitgraph>
      </div>
    </div>
  );
}
