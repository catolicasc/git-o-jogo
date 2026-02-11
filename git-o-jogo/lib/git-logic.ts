// Git Graph Logic for As Crônicas de Aetheria
import { v4 as uuidv4 } from 'uuid';

export interface Commit {
  id: string;
  message: string;
  author: string;
  timestamp: number;
  parentId: string | null;
  content: string; // The "story" at this point
}

export interface Branch {
  name: string;
  headCommitId: string;
}

export interface GitGraph {
  commits: Record<string, Commit>;
  branches: Record<string, Branch>;
  head: string | null; // ID of the currently checked out commit
  activePlayers?: Record<string, { name: string, branch: string, color: string }>;
}

export const createInitialCommit = (initialStory: string): Commit => {
  return {
    id: uuidv4().substring(0, 7), // Short hash style
    message: "In the beginning...",
    author: "System",
    timestamp: Date.now(),
    parentId: null,
    content: initialStory,
  };
};

export const createCommit = (
  message: string,
  author: string,
  parentId: string,
  content: string
): Commit => {
  return {
    id: uuidv4().substring(0, 7),
    message,
    author,
    timestamp: Date.now(),
    parentId,
    content,
  };
};

// Helper to get history of a commit (traverse parents)
export const getHistory = (commits: Record<string, Commit>, startCommitId: string): Commit[] => {
  const history: Commit[] = [];
  let currentId: string | null = startCommitId;

  while (currentId && commits[currentId]) {
    history.push(commits[currentId]);
    currentId = commits[currentId].parentId;
  }

  return history.reverse(); // Chronological order
};
