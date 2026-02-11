'use client';

import { useGameStore } from '../store/gameStore';
import { Gitgraph, templateExtend, TemplateName, Orientation } from '@gitgraph/react';

export default function TreeOfWorlds() {
  const { graph } = useGameStore();

  // Define Dark Fantasy Theme Template
  const fantasyTemplate = templateExtend(TemplateName.Metro, {
    colors: ['#c5a059', '#22c55e', '#ef4444', '#3b82f6', '#a855f7'],
    branch: {
      lineWidth: 4,
      spacing: 50,
      label: {
        font: 'normal 10px "Cinzel", serif',
        borderRadius: 4,
        color: '#e5e5e5', 
        strokeColor: '#8b5a2b',
      },
    },
    commit: {
      spacing: 60,
      dot: {
        size: 10,
        strokeWidth: 2,
        color: '#c5a059',
      },
      message: {
        displayAuthor: true,
        displayHash: true,
        font: 'normal 12px "Lato", sans-serif',
        color: '#e5e5e5',
      },
    },
  });

  return (
    <div className="h-full flex flex-col">
       {/* Scrolling Container */}
      <div className="flex-1 overflow-auto p-4 scrollbar-thin scrollbar-thumb-[var(--color-gold-dim)] scrollbar-track-transparent">
        <Gitgraph key={Object.keys(graph.commits).length} options={{
          template: fantasyTemplate,
          orientation: Orientation.VerticalReverse, // Newest at top
          author: 'Invocador', 
        }}>
          {(gitgraph) => {
            // 1. Sort commits chronologically
            const sortedCommits = Object.values(graph.commits).sort((a, b) => a.timestamp - b.timestamp);

            // 2. Branch Affinity Calculation
            const commitAffinity: Record<string, string> = {};
            const visitedForAffinity = new Set<string>();

            const traceAffinity = (commitId: string | null, branchName: string) => {
                const queue = [commitId];
                while (queue.length > 0) {
                    const currId = queue.shift();
                    if (!currId || !graph.commits[currId]) continue;
                    
                    if (visitedForAffinity.has(currId)) {
                        continue; 
                    }

                    commitAffinity[currId] = branchName;
                    visitedForAffinity.add(currId);
                    
                    queue.push(graph.commits[currId].parentId);
                }
            };

            // A. PRIORITY: Claim Main History First
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
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const branchVisuals: Record<string, any> = {};
            
            // ALWAYS initialize Main first
            const mainBranch = gitgraph.branch({
                name: 'O Destino (main)',
                style: {
                    color: '#c5a059',
                    lineWidth: 4, 
                    spacing: 50,
                    label: {
                        color: '#c5a059',
                        strokeColor: '#3d2618',
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
                    const parentId = commit.parentId;
                    const parentAffinity = parentId ? (commitAffinity[parentId] || 'main') : 'main';
                    
                    const parentVisual = branchVisuals[parentAffinity] || mainBranch;
                    
                    branchVisual = parentVisual.branch({
                        name: affinity === 'detached' ? '?' : affinity,
                        style: {
                            lineWidth: 3, 
                            spacing: 50,
                            label: {
                                color: '#e5e5e5',
                                strokeColor: '#1a1110', 
                            }
                        }
                    });
                    branchVisuals[affinity] = branchVisual;
                }

                if (commit.secondaryParentId) {
                    const incomingAffinity = commitAffinity[commit.secondaryParentId];
                    const incomingBranch = branchVisuals[incomingAffinity];
                    const playerBranchName = incomingAffinity;
                    
                    if (incomingBranch && incomingAffinity !== affinity) {
                        const mergeTooltip = `Invocador: ${commit.author}\nData: ${new Date(commit.timestamp).toLocaleString('pt-BR')}\nHashId: ${commit.id}\nMerge: ${playerBranchName} -> ${affinity}`;
                        
                        branchVisual.merge({
                            branch: incomingBranch,
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            commitOptions: {
                                hash: commit.id,
                                subject: displayMessage,
                                author: commit.author,
                                dotText: commit.id === graph.head ? '👑' : '⚡',
                                tooltip: mergeTooltip as any,
                                style: {
                                    message: { font: 'bold 12px "Lato"', color: '#e5e5e5' },
                                    dot: { size: 10, strokeWidth: 3, color: '#f59e0b' }
                                }
                            }
                        });
                        return;
                    }
                }

                // Regular Commit
                const tooltipContent = `Invocador: ${commit.author}\nData: ${new Date(commit.timestamp).toLocaleString('pt-BR')}\nHashId: ${commit.id}`;
                
                branchVisual.commit({
                    hash: commit.id,
                    subject: displayMessage,
                    author: commit.author,
                    dotText: commit.id === graph.head ? '👑' : '📜',
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    tooltip: tooltipContent as any, // Force tooltip property
                    style: {
                         dot: {
                             color: affinity === 'main' ? '#c5a059' : undefined,
                             strokeColor: '#1a1110' // Contrast stroke
                         },
                         message: {
                             color: commit.id === graph.head ? '#c5a059' : '#e5e5e5',
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
