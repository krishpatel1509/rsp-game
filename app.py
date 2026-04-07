import streamlit as st
import random
from collections import Counter

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RPS · BEST OF 5",
    page_icon="✊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Session state ─────────────────────────────────────────────────────────────
DEFAULTS = {
    # Set-level
    "player_sets":   0,
    "ai_sets":       0,
    # Current round within the set (1–5)
    "round_in_set":  0,
    # Scores within the current set
    "set_player_w":  0,
    "set_ai_w":      0,
    "set_ties":      0,
    # Total rounds ever played
    "total_rounds":  0,
    # AI prediction engine
    "history":       [],   # all user moves ever
    # Last move info
    "last_result":   None,
    "last_player":   None,
    "last_ai":       None,
    # Set result popup
    "set_over":      False,
    "set_winner":    None,   # "player" | "ai" | "tie"
    # Log
    "set_log":       [],     # list of {"set":n, "winner":..., "score":"3-1"}
    "round_log":     [],     # within current set
    # Misc
    "streak":        0,
    "best_streak":   0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── AI Engine (Hardened) ──────────────────────────────────────────────────────
BEATS = {"R": "P", "P": "S", "S": "R"}   # what beats the key
LOSES = {"R": "S", "P": "R", "S": "P"}   # what the key beats

def ai_predict(history: list) -> str:
    """
    Multi-layer prediction — returns what the AI *expects* the user to play next.
    Layer 1 – Spam detection:   if last 3 moves are identical → predict same again
    Layer 2 – Markov-2 chain:   look at what user played after the last 2-move sequence
    Layer 3 – Markov-1 chain:   look at what user played after the last move
    Layer 4 – Global frequency: pick user's most-played move
    Layer 5 – Random fallback
    """
    if len(history) < 2:
        return random.choice(["R", "P", "S"])

    # Layer 1: spam detection (very fast)
    if len(history) >= 3 and history[-1] == history[-2] == history[-3]:
        return history[-1]

    # Layer 2: Markov-2
    if len(history) >= 3:
        pattern = (history[-2], history[-1])
        after   = [history[i+2] for i in range(len(history)-2)
                   if (history[i], history[i+1]) == pattern]
        if len(after) >= 2:
            return Counter(after).most_common(1)[0][0]

    # Layer 3: Markov-1
    last  = history[-1]
    after = [history[i+1] for i in range(len(history)-1) if history[i] == last]
    if len(after) >= 2:
        return Counter(after).most_common(1)[0][0]

    # Layer 4: global frequency
    freq = Counter(history)
    return freq.most_common(1)[0][0]

def smart_ai_choice(history: list) -> str:
    """Counter the predicted move. 92 % confidence, 8 % random noise."""
    predicted = ai_predict(history)
    counter   = BEATS[predicted]
    return counter if random.random() < 0.92 else random.choice(["R", "P", "S"])

def determine_result(player: str, ai: str) -> str:
    if player == ai:        return "tie"
    if LOSES[ai] == player: return "win"
    return "lose"

# ── Constants ─────────────────────────────────────────────────────────────────
EMOJI = {"R": "✊", "P": "✋", "S": "✌️"}
NAME  = {"R": "ROCK", "P": "PAPER", "S": "SCISSORS"}
MSGS  = {
    "win":  ["YOU WIN!", "VICTORY!", "NICE MOVE!", "UNSTOPPABLE!"],
    "lose": ["I WIN!", "PREDICTED YOU!", "TOO EASY!", "OUTSMARTED!"],
    "tie":  ["DRAW!", "STALEMATE!", "TIE!", "EQUAL POWER!"],
}
SET_MSGS = {
    "player": ["SET YOURS!", "YOU TOOK IT!", "WELL PLAYED!", "SET WIN!"],
    "ai":     ["AI WINS SET!", "SET MINE!", "I OWN THIS!", "DOMINATED!"],
    "tie":    ["SET TIED!", "EVEN SETS!", "DEAD HEAT!"],
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bungee+Shade&family=Bungee&family=Share+Tech+Mono&display=swap');

:root {
  --bg:        #070710;
  --surface:   #0f0f1c;
  --panel:     #161628;
  --neon-blue: #00f0ff;
  --neon-pink: #ff2d78;
  --neon-gold: #ffd700;
  --neon-grn:  #39ff14;
  --neon-pur:  #bf5fff;
  --text:      #dde0ff;
  --muted:     #44446a;
}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--text);font-family:'Share Tech Mono',monospace;}
[data-testid="stHeader"]{background:transparent!important;}
[data-testid="stSidebar"]{display:none;}
.block-container{max-width:780px;padding-top:.8rem!important;}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:9999;
  background:repeating-linear-gradient(to bottom,transparent 0,transparent 3px,rgba(0,0,0,.13) 3px,rgba(0,0,0,.13) 4px);}

