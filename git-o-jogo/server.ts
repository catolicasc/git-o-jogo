import { createServer } from "node:http";
import next from "next";
import { Server } from "socket.io";
import { createInitialCommit, createCommit, GitGraph } from "./lib/git-logic";

const dev = process.env.NODE_ENV !== "production";
const hostname = "localhost";
const port = 3000;
const app = next({ dev, hostname, port });
const handler = app.getRequestHandler();

// Server-side Game State
const initialStory = "No princípio, havia apenas o vazio. Então, a primeira linha de código foi escrita...";
const initialCommit = createInitialCommit(initialStory);
const graph: GitGraph = {
    commits: { [initialCommit.id]: initialCommit },
    branches: { main: { name: 'main', headCommitId: initialCommit.id } },
    head: initialCommit.id
};

app.prepare().then(() => {
  const httpServer = createServer(handler);
  const io = new Server(httpServer);

  io.on("connection", (socket) => {
    console.log("Cliente conectado:", socket.id);

    // Send current graph to new player
    socket.emit("sync_graph", graph);

    socket.on("join_game", (data) => {
        console.log("Jogador entrou:", data);
        socket.join("game_room");
        
        // Add to active players
        if (!graph.activePlayers) graph.activePlayers = {};
        graph.activePlayers[socket.id] = {
            name: data.playerName || 'Anônimo',
            branch: 'main', // Default to main
            color: '#' + Math.floor(Math.random()*16777215).toString(16) // Random color
        };

        io.to("game_room").emit("sync_graph", graph);
    });
    
    // Support Switching branches explicitly (git checkout)
    socket.on("checkout_branch", ({ branchName }) => {
        if (graph.activePlayers && graph.activePlayers[socket.id]) {
            graph.activePlayers[socket.id].branch = branchName;
            io.to("game_room").emit("sync_graph", graph);
        }
    });

    socket.on("new_branch", ({ name, fromCommitId }) => {
        console.log("Nova branch:", name);
        if (graph.branches[name]) return; // Branch exists

        // Create the initial commit for this branch instantly
        // This gives visual feedback that a divergence happened
        const msg = `Inicio da profecia "${name}"`;
        const content = graph.commits[fromCommitId]?.content || "";
        
        // We need an author. In this scope we don't have the player ID handy in the payload
        // But we can just use "System" or require it in payload.
        // Let's rely on "System" for now or update Client to send it.
        // Actually, let's keep it simple: just create the commit.
        
        const newCommit = createCommit(msg, "Destino", fromCommitId, content);
        graph.commits[newCommit.id] = newCommit;

        // Create new branch pointing to this new commit
        graph.branches[name] = {
            name,
            headCommitId: newCommit.id
        };
        
        io.to("game_room").emit("sync_graph", graph);
    });

    socket.on("commit", ({ parentId, message, content, author }) => {
        console.log("Commit:", message);
        
        const playerBranchName = graph.activePlayers?.[socket.id]?.branch;
        if (!playerBranchName || !graph.branches[playerBranchName]) {
             return; 
        }

        const currentBranchHead = graph.branches[playerBranchName].headCommitId;

        // PROTECTED BRANCH LOGIC: "main" is read-only for direct commits.
        // If user is on "main", we MUST fork them to a new branch.
        if (playerBranchName === 'main') {
             console.log("Attempt to commit to main blocked. Forking new branch...");
             
             const newCommit = createCommit(message, author, parentId, content);
             graph.commits[newCommit.id] = newCommit;

             const newBranchName = `feature-${newCommit.id.substring(0,6)}`;
             graph.branches[newBranchName] = {
                 name: newBranchName,
                 headCommitId: newCommit.id
             };

             if (graph.activePlayers && graph.activePlayers[socket.id]) {
                 graph.activePlayers[socket.id].branch = newBranchName;
             }

             io.to("game_room").emit("sync_graph", graph);
             io.to(socket.id).emit("message", `A Profecia "main" é sagrada e imutável! Uma nova profecia "${newBranchName}" foi criada para suas escrituras.`);
             return;
        }

        // Check if the user is committing on top of a STALE commit (e.g. someone else moved the branch)
        if (currentBranchHead !== parentId) {
            console.log("Divergence detected! Forking branch...");
            
            // 1. Create the commit anyway
            const newCommit = createCommit(message, author, parentId, content);
            graph.commits[newCommit.id] = newCommit;

            // 2. Create a NEW branch for this user to save their work
            const newBranchName = `${playerBranchName}-fork-${newCommit.id.substring(0,4)}`;
            graph.branches[newBranchName] = {
                name: newBranchName,
                headCommitId: newCommit.id
            };

            // 3. Force move the player to this new branch
            if (graph.activePlayers && graph.activePlayers[socket.id]) {
                graph.activePlayers[socket.id].branch = newBranchName;
            }

            io.to("game_room").emit("sync_graph", graph);
            // Notify the specific user they were moved
            io.to(socket.id).emit("message", `Sua visão do tempo estava desatualizada! Uma nova linha do tempo "${newBranchName}" foi criada para salvar sua mudança.`);
            
            // Should we emit to everyone? Yes, sync_graph does that.
            return;
        }

        // Normal Case: Fast-forward
        const newCommit = createCommit(message, author, parentId, content);
        graph.commits[newCommit.id] = newCommit;

        // Update the head of the player's current branch
        graph.branches[playerBranchName].headCommitId = newCommit.id;

        // Also update global head if it matches (legacy support / default view)
        if (graph.head === parentId) {
            graph.head = newCommit.id;
        }

        io.to("game_room").emit("sync_graph", graph);
    });
    
    socket.on("merge_proposal", ({ target }) => {
        console.log(`Merge proposto para ${target}`);
        
        const playerBranchName = graph.activePlayers?.[socket.id]?.branch;
        if (!playerBranchName) return;

        const sourceBranch = graph.branches[playerBranchName];
        const targetBranch = graph.branches[target];

        // 1. Validate branches
        if (!sourceBranch || !targetBranch) return;

        // RESTRICTION: 'main' cannot merge into other branches
        if (playerBranchName === 'main') {
            io.to(socket.id).emit("message", `A Verdade Absoluta (main) não pode ser diluída em profecias menores. Apenas o contrário é permitido.`);
            return;
        }

        const myHeadId = sourceBranch.headCommitId;
        const targetHeadId = targetBranch.headCommitId;

        // 2. Conflict Detection Logic
        
        // Check if OUR base is the SAME as target's CURRENT head.
        // If target moved, we are based on an old commit -> Conflict!
        
        const isFastForwardable = (targetHead: string, myHead: string): boolean => {
             let curr: string | null = myHead;
             while (curr) {
                 if (curr === targetHead) return true;
                 curr = graph.commits[curr]?.parentId || null;
             }
             return false;
        };

        if (isFastForwardable(targetHeadId, myHeadId)) {
            // Fast-forward merge
            graph.branches[target].headCommitId = myHeadId;
            // Only update global head if we merged INTO main
            if (target === 'main') {
                graph.head = myHeadId;
            }
            
            io.to("game_room").emit("sync_graph", graph);
            io.to("game_room").emit("message", `A profecia "${playerBranchName}" tornou-se a Verdade absoluta em "${target}"!`);
            
            // AUTO-DELETE BRANCH Logic
            if (playerBranchName !== 'main') {
                delete graph.branches[playerBranchName];
                // Move players on that branch to target
                Object.keys(graph.activePlayers || {}).forEach(pid => {
                    if (graph.activePlayers![pid].branch === playerBranchName) {
                        graph.activePlayers![pid].branch = target;
                    }
                });
                io.to("game_room").emit("sync_graph", graph);
                io.to("game_room").emit("message", `A profecia "${playerBranchName}" foi cumprida e desvaneceu da história.`);
            }

        } else {
            // CONFLICT! Target moved forward while we were working.
            console.log("Conflict detected!");
            socket.emit("merge_conflict", {
                sourceBranch: playerBranchName,
                targetBranch: target,
                baseContent: graph.commits[targetHeadId].content, // The content we are conflicting with (target head)
                myContent: graph.commits[myHeadId].content // Our content
            });
        }
    });

    socket.on("resolve_conflict", ({ target, content, message, author }) => {
        console.log(`Resolvendo conflito para ${target}`);
        
        const playerBranchName = graph.activePlayers?.[socket.id]?.branch;
        if (!playerBranchName) return;
        
        const sourceBranch = graph.branches[playerBranchName];
        const targetBranch = graph.branches[target];

        if (!sourceBranch || !targetBranch) return;

        // Create a merge commit
        // Parent 1: Target Head (the one we are merging into)
        // Parent 2: Source Head (us) -> In real git. 
        // Here `createCommit` only takes one parent. Let's use Target Head as primary parent.
        
        const newCommit = createCommit(message, author, targetBranch.headCommitId, content);
        graph.commits[newCommit.id] = newCommit;

        // Update target branch to this new commit
        graph.branches[target].headCommitId = newCommit.id;

        // If merging into main, update global head
        if (target === 'main') {
            graph.head = newCommit.id;
        }

        // AUTO-DELETE BRANCH Logic (after conflict resolution)
        if (playerBranchName !== 'main') {
            delete graph.branches[playerBranchName];
            // Move players on that branch to target
            Object.keys(graph.activePlayers || {}).forEach(pid => {
                if (graph.activePlayers![pid].branch === playerBranchName) {
                    graph.activePlayers![pid].branch = target;
                }
            });
             io.to("game_room").emit("message", `A profecia "${playerBranchName}" foi cumprida (após duelo) e desvaneceu da história.`);
        }

        io.to("game_room").emit("sync_graph", graph);
        io.to("game_room").emit("message", `CONFLITO RESOLVIDO! A história avança!`);
    });

    socket.on("disconnect", () => {
        console.log("Cliente desconectado:", socket.id);
        if (graph.activePlayers && graph.activePlayers[socket.id]) {
            delete graph.activePlayers[socket.id];
            io.to("game_room").emit("sync_graph", graph);
        }
    });
  });

  httpServer
    .once("error", (err) => {
      console.error(err);
      process.exit(1);
    })
    .listen(port, () => {
      console.log(`> Ready on http://${hostname}:${port}`);
    });
});
