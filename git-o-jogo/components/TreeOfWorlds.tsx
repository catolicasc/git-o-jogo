'use client';

import { useGameStore } from '../store/gameStore';
import { GitCommit, GitBranch, Clock } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { useMemo } from 'react';
import { motion } from 'framer-motion';

// Helper types for visualization
interface VisualNode {
    id: string;
    x: number; // Lane index (0, 1, 2...)
    y: number; // Vertical position (index in sorted list)
    commit: any;
    branch?: string; // If it's a branch head
    color: string;
}

interface VisualLink {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    color: string;
}

const COLORS = [
    '#c5a059', // Gold (Main)
    '#3b82f6', // Blue
    '#22c55e', // Green
    '#ef4444', // Red
    '#a855f7', // Purple
    '#f97316', // Orange
    '#ec4899', // Pink
];

export default function TreeOfWorlds() {
  const { graph } = useGameStore();

  // 1. Process Graph into Lanes
  const visualData = useMemo(() => {
    const commits = Object.values(graph.commits).sort((a, b) => b.timestamp - a.timestamp);
    const branchHeads = Object.values(graph.branches);

    // Map Commit ID -> Branch Name (to assign color/lane affinity)
    // This is heuristic: tracing back from branch heads
    const commitBranchMap: Record<string, string> = {};
    const branchColorMap: Record<string, string> = {};
    const laneMap: Record<string, number> = {};
    
    // Assign Main first
    const mainBranch = branchHeads.find(b => b.name === 'main');
    if (mainBranch) {
        let curr: string | null = mainBranch.headCommitId;
        // Trace back simple history (this is naive, real git graph visualizers are complex)
        // For this game, we can try to "claim" commits for branches
        // But commits can belong to multiple histories.
        // Simplified Logic: 
        // 1. Sort branches by creation time (if we had it). 'main' is 0.
        // 2. Assign unique lanes to active branches.
        
        laneMap['main'] = 0;
        branchColorMap['main'] = COLORS[0];
    }

    const ROW_HEIGHT = 60;
    const LANE_WIDTH = 30;
    const PADDING_TOP = 20;

    const nodes: VisualNode[] = [];
    const links: VisualLink[] = [];

    // Assign lanes using topological tracing
    // Main (or current HEAD) starts at 0.
    // Secondary parents trigger new lanes.
    
    // We need to find all "Tips" of the graph.
    // Branch heads are tips.
    // Merged branches that were deleted are reachable via merge commits (secondary parents).

    // Reset lane counter
    let laneCounter = 1;
    
    // Map Commit ID -> Lane
    const commitLane: Record<string, number> = {};

    // Use a Set to avoid infinite recursion
    const visited = new Set<string>();

    const trace2 = (commitId: string, lane: number) => {
        if (!commitId || !graph.commits[commitId]) return;
        
        // If already assigned a lane...
        if (commitLane[commitId] !== undefined) {
            return;
        }

        commitLane[commitId] = lane;
        visited.add(commitId);

        const commit = graph.commits[commitId];

        // 1. Trace Primary Parent (Stay in same lane)
        if (commit.parentId) {
            trace2(commit.parentId, lane);
        }

        // 2. Trace Secondary Parent (Start new lane - this captures the "merged" history)
        if (commit.secondaryParentId) {
            // Assign a new lane color/index
            const newLane = laneCounter++; 
            trace2(commit.secondaryParentId, newLane);
        }
    };

    // Start tracing from Main Head
    if (mainBranch) {
        trace2(mainBranch.headCommitId, 0);
    }
    
    // Also trace other active branches if they are detached/ahead
    branchHeads.filter(b => b.name !== 'main').forEach(b => {
         // If not yet visited, it means it's a parallel tip not yet merged
         if (commitLane[b.headCommitId] === undefined) {
             const newLane = laneCounter++;
             trace2(b.headCommitId, newLane);
         }
    });

    // Generate Nodes
    commits.forEach((commit, index) => {
        const laneIndex = commitLane[commit.id] ?? 0;
        
        nodes.push({
            id: commit.id,
            x: laneIndex * LANE_WIDTH + 20, 
            y: index * ROW_HEIGHT + PADDING_TOP,
            commit,
            branch: branchHeads.find(b => b.headCommitId === commit.id)?.name,
            color: COLORS[laneIndex % COLORS.length]
        });
    });

    // Generate Links
    nodes.forEach(node => {
        // Primary Parent Link
        if (node.commit.parentId) {
            const parent = nodes.find(n => n.id === node.commit.parentId);
            if (parent) {
                links.push({
                    x1: node.x,
                    y1: node.y,
                    x2: parent.x,
                    y2: parent.y,
                    color: node.color // Link color matches child
                });
            }
        }
        
        // Secondary Parent Link (Merge)
        if (node.commit.secondaryParentId) {
            const secondParent = nodes.find(n => n.id === node.commit.secondaryParentId);
             if (secondParent) {
                // Merge Link: usually from the branch being merged (second parent) TO the merge commit (node)
                // But we draw from Node to Parent.
                // Color should probably match the branch being merged (second parent)? 
                // Or maybe a neutral/gradient? Let's use Second Parent's color to show "incoming"
                links.push({
                    x1: node.x,
                    y1: node.y,
                    x2: secondParent.x,
                    y2: secondParent.y,
                    color: secondParent.color 
                });
            }
        }
    });

    return { nodes, links, height: commits.length * ROW_HEIGHT + 100 };
  }, [graph]);

  return (
    <div className="h-full bg-[#2c1810]/95 rounded-lg border border-[#8b5a2b] shadow-xl backdrop-blur-sm flex flex-col overflow-hidden leading-relaxed">
      
      {/* Header */}
      <div className="p-2 border-b border-[#8b5a2b]/30 bg-[#1a0f0a]/50 shrink-0 z-20">
        <h3 className="text-[#c5a059] font-fantasy text-lg flex items-center justify-center gap-2">
          <Clock className="w-4 h-4" />
          Linha do Tempo
        </h3>
      </div>

      {/* SVG Viz Container */}
      <div className="flex-1 overflow-y-auto relative scrollbar-thin scrollbar-thumb-[#c5a059] scrollbar-track-[#2c1810]">
         <div className="min-h-full relative" style={{ height: visualData.height }}>
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="28" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#8b5a2b" />
                    </marker>
                </defs>
                {/* Links (Bezier Curves) */}
                {visualData.links.map((link, i) => {
                    const isStraight = link.x1 === link.x2;
                    let d = "";
                    if (isStraight) {
                        d = `M ${link.x1} ${link.y1} L ${link.x2} ${link.y2}`;
                    } else {
                        // Bezier logic for lane jumping (Merge/Branching)
                        // Make curves smoother for merges
                        const c1y = link.y1 + (link.y2 - link.y1) / 2;
                        d = `M ${link.x1} ${link.y1} C ${link.x1} ${c1y}, ${link.x2} ${c1y}, ${link.x2} ${link.y2}`;
                    }

                    return (
                        <path 
                            key={i}
                            d={d}
                            stroke={link.color}
                            strokeWidth="2"
                            fill="none"
                            opacity="0.5"
                        />
                    );
                })}
            </svg>

            {/* Nodes (React Components) */}
            {visualData.nodes.map((node) => (
                <motion.div
                    key={node.id}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="absolute flex items-center gap-2 group"
                    style={{ left: node.x - 8, top: node.y - 10 }}
                >
                    {/* The Dot */}
                    <div 
                        className="w-4 h-4 rounded-full border-2 shadow-md bg-[#2c1810] z-10 transition-transform group-hover:scale-125 cursor-pointer relative"
                        style={{ borderColor: node.color }}
                        title={`Commit: ${node.id}`}
                    >
                         {/* Branch Head Indicator */}
                         {node.branch && (
                             <div className="absolute -top-5 left-1/2 -translate-x-1/2 bg-[#2c1810] text-[9px] px-1.5 py-0.5 rounded border shadow-sm whitespace-nowrap z-20 font-bold" style={{ borderColor: node.color, color: node.color }}>
                                 {node.branch === 'main' ? 'Destino' : node.branch}
                             </div>
                         )}
                    </div>

                    {/* Commit Info Card (Right side) */}
                    <div className="bg-[#1a0f0a]/80 p-1.5 rounded border border-[#8b5a2b]/30 w-56 backdrop-blur-sm hover:bg-[#2c1810] hover:border-[#c5a059] transition-colors ml-2 shadow-lg">
                        <div className="flex justify-between items-start mb-0.5 text-[9px] text-[#f4e4bc]/50 font-mono">
                            <span className="text-[#c5a059]">#{node.id}</span>
                            <span>{formatDistanceToNow(node.commit.timestamp, { addSuffix: true, locale: ptBR })}</span>
                        </div>
                        <div className="text-[#f4e4bc] text-[10px] font-serif leading-snug break-words line-clamp-2">
                            {node.commit.message}
                        </div>
                        <div className="mt-0.5 text-[9px] text-right text-[#f4e4bc]/30 italic truncate">
                            {node.commit.author}
                        </div>
                    </div>
                </motion.div>
            ))}
         </div>
      </div>
    </div>
  );
}