/* Title */
.game-title{font-family:'Bungee Shade',cursive;font-size:clamp(1.8rem,5vw,3rem);text-align:center;
  background:linear-gradient(135deg,var(--neon-blue),var(--neon-pink));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  letter-spacing:3px;margin:.2rem 0;animation:tpulse 3s ease-in-out infinite;}
@keyframes tpulse{0%,100%{filter:drop-shadow(0 0 10px #00f0ff55);}50%{filter:drop-shadow(0 0 24px #ff2d7877);}}
.subtitle{text-align:center;color:var(--muted);font-size:.68rem;letter-spacing:6px;text-transform:uppercase;margin-bottom:1rem;}

/* Set tracker */
.set-tracker{display:flex;align-items:center;justify-content:center;gap:.5rem;margin:.4rem 0 1rem;}
.set-pip{width:22px;height:22px;border-radius:50%;border:2px solid var(--muted);
  display:flex;align-items:center;justify-content:center;font-size:.55rem;
  font-family:'Bungee',cursive;transition:all .3s;}
.set-pip.player-win{background:var(--neon-blue);border-color:var(--neon-blue);box-shadow:0 0 10px #00f0ff88;color:#000;}
.set-pip.ai-win{background:var(--neon-pink);border-color:var(--neon-pink);box-shadow:0 0 10px #ff2d7888;color:#fff;}
.set-pip.tie-pip{background:var(--muted);border-color:var(--muted);color:#fff;}
.set-label{font-family:'Bungee',cursive;font-size:.6rem;letter-spacing:2px;color:var(--muted);}

/* Round progress */
.round-progress{display:flex;align-items:center;justify-content:center;gap:.4rem;margin-bottom:.8rem;}
.round-dot{width:14px;height:14px;border-radius:50%;border:1.5px solid var(--muted);transition:all .3s;}
.round-dot.win-dot {background:var(--neon-grn); border-color:var(--neon-grn); box-shadow:0 0 6px #39ff1466;}
.round-dot.lose-dot{background:var(--neon-pink);border-color:var(--neon-pink);box-shadow:0 0 6px #ff2d7866;}
.round-dot.tie-dot {background:var(--muted);    border-color:var(--muted);}
.round-dot.cur-dot {border-color:var(--neon-gold);animation:dotPulse 1s ease-in-out infinite;}
@keyframes dotPulse{0%,100%{box-shadow:0 0 4px #ffd70066;}50%{box-shadow:0 0 12px #ffd700bb;}}
.round-label{font-size:.6rem;letter-spacing:3px;color:var(--muted);font-family:'Bungee',cursive;}

/* Scoreboard */
.scoreboard{display:grid;grid-template-columns:1fr auto 1fr;gap:1rem;margin:.6rem 0;}
.score-card{background:var(--panel);border-radius:14px;padding:.9rem .6rem;text-align:center;border:1px solid;position:relative;overflow:hidden;}
.score-card::before{content:"";position:absolute;inset:0;background:linear-gradient(135deg,rgba(255,255,255,.04),transparent);pointer-events:none;}
.score-card.player{border-color:var(--neon-blue);box-shadow:0 0 14px #00f0ff2a;}
.score-card.ai{border-color:var(--neon-pink);box-shadow:0 0 14px #ff2d782a;}
.score-card.misc{border-color:var(--muted);}
.score-label{font-family:'Bungee',cursive;font-size:.55rem;letter-spacing:3px;opacity:.45;margin-bottom:.2rem;}
.score-num{font-family:'Bungee',cursive;font-size:2.6rem;line-height:1;}
.score-card.player .score-num{color:var(--neon-blue);text-shadow:0 0 10px #00f0ff55;}
.score-card.ai     .score-num{color:var(--neon-pink); text-shadow:0 0 10px #ff2d7855;}
.score-card.misc   .score-num{color:var(--muted);font-size:1.6rem;}
.vs-badge{display:flex;align-items:center;justify-content:center;font-family:'Bungee',cursive;
  font-size:1.3rem;color:var(--neon-gold);text-shadow:0 0 10px #ffd70055;animation:vspulse 1.5s ease-in-out infinite;}
@keyframes vspulse{0%,100%{transform:scale(1);}50%{transform:scale(1.22);}}
.mini-stats{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;margin-bottom:1rem;}

/* Arena */
.arena{background:var(--panel);border:1px solid #ffffff0d;border-radius:20px;
  padding:1.6rem 1rem 1.2rem;text-align:center;position:relative;overflow:hidden;margin-bottom:1rem;}
.arena::before{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse at 50% 0%,#00f0ff08 0%,transparent 65%);}
.arena-row{display:flex;align-items:center;justify-content:center;gap:2rem;min-height:110px;}
.fighter{display:flex;flex-direction:column;align-items:center;gap:.3rem;width:120px;}
.fighter-label{font-size:.55rem;letter-spacing:3px;opacity:.4;text-transform:uppercase;}
.fighter-emoji{font-size:4.6rem;line-height:1;display:inline-block;}
.fighter-emoji.player-side{filter:drop-shadow(0 0 10px #00f0ff44);}
.fighter-emoji.ai-side    {filter:drop-shadow(0 0 10px #ff2d7844);}
.fighter-emoji.idle{animation:bob 2.6s ease-in-out infinite;}
@keyframes bob{0%,100%{transform:translateY(0);}50%{transform:translateY(-9px);}}
.fighter-emoji.reveal{animation:popIn .5s cubic-bezier(.22,1.8,.36,1) forwards;}
@keyframes popIn{0%{transform:scale(0) rotate(-180deg);opacity:0;}100%{transform:scale(1) rotate(0);opacity:1;}}
.fighter-emoji.winner{animation:winGlow .85s ease-in-out infinite alternate;}
@keyframes winGlow{from{transform:scale(1);filter:drop-shadow(0 0 6px #39ff1466);}to{transform:scale(1.18);filter:drop-shadow(0 0 24px #39ff14aa);}}
.fighter-emoji.loser{animation:loseFade .7s ease forwards;}
@keyframes loseFade{to{opacity:.18;transform:scale(.8);filter:grayscale(1);}}
.vs-divider{font-family:'Bungee',cursive;font-size:1.6rem;color:var(--neon-gold);text-shadow:0 0 10px #ffd70055;}
.vs-divider::before,.vs-divider::after{content:"";display:block;height:50px;width:2px;
  background:linear-gradient(to bottom,transparent,var(--neon-gold),transparent);margin:.3rem auto;}
.result-banner{font-family:'Bungee',cursive;font-size:1.3rem;letter-spacing:4px;
  padding:.5rem 1.3rem;border-radius:12px;display:inline-block;margin-top:.8rem;
  animation:bannerPop .4s cubic-bezier(.22,1.8,.36,1) forwards;}
@keyframes bannerPop{from{transform:scale(.3);opacity:0;}to{transform:scale(1);opacity:1;}}
.result-banner.win {background:#39ff1415;color:var(--neon-grn); border:1px solid var(--neon-grn); box-shadow:0 0 16px #39ff1433;}
.result-banner.lose{background:#ff2d7815;color:var(--neon-pink);border:1px solid var(--neon-pink);box-shadow:0 0 16px #ff2d7833;}
.result-banner.tie {background:#ffd70015;color:var(--neon-gold);border:1px solid var(--neon-gold);box-shadow:0 0 16px #ffd70033;}
.result-sub{font-size:.7rem;letter-spacing:2px;opacity:.5;margin-top:.25rem;}

/* Set result overlay */
.set-overlay{background:var(--surface);border:2px solid;border-radius:20px;
  padding:2rem 1.5rem;text-align:center;margin-bottom:1rem;
  animation:overlayIn .5s cubic-bezier(.22,1.8,.36,1) forwards;}
@keyframes overlayIn{from{transform:scale(.6) translateY(30px);opacity:0;}to{transform:scale(1) translateY(0);opacity:1;}}
.set-overlay.player-win-ov{border-color:var(--neon-blue);box-shadow:0 0 40px #00f0ff22;}
.set-overlay.ai-win-ov    {border-color:var(--neon-pink); box-shadow:0 0 40px #ff2d7822;}
.set-overlay.tie-ov       {border-color:var(--neon-gold); box-shadow:0 0 40px #ffd70022;}
.set-title{font-family:'Bungee',cursive;font-size:2.2rem;letter-spacing:4px;margin-bottom:.4rem;}
.set-score{font-size:.9rem;letter-spacing:3px;opacity:.55;margin-bottom:1.2rem;}

/* Buttons */
[data-testid="stBaseButton-secondary"]{
  background:#0f0f1c!important;border:2px solid #ffffff12!important;
  border-radius:16px!important;padding:1.4rem .5rem!important;
  font-family:'Bungee',cursive!important;color:#555577!important;
  font-size:.76rem!important;letter-spacing:2px!important;
  min-height:110px!important;transition:all .2s!important;}
[data-testid="stBaseButton-secondary"]:hover{
  border-color:var(--neon-blue)!important;box-shadow:0 0 14px #00f0ff55!important;
  color:var(--neon-blue)!important;transform:translateY(-5px) scale(1.04)!important;}
[data-testid="stBaseButton-secondary"]:active{transform:scale(.96)!important;}

/* Log */
.log-row{display:flex;justify-content:space-between;align-items:center;
  padding:.35rem .7rem;border-radius:8px;font-size:.74rem;margin-bottom:.2rem;background:var(--surface);}
.log-row.win-r {border-left:3px solid var(--neon-grn);}
.log-row.lose-r{border-left:3px solid var(--neon-pink);}
.log-row.tie-r {border-left:3px solid var(--muted);}
.log-res{font-family:'Bungee',cursive;font-size:.6rem;letter-spacing:2px;}
.log-res.win {color:var(--neon-grn);}
.log-res.lose{color:var(--neon-pink);}
.log-res.tie {color:var(--neon-gold);}

.streak-bar{text-align:center;font-size:.68rem;letter-spacing:2px;color:var(--neon-gold);min-height:1.3rem;margin-bottom:.4rem;}
.ai-warning{text-align:center;font-size:.58rem;letter-spacing:3px;color:#1e1e38;margin:1rem 0 .3rem;}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def round_dot_html(round_log):
    """Build 5 dots showing current set progress."""
    dots = ""
    for i in range(5):
        if i < len(round_log):
            r = round_log[i]["result"]
            cls = "win-dot" if r == "win" else "lose-dot" if r == "lose" else "tie-dot"
        elif i == len(round_log) and len(round_log) < 5:
            cls = "cur-dot"
        else:
            cls = ""
        dots += f'<div class="round-dot {cls}"></div>'
    return f'<div class="round-progress"><span class="round-label">ROUND</span>{dots}<span class="round-label">OF 5</span></div>'

def set_pip_row():
    """Historical set pip icons."""
    log  = st.session_state.set_log
    pips = ""
    for s in log:
        if s["winner"] == "player":
            pips += '<div class="set-pip player-win">P</div>'
        elif s["winner"] == "ai":
            pips += '<div class="set-pip ai-win">A</div>'
        else:
            pips += '<div class="set-pip tie-pip">-</div>'
    if not log:
        return ""
    return (f'<div class="set-tracker">'
            f'<span class="set-label">SETS</span>{pips}</div>')

# ── Title ─────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="game-title">ROCK · PAPER · SCISSORS</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">⚡ Best of 5 Rounds · Hard Mode AI ⚡</p>', unsafe_allow_html=True)

# ── Set history pips ──────────────────────────────────────────────────────────
st.markdown(set_pip_row(), unsafe_allow_html=True)

# ── SET OVER overlay ──────────────────────────────────────────────────────────
if st.session_state.set_over:
    sw  = st.session_state.set_winner
    pw  = st.session_state.set_player_w
    aw  = st.session_state.set_ai_w
    tw  = st.session_state.set_ties
    ov_cls = "player-win-ov" if sw == "player" else "ai-win-ov" if sw == "ai" else "tie-ov"
    color  = "var(--neon-blue)" if sw == "player" else "var(--neon-pink)" if sw == "ai" else "var(--neon-gold)"
    msg    = random.choice(SET_MSGS[sw])
    label  = "🏆 YOU WIN THE SET!" if sw == "player" else "🤖 AI WINS THE SET!" if sw == "ai" else "🤝 SET TIED!"

    st.markdown(
        f'<div class="set-overlay {ov_cls}">'
        f'<div class="set-title" style="color:{color}">{msg}</div>'
        f'<div style="font-family:Bungee,cursive;font-size:1rem;color:{color}">{label}</div>'
        f'<div class="set-score">ROUNDS: YOU {pw} — AI {aw} — TIES {tw}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    col_next, col_skip = st.columns(2)
    with col_next:
        if st.button("▶  NEXT SET", key="next_set", use_container_width=True):
            st.session_state.round_in_set = 0
            st.session_state.set_player_w = 0
            st.session_state.set_ai_w     = 0
            st.session_state.set_ties     = 0
            st.session_state.set_over     = False
            st.session_state.set_winner   = None
            st.session_state.last_result  = None
            st.session_state.last_player  = None
            st.session_state.last_ai      = None
            st.session_state.round_log    = []
            st.rerun()
    with col_skip:
        if st.button("↺  FULL RESET", key="reset_from_set", use_container_width=True):
            for k, v in DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()
    st.stop()

# ── Scoreboards ───────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="scoreboard">'
    f'<div class="score-card player"><div class="score-label">SETS — YOU</div>'
    f'<div class="score-num">{st.session_state.player_sets}</div></div>'
    f'<div class="vs-badge">VS</div>'
    f'<div class="score-card ai"><div class="score-label">SETS — A.I.</div>'
    f'<div class="score-num">{st.session_state.ai_sets}</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

total    = st.session_state.player_sets + st.session_state.ai_sets
win_rate = (st.session_state.player_sets / total * 100) if total else 0
st.markdown(
    f'<div class="mini-stats">'
    f'<div class="score-card misc"><div class="score-label">ROUND IN SET</div>'
    f'<div class="score-num">{st.session_state.round_in_set}/5</div></div>'
    f'<div class="score-card misc"><div class="score-label">TOTAL ROUNDS</div>'
    f'<div class="score-num">{st.session_state.total_rounds}</div></div>'
    f'<div class="score-card misc"><div class="score-label">SET WIN %</div>'
    f'<div class="score-num">{win_rate:.0f}%</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

# Current set score
st.markdown(
    f'<div class="scoreboard" style="margin-top:-.4rem;margin-bottom:.6rem;">'
    f'<div class="score-card player" style="padding:.6rem;">'
    f'<div class="score-label" style="font-size:.5rem;">THIS SET — YOU</div>'
    f'<div class="score-num" style="font-size:1.8rem;">{st.session_state.set_player_w}</div></div>'
    f'<div class="vs-badge" style="font-size:.9rem;">SET</div>'
    f'<div class="score-card ai" style="padding:.6rem;">'
    f'<div class="score-label" style="font-size:.5rem;">THIS SET — A.I.</div>'
    f'<div class="score-num" style="font-size:1.8rem;">{st.session_state.set_ai_w}</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

# Round progress dots
st.markdown(round_dot_html(st.session_state.round_log), unsafe_allow_html=True)

# Streak
if st.session_state.streak > 1:
    st.markdown(f'<div class="streak-bar">🔥 {st.session_state.streak} WIN STREAK &nbsp;|&nbsp; BEST: {st.session_state.best_streak}</div>', unsafe_allow_html=True)
elif st.session_state.best_streak > 0:
    st.markdown(f'<div class="streak-bar">BEST STREAK: {st.session_state.best_streak}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="streak-bar">&nbsp;</div>', unsafe_allow_html=True)

# ── Arena ─────────────────────────────────────────────────────────────────────
p = st.session_state.last_player
a = st.session_state.last_ai
r = st.session_state.last_result

if r is None:
    p_em, a_em = "✊", "✊"
    p_cls      = "idle player-side"
    a_cls      = "idle ai-side"
    p_name     = "READY?"
    a_name     = "READY?"
    banner     = ""
else:
    p_em   = EMOJI[p]
    a_em   = EMOJI[a]
    p_cls  = "reveal player-side " + ("winner" if r == "win" else "loser" if r == "lose" else "")
    a_cls  = "reveal ai-side "     + ("winner" if r == "lose" else "loser" if r == "win" else "")
    p_name = NAME[p]
    a_name = NAME[a]
    desc   = (NAME[p] + " beats " + NAME[a] if r == "win" else
              NAME[a] + " beats " + NAME[p] if r == "lose" else
              "Both chose " + NAME[p])
    msg    = random.choice(MSGS[r])
    banner = ('<div><div class="result-banner ' + r + '">' + msg + '</div>'
              '<p class="result-sub">' + desc + '</p></div>')

st.markdown(
    '<div class="arena"><div class="arena-row">'
    '<div class="fighter"><span class="fighter-label">YOU</span>'
    '<span class="fighter-emoji ' + p_cls + '">' + p_em + '</span>'
    '<span class="fighter-label">' + p_name + '</span></div>'
    '<div class="vs-divider">VS</div>'
    '<div class="fighter"><span class="fighter-label">A.I.</span>'
    '<span class="fighter-emoji ' + a_cls + '">' + a_em + '</span>'
    '<span class="fighter-label">' + a_name + '</span></div>'
    '</div>' + banner + '</div>',
    unsafe_allow_html=True
)

# ── Weapon buttons ────────────────────────────────────────────────────────────
st.markdown('<div style="text-align:center;font-size:.6rem;letter-spacing:4px;color:var(--muted);margin-bottom:.7rem;">— CHOOSE YOUR WEAPON —</div>', unsafe_allow_html=True)

def play(choice: str):
    ai_move = smart_ai_choice(st.session_state.history)
    result  = determine_result(choice, ai_move)

    st.session_state.last_player  = choice
    st.session_state.last_ai      = ai_move
    st.session_state.last_result  = result
    st.session_state.total_rounds += 1
    st.session_state.history.append(choice)
    st.session_state.round_in_set += 1
    st.session_state.round_log.append({"result": result, "player": choice, "ai": ai_move})

    if result == "win":
        st.session_state.set_player_w += 1
        st.session_state.streak       += 1
        st.session_state.best_streak   = max(st.session_state.streak, st.session_state.best_streak)
    elif result == "lose":
        st.session_state.set_ai_w += 1
        st.session_state.streak    = 0
    else:
        st.session_state.set_ties += 1
        st.session_state.streak    = 0

    # After 5 rounds → decide set winner
    if st.session_state.round_in_set == 5:
        pw = st.session_state.set_player_w
        aw = st.session_state.set_ai_w
        sw = "player" if pw > aw else "ai" if aw > pw else "tie"
        st.session_state.set_winner = sw
        st.session_state.set_over   = True
        if sw == "player":
            st.session_state.player_sets += 1
        elif sw == "ai":
            st.session_state.ai_sets += 1
        st.session_state.set_log.append({
            "set":    len(st.session_state.set_log) + 1,
            "winner": sw,
            "score":  f"{pw}-{aw}",
        })

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("✊\n\nROCK", key="rock", use_container_width=True):
        play("R"); st.rerun()
with col2:
    if st.button("✋\n\nPAPER", key="paper", use_container_width=True):
        play("P"); st.rerun()
with col3:
    if st.button("✌️\n\nSCISSORS", key="scissors", use_container_width=True):
        play("S"); st.rerun()

# ── Battle log ────────────────────────────────────────────────────────────────
if st.session_state.round_log:
    with st.expander("📋  CURRENT SET LOG", expanded=False):
        rows = ""
        for i, e in enumerate(st.session_state.round_log):
            rows += (f'<div class="log-row {e["result"]}-r">'
                     f'<span style="color:var(--muted);width:50px">RD {i+1}</span>'
                     f'<span>{EMOJI[e["player"]]} {NAME[e["player"]]}</span>'
                     f'<span style="color:var(--muted)">vs</span>'
                     f'<span>{EMOJI[e["ai"]]} {NAME[e["ai"]]}</span>'
                     f'<span class="log-res {e["result"]}">{e["result"].upper()}</span>'
                     f'</div>')
        st.markdown(rows, unsafe_allow_html=True)

if st.session_state.set_log:
    with st.expander("🏆  SET HISTORY", expanded=False):
        rows = ""
        for s in reversed(st.session_state.set_log):
            w   = s["winner"]
            cls = "win-r" if w == "player" else "lose-r" if w == "ai" else "tie-r"
            lbl = "YOU" if w == "player" else "A.I." if w == "ai" else "TIE"
            res = "win" if w == "player" else "lose" if w == "ai" else "tie"
            rows += (f'<div class="log-row {cls}">'
                     f'<span style="color:var(--muted)">SET {s["set"]}</span>'
                     f'<span>Score: {s["score"]}</span>'
                     f'<span class="log-res {res}">{lbl} WINS</span>'
                     f'</div>')
        st.markdown(rows, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown('<div class="ai-warning">⚠️ A.I. DETECTS SPAM · ADAPTS TO PATTERNS · COUNTERS EVERY MOVE ⚠️</div>', unsafe_allow_html=True)

if st.button("↺  RESET EVERYTHING", key="reset"):
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.rerun()