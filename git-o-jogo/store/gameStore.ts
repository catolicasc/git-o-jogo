import { create } from 'zustand';
import io, { type Socket } from 'socket.io-client';
import { GitGraph, createInitialCommit, getBlame } from '../lib/git-logic';

interface GameState {
  socket: any | null;
  isConnected: boolean;
  graph: GitGraph;
  playerId: string | null;
  
  // Derived helpers (or setters that trigger socket events)
  connect: () => void;
  createBranch: (branchName: string) => void;
  commitChange: (content: string, message: string) => void;
  mergeProposal: (targetBranch: string) => void;
  
  // Animation State
  showMergeAnimation: boolean;
  setMergeAnimation: (show: boolean) => void;

  // Review Modal State
  reviewModal: { isOpen: boolean; targetBranch: string | null };
  openReviewModal: (targetBranch: string) => void;
  closeReviewModal: () => void;

  commitModal: { isOpen: boolean };
  openCommitModal: () => void;
  closeCommitModal: () => void;

  notifications: { id: string; message: string; type: 'info' | 'error' }[];
  addNotification: (message: string, type?: 'info' | 'error') => void;
  removeNotification: (id: string) => void;
  
  // Getters for keys used in components
  getStory: () => string;
  getCurrentBranchName: () => string;
  
  currentBranch: string;
  playerName: string | null;
  setPlayerName: (name: string) => void;

  commandLog: { id: string; command: string; description?: string; timestamp: number }[];
  addCommand: (command: string, description?: string) => void;
  checkoutBranch: (branchName: string) => void;
  
  // Blame support
  getBlame: () => import('../lib/git-logic').BlameInfo[];
}

const initialStory = "No princípio, havia apenas o vazio. Então, a primeira linha de código foi escrita...";
const initialCommit = createInitialCommit(initialStory);

const initialGraph: GitGraph = {
    commits: { [initialCommit.id]: initialCommit },
    branches: { main: { name: 'main', headCommitId: initialCommit.id } },
    head: initialCommit.id
};

export const useGameStore = create<GameState>((set, get) => ({
  socket: null,
  isConnected: false,
  graph: initialGraph,
  currentBranch: 'main',
  playerId: null,
  playerName: null,
  commandLog: [],
  showMergeAnimation: false,

  setMergeAnimation: (show: boolean) => set({ showMergeAnimation: show }),

  reviewModal: { isOpen: false, targetBranch: null },
  openReviewModal: (targetBranch: string) => set({ reviewModal: { isOpen: true, targetBranch } }),
  closeReviewModal: () => set({ reviewModal: { isOpen: false, targetBranch: null } }),

  commitModal: { isOpen: false },
  openCommitModal: () => set({ commitModal: { isOpen: true } }),
  closeCommitModal: () => set({ commitModal: { isOpen: false } }),

  notifications: [],
  addNotification: (message, type = 'info') => {
      const id = Math.random().toString(36).substr(2, 9);
      set(state => ({ notifications: [...state.notifications, { id, message, type }] }));
      setTimeout(() => get().removeNotification(id), 5000);
  },
  removeNotification: (id) => {
      set(state => ({ notifications: state.notifications.filter(n => n.id !== id) }));
  },

  // Local state for the user's current view

  addCommand: (command, description) => {
      set(state => ({
          commandLog: [...state.commandLog, {
              id: Math.random().toString(36).substr(2, 9),
              command,
              description,
              timestamp: Date.now()
          }]
      }));
  },


  setPlayerName: (name: string) => {
      set({ playerName: name });
      // If already connected, update server? For now, we rely on connect called later or re-emit
      const { socket, playerId } = get();
      if (socket && playerId) {
          socket.emit('update_player_info', { playerId, name });
      }
  },

  connect: () => {
    if (get().socket) return;
    
    // Auto-reconnect logic could go here
    const socket = io();

    socket.on('connect', () => {
      set({ isConnected: true });
      const userId = localStorage.getItem("userId");
      set({ playerId: userId });
      
      // Only join if we have a name? Or join and identify later.
      // Let's join and send whatever info we have.
      const playerName = get().playerName || localStorage.getItem('invocadorName');
      if (playerName) set({ playerName });

      socket.emit('join_game', { userId, playerName });
    });

    socket.on('disconnect', () => {
      set({ isConnected: false });
    });

    socket.on('message', (msg: string) => {
        get().addNotification(msg, 'info');
    });

    socket.on('error', (msg: string) => {
        get().addNotification(msg, 'error');
    });

    socket.on('sync_graph', (newGraph: GitGraph) => {
        set(state => {
            // If we have a currentBranch, ensure it exists in new graph, else fallback to head
            const branchExists = state.currentBranch && newGraph.branches[state.currentBranch];
            const newBranch = branchExists ? state.currentBranch : 'main';
            
            return { 
                graph: newGraph,
                currentBranch: newBranch
            };
        });
    });

    socket.on('merge_success_yours', () => {
        set({ showMergeAnimation: true });
    });

    set({ socket });
  },

  createBranch: (branchName: string) => {
      const { socket, graph, playerId, addCommand, currentBranch } = get();
      if (!socket || !playerId) return;
      
      // Prevent duplicate branch creation logic client-side check
      if (graph.branches[branchName]) return;

      const fromCommitId = graph.branches[currentBranch]?.headCommitId || graph.head;

      addCommand(`git checkout -b ${branchName}`, `Criando nova profecia "${branchName}" e mudando para ela.`);

      // Optimistic update
      set({ currentBranch: branchName });

      socket.emit('new_branch', { name: branchName, fromCommitId: fromCommitId, author: playerId });
  },

  commitChange: (content: string, message: string) => {
      const { socket, graph, playerId, addCommand, playerName, currentBranch, addNotification } = get();
      if (!socket || !playerId) return;

      if (currentBranch === 'main') {
          addNotification("A Profecia 'O Destino (main)' é sagrada e imutável! Você deve criar uma nova ramificação (branch) para propor mudanças.", 'error');
          return;
      }

      const parentId = graph.branches[currentBranch]?.headCommitId;
      if (!parentId) return;

      addCommand(`git add . && git commit -m "${message}"`, "Registrando novo capítulo na história.");
      
      socket.emit('commit', { 
          parentId: parentId, 
          message, 
          content, 
          author: playerName || playerId 
      });
  },

  mergeProposal: (targetBranch: string) => {
      const { socket, playerId, addCommand, getCurrentBranchName, playerName } = get();
      if (!socket || !playerId) return;

      const currentBranch = getCurrentBranchName();
      addCommand(`git checkout ${targetBranch} && git merge ${currentBranch}`, `Fundindo a profecia "${currentBranch}" na verdade "${targetBranch}".`);

      socket.emit('merge_proposal', { target: targetBranch, author: playerName || playerId });
  },

  getStory: () => {
      const { graph, currentBranch } = get();
      const branch = graph.branches[currentBranch];
      if (!branch) return "";
      
      const commit = graph.commits[branch.headCommitId];
      return commit ? commit.content : "";
  },

  getCurrentBranchName: () => {
      return get().currentBranch;
  },

  checkoutBranch: (branchName: string) => {
      const { socket, graph, addCommand } = get();
      if (!socket || !graph.branches[branchName]) return;

      addCommand(`git checkout ${branchName}`, `Alternando para a profecia "${branchName}".`);
      
      set({ currentBranch: branchName });

      socket.emit('checkout_branch', { branchName });
  },

  getBlame: () => {
      const { graph, currentBranch } = get();
      const branch = graph.branches[currentBranch];
      if (!branch) return [];
      
      return getBlame(graph.commits, branch.headCommitId);
  }
}));


