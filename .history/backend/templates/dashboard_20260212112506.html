<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RFID Nexus | Cyber Edition</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #05070a; }
        .neon-border-cyan { box-shadow: 0 0 10px rgba(34, 211, 238, 0.2), inset 0 0 5px rgba(34, 211, 238, 0.1); border: 1px solid rgba(34, 211, 238, 0.3); }
        .neon-border-indigo { box-shadow: 0 0 15px rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); }
        .neon-text-cyan { text-shadow: 0 0 8px rgba(34, 211, 238, 0.5); color: #22d3ee; }
        .glass-dark { background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(12px); }
        .status-pulse { animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; box-shadow: 0 0 10px currentColor; } 50% { opacity: 0.4; box-shadow: 0 0 2px currentColor; } }
        .mono { font-family: 'JetBrains Mono', monospace; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 10px; }
    </style>
</head>
<body class="text-slate-300 min-h-screen overflow-x-hidden">

    <div class="w-full bg-slate-900/50 border-b border-white/5 py-2 px-6 flex justify-between items-center backdrop-blur-md">
        <div class="flex items-center gap-4">
            <h1 class="text-lg font-black tracking-tighter text-white">RFID<span class="neon-text-cyan italic">NEXUS</span></h1>
            <span class="h-4 w-[1px] bg-slate-700"></span>
            <span class="text-[10px] mono text-slate-500 uppercase tracking-widest">Node: <span class="text-indigo-400">team_pixel</span></span>
        </div>
        <div class="flex items-center gap-3 bg-black/40 px-4 py-1 rounded-full border border-white/5">
            <span id="conn-status-dot" class="w-2 h-2 bg-red-500 rounded-full status-pulse"></span>
            <span id="conn-status-text" class="text-[10px] font-bold uppercase tracking-widest text-red-500">System Offline</span>
        </div>
    </div>

    <main class="container mx-auto px-6 py-10 max-w-5xl">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
            
            <div class="lg:col-span-7 space-y-6">
                <div class="neon-border-indigo glass-dark p-8 rounded-[2rem] relative overflow-hidden group">
                    <div class="absolute -top-24 -right-24 w-64 h-64 bg-indigo-600/10 blur-[100px] rounded-full"></div>
                    <div class="relative z-10">
                        <div class="flex justify-between items-start mb-16">
                            <div>
                                <p class="text-[10px] font-bold text-indigo-400 uppercase tracking-[0.3em] mb-1">Secure Edge Protocol</p>
                                <h2 class="text-white text-xl font-semibold">Smart Wallet Interface</h2>
                            </div>
                            <div class="w-12 h-8 bg-gradient-to-br from-slate-700 to-slate-800 rounded-md border border-white/10 opacity-50"></div>
                        </div>
                        <div class="space-y-6">
                            <div>
                                <p class="text-slate-500 text-[10px] mono uppercase mb-1 tracking-widest text-indigo-500/50">Card Signature (UID)</p>
                                <p id="card-uid" class="text-2xl mono text-white tracking-widest">_WAITING_FOR_TAP_</p>
                            </div>
                            <div class="pt-4 border-t border-white/5">
                                <p class="text-slate-500 text-[10px] mono uppercase mb-1">Available Credits</p>
                                <div class="flex items-baseline gap-3">
                                    <span id="card-balance" class="text-5xl font-bold text-white tracking-tighter neon-text-cyan">0</span>
                                    <span class="text-cyan-500/50 mono text-sm italic">RWF</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="neon-border-cyan glass-dark rounded-2xl p-6 bg-black/20 overflow-hidden">
                    <h3 class="text-[10px] font-bold text-cyan-500/80 uppercase tracking-widest mb-4">Transaction_History.db</h3>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left mono text-[11px]">
                            <thead>
                                <tr class="text-slate-500 border-b border-white/5">
                                    <th class="pb-2 font-medium">TIMESTAMP</th>
                                    <th class="pb-2 font-medium">UID</th>
                                    <th class="pb-2 font-medium">TYPE</th>
                                    <th class="pb-2 font-medium text-right">AMOUNT</th>
                                </tr>
                            </thead>
                            <tbody id="history-body">
                                </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="lg:col-span-5 space-y-6">
                <div class="neon-border-cyan glass-dark p-8 rounded-[2rem]">
                    <h3 class="text-white font-bold text-lg mb-8 flex items-center gap-2">
                        <span class="w-1.5 h-6 bg-cyan-500 rounded-full inline-block"></span>
                        Credit Top-Up
                    </h3>
                    <div class="space-y-6">
                        <div class="space-y-3">
                            <label class="block text-[10px] mono text-slate-500 uppercase font-bold tracking-widest">Deposit Amount</label>
                            <div class="relative group">
                                <input type="number" id="amount" placeholder="0.00" 
                                    class="w-full bg-black/40 border border-white/5 rounded-xl py-4 px-6 text-white focus:outline-none focus:border-cyan-500/50 transition-all font-bold text-lg">
                                <div class="absolute right-4 top-1/2 -translate-y-1/2 text-cyan-500/20 font-bold italic text-sm">RWF</div>
                            </div>
                        </div>
                        <button onclick="sendTopUp()" 
                            class="w-full bg-white text-black font-black uppercase tracking-widest text-xs py-5 rounded-xl hover:bg-cyan-400 hover:shadow-[0_0_25px_rgba(34,211,238,0.4)] active:scale-[0.97] transition-all duration-300">
                            Confirm Transaction
                        </button>
                    </div>
                </div>

                <div class="neon-border-cyan glass-dark rounded-2xl p-6 h-48 flex flex-col bg-black/20">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-[10px] font-bold text-cyan-500/80 uppercase tracking-widest">Console</h3>
                    </div>
                    <div id="logs" class="flex-grow overflow-y-auto space-y-2 pr-2 mono text-[10px] text-slate-500">
                        <p class="text-cyan-500/40 italic">> System Ready.</p>
                    </div>
                </div>
            </div>

        </div>
    </main>

    <script>
        const socket = io(`http://${window.location.hostname}:5001`);
        const logContainer = document.getElementById('logs');
        const historyBody = document.getElementById('history-body');

        function addLog(msg, isHighlight = false) {
            const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const p = document.createElement('p');
            p.className = `py-1 ${isHighlight ? 'text-cyan-400' : 'text-slate-500'}`;
            p.innerHTML = `<span class="opacity-30 mr-2">[${time}]</span> > ${msg}`;
            logContainer.prepend(p);
        }

        function addHistoryRow(data) {
            const row = document.createElement('tr');
            row.className = "border-b border-white/5 animate-pulse text-cyan-100";
            const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });
            
            row.innerHTML = `
                <td class="py-3 opacity-50">${time}</td>
                <td class="py-3">${data.uid.substring(0,8)}..</td>
                <td class="py-3 text-[9px]"><span class="bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded">${data.type || 'TOP-UP'}</span></td>
                <td class="py-3 text-right font-bold text-cyan-400">+${data.amount}</td>
            `;
            historyBody.prepend(row);
            setTimeout(() => row.classList.remove('animate-pulse', 'text-cyan-100'), 2000);
        }

        socket.on('connect', () => {
            document.getElementById('conn-status-dot').className = "w-2 h-2 bg-cyan-400 rounded-full status-pulse";
            document.getElementById('conn-status-text').innerText = "System Live";
            addLog("Uplink Established", true);
        });

        socket.on('update_ui', (data) => {
            if(data.uid) {
                document.getElementById('card-uid').innerText = data.uid;
            }
            if(data.balance !== undefined) {
                document.getElementById('card-balance').innerText = data.balance;
            }
            if(data.type === 'TOP-UP') {
                addLog(`Transaction Verified: +${data.amount} RWF`, true);
                addHistoryRow(data);
            } else {
                addLog(`Card Detected: ${data.uid}`);
            }
        });

        async function sendTopUp() {
            const uid = document.getElementById('card-uid').innerText;
            const amount = document.getElementById('amount').value;
            if(uid === "_WAITING_FOR_TAP_" || !amount) return alert("Scan card first!");

            try {
                addLog(`Syncing transaction: ${amount} RWF...`);
                await fetch(`http://${window.location.hostname}:5001/topup`, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({ uid: uid, amount: parseInt(amount) })
                });
                document.getElementById('amount').value = '';
            } catch (err) {
                addLog("Error: API Gateway Unreachable", false);
            }
        }
    </script>
</body>
</html>