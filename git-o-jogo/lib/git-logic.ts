// Git Graph Logic for As Crônicas de Aetheria
import { v4 as uuidv4 } from 'uuid';

export interface Commit {
  id: string;
  message: string;
  author: string;
  timestamp: number;
  parentId: string | null;
  content: string; // The "story" at this point
  secondaryParentId?: string | null; // For merge commits
}

export interface Branch {
  name: string;
  headCommitId: string;
  status?: 'active' | 'merged';
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
    secondaryParentId: null,
    content: initialStory,
  };
};

export const createCommit = (
  message: string,
  author: string,
  parentId: string,
  content: string,
  secondaryParentId: string | null = null
): Commit => {
  return {
    id: uuidv4().substring(0, 7),
    message,
    author,
    timestamp: Date.now(),
    parentId,
    secondaryParentId,
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

export interface BlameInfo {
    commitId: string;
    author: string;
    timestamp: number;
    message: string;
    content: string; // The specific line content
}

export const getBlame = (commits: Record<string, Commit>, headCommitId: string): BlameInfo[] => {
    if (!headCommitId || !commits[headCommitId]) return [];

    const currentContent = commits[headCommitId].content;
    const lines = currentContent.split('\n');
    
    // For each line, we want to find the OLDEST commit in the ancestry chain that introduced it.
    // Optimization: Traverse specific history path backwards from HEAD.
    
    // 1. Get linear history from HEAD to Root
    // (Note: This simple blame doesn't handle merge conflict resolution attribution perfectly, 
    // it follows the primary parent path usually, or we can check both. 
    // For simplicity in this game, we follow the primary parent chain).
    const history = [];
    let curr: string | null = headCommitId;
    while(curr && commits[curr]) {
        history.push(commits[curr]);
        curr = commits[curr].parentId;
    }
    // History is now [HEAD, Parent, Grandparent, ... Root]
    
    const blameResults: BlameInfo[] = new Array(lines.length);

    // 2. Iterate lines and find their origin
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (!line.trim()) {
             // Empty lines belong to current or system? Let's verify.
             // Actually, emptiness tracks too.
        }

        // Default to HEAD if not found otherwise (shouldn't happen if root has it)
        let blamedCommit = commits[headCommitId];

        // Walk backwards from HEAD. 
        // If the parent ALSO has this exact line at this index... wait, indices shift!
        // "Diff" logic is complex. 
        // SIMPLIFICATION FOR THIS GAME: 
        // We assume lines are appended or modified. 
        // We look for the FIRST time this *exact string* appeared in the history chain? 
        // No, that fails if two people write "The end." separately.
        
        // Correct approach:
        // We need to diff `current` vs `parent`.
        // Since our game usually appends, we can check if `line` exists in `parent.content`.
        // If it does, we pass blame to parent. 
        // If it DOES NOT, then `current` introduced it.
        // What if it exists but at a different place? (Moved code) -> In standard git blame, moving is often "new line" unless -C is used.
        // Let's stick to: "Does parent content satisfy this line?" 
        
        // BETTER: Iterate from Root to Head. 
        // Maintain a "Current Blame Map" (Line Content -> Author).
        // If a commit changes content, re-calculate.
        
        // Let's try the "Walk Backwards" check:
        // For this specific line `line` at index `i` in `HEAD`:
        // Does `Parent` have `line`? 
        // If yes, blame Parent. 
        //   -> Then Does `Grandparent` have `line`?
        //   -> ...
        // The last one who HAS it is the author? NO.
        // The First one (chronologically) who has it is the author.
        // So we walk back as far as possible. 
        // If `root` has it, blame root.
        
        // LIMITATION: If multiple lines are identical, this simple "includes" check might blame the wrong one.
        // But for a story game, duplicate lines are rare or acceptable to mis-attribute.
        
        for (const candidate of history) {
             // candidate is traversing backwards: Head -> Parent -> ... -> Root
             // If candidate has the line, they are a POTENTIAL blamer.
             // We want the OLDEST one who has the line.
             // Which is the LAST one in this loop (since we go New -> Old) who still has the line?
             // No, wait.
             // Head (Has Line) -> Parent (Has Line) -> Root (Has Line). 
             // Author is Root.
             // Head (Has Line) -> Parent (Does NOT Have Line).
             // Author is Head.
             
             if (candidate.content.includes(line)) {
                 blamedCommit = candidate;
             } else {
                 // The parent (candidate) does NOT have the line.
                 // So the child (previous loop iteration) was the last one to have it.
                 // We stop here.
                 break;
             }
        }
        
        blameResults[i] = {
            commitId: blamedCommit.id,
            author: blamedCommit.author,
            timestamp: blamedCommit.timestamp,
            message: blamedCommit.message,
            content: line
        };
    }

    return blameResults;
};
