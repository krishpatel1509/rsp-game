import streamlit as st
import random
import json
import os
import time
import math
from collections import Counter
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="RPS ARENA · ULTIMATE",
    page_icon="⚔️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  CROSS-SESSION PERSISTENCE  (rps_save.json)
# ═══════════════════════════════════════════════════════════════════════════════
SAVE_FILE = "rps_save.json"

def load_save():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def write_save(data: dict):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def save_profile(name: str, wins: int, losses: int, ties: int,
                 sets_won: int, best_streak: int, total_rounds: int):
    save = load_save()
    save["profile"] = {
        "name": name,
        "wins": wins, "losses": losses, "ties": ties,
        "sets_won": sets_won, "best_streak": best_streak,
        "total_rounds": total_rounds,
        "last_played": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    # Long-term history for AI (up to 500 moves)
    save["lt_history"] = save.get("lt_history", [])
    write_save(save)

def load_lt_history():
    save = load_save()
    return save.get("lt_history", [])

def append_lt_history(moves: list):
    save = load_save()
    hist = save.get("lt_history", [])
    hist = (hist + moves)[-500:]          # keep last 500 moves
    save["lt_history"] = hist
    write_save(save)

def load_leaderboard():
    save = load_save()
    return save.get("leaderboard", [])

def update_leaderboard(name: str, sets_won: int, win_pct: float, total_rounds: int):
    save   = load_save()
    board  = save.get("leaderboard", [])
    # Remove old entry for this player
    board  = [e for e in board if e.get("name") != name]
    board.append({
        "name": name,
        "sets_won": sets_won,
        "win_pct": round(win_pct, 1),
        "total_rounds": total_rounds,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    # Sort by sets_won desc, then win_pct desc
    board.sort(key=lambda x: (-x["sets_won"], -x["win_pct"]))
    board = board[:10]
    save["leaderboard"] = board
    write_save(save)

# ═══════════════════════════════════════════════════════════════════════════════
#  ACHIEVEMENTS
# ═══════════════════════════════════════════════════════════════════════════════
ACHIEVEMENTS = {
    "FIRST_BLOOD":  {"name": "First Blood",      "desc": "Win your first round",                     "icon": "🩸"},
    "HAT_TRICK":    {"name": "Hat Trick",         "desc": "3-round win streak",                       "icon": "🎩"},
    "ON_FIRE":      {"name": "On Fire",           "desc": "5-round win streak",                       "icon": "🔥"},
    "UNSTOPPABLE":  {"name": "Unstoppable",       "desc": "10-round win streak",                      "icon": "⚡"},
    "SET_MASTER":   {"name": "Set Master",        "desc": "Win 3 sets total",                         "icon": "👑"},
    "PERFECT_SET":  {"name": "Perfect Set",       "desc": "Win a set without dropping a round",       "icon": "💎"},
    "COMEBACK_KID": {"name": "Comeback Kid",      "desc": "Win a set after trailing 0-2",             "icon": "🦾"},
    "CENTURION":    {"name": "Centurion",         "desc": "Play 100 total rounds",                    "icon": "💯"},
    "CHAOS_AGENT":  {"name": "Chaos Agent",       "desc": "No repeated moves in 5 rounds",            "icon": "🎲"},
    "ROCK_STEADY":  {"name": "Rock Steady",       "desc": "Play Rock 15 times",                       "icon": "✊"},
    "PAPER_TRAIL":  {"name": "Paper Trail",       "desc": "Play Paper 15 times",                      "icon": "✋"},
    "SNIP_SNIP":    {"name": "Snip Snip",         "desc": "Play Scissors 15 times",                   "icon": "✌️"},
    "MIND_READER":  {"name": "Mind Reader",       "desc": "Stay unpredicted 5 rounds in a row",       "icon": "🧠"},
    "MARATHON":     {"name": "Marathon",          "desc": "Play 10 sets total",                       "icon": "🏃"},
    "SPEEDSTER":    {"name": "Speedster",         "desc": "Make a move in under 1 second",            "icon": "⚡"},
    "VETERAN":      {"name": "Veteran",           "desc": "Play 500 total rounds (career)",           "icon": "🎖️"},
    "UPSET":        {"name": "Upset",             "desc": "Beat HARD mode AI in a set",               "icon": "💥"},
    "TIEMASTER":    {"name": "Tie Master",        "desc": "Draw 10 rounds in total",                  "icon": "🤝"},
}

# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════
DEFAULTS = {
    # Profile
    "player_name":      "PLAYER",
    "profile_set":      False,
    # Mode: "solo" | "multi"
    "game_mode":        "solo",
    # Set-level
    "player_sets":      0,
    "ai_sets":          0,
    # Current round
    "round_in_set":     0,
    "set_player_w":     0,
    "set_ai_w":         0,
    "set_ties":         0,
    # Career stats
    "total_rounds":     0,
    "total_wins":       0,
    "total_losses":     0,
    "total_ties_all":   0,
    # AI history (session + loaded from file)
    "history":          [],
    "lt_history_loaded":False,
    # Last move
    "last_result":      None,
    "last_player":      None,
    "last_ai":          None,
    # Multiplayer last move
    "mp_p1_choice":     None,
    "mp_p2_choice":     None,
    "mp_stage":         "p1",   # "p1" | "p2" | "reveal"
    # Set result
    "set_over":         False,
    "set_winner":       None,
    # Logs
    "set_log":          [],
    "round_log":        [],
    # Streaks
    "streak":           0,
    "best_streak":      0,
    # Settings
    "difficulty":       "MEDIUM",
    "rounds_per_set":   5,
    "theme":            "CYBER",
    "sound_enabled":    True,
    # AI analytics
    "ai_predicted":     0,
    "ai_correct":       0,
    "last_ai_pred":     None,
    "unpredict_streak": 0,
    # Achievements
    "achievements":     [],
    "new_achievement":  None,
    # Misc
    "comeback_possible":False,
    "confirm_reset":    False,
    "pending_sound":    None,
    "pending_confetti": False,
    # Timer
    "round_start_time": None,
    "last_reaction_ms": None,
    "best_reaction_ms": None,
    # Comeback tracking  
    "ai_set_lead":      0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Load long-term history once per session
if not st.session_state.lt_history_loaded:
    lt = load_lt_history()
    if lt:
        # Prepend to session history (deduplicated conceptually)
        st.session_state.history = lt + st.session_state.history
    st.session_state.lt_history_loaded = True

# ═══════════════════════════════════════════════════════════════════════════════
#  AI ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
BEATS = {"R": "P", "P": "S", "S": "R"}
LOSES = {"R": "S", "P": "R", "S": "P"}
CHOICES = ["R", "P", "S"]

def calculate_entropy(history, window=10):
    if len(history) < 3:
        return 0.0
    recent = history[-window:]
    counts = Counter(recent)
    total  = len(recent)
    ent    = sum(-( c/total) * math.log2(c/total) for c in counts.values())
    return ent   # max ≈ 1.585

def ai_predict(history, difficulty):
    if len(history) < 2:
        return random.choice(CHOICES)

    # HARD: 3-step Markov chain
    if difficulty == "HARD" and len(history) >= 4:
        pat3  = tuple(history[-3:])
        after = [history[i+3] for i in range(len(history)-3)
                 if tuple(history[i:i+3]) == pat3]
        if len(after) >= 2:
            return Counter(after).most_common(1)[0][0]

    # Spam detection
    if len(history) >= 3 and history[-1] == history[-2] == history[-3]:
        return history[-1]

    # Markov-2
    if len(history) >= 3:
        pat   = (history[-2], history[-1])
        after = [history[i+2] for i in range(len(history)-2)
                 if (history[i], history[i+1]) == pat]
        if len(after) >= 2:
            return Counter(after).most_common(1)[0][0]

    # Markov-1
    last  = history[-1]
    after = [history[i+1] for i in range(len(history)-1) if history[i] == last]
    if len(after) >= 2:
        return Counter(after).most_common(1)[0][0]

    # Global frequency
    return Counter(history).most_common(1)[0][0]

def smart_ai_choice(history, difficulty):
    predicted = ai_predict(history, difficulty)
    st.session_state.last_ai_pred = predicted
    counter   = BEATS[predicted]
    if difficulty == "EASY":
        conf = 0.22
    elif difficulty == "MEDIUM":
        conf = 0.82
    else:   # HARD: adaptive to entropy
        ent   = calculate_entropy(history)
        max_e = math.log2(3)
        ratio = min(ent / max_e, 1.0) if max_e else 0
        conf  = 0.96 - (ratio * 0.20)   # range [0.76, 0.96]
    return counter if random.random() < conf else random.choice(CHOICES)

def determine_result(player, ai):
    if player == ai:        return "tie"
    if LOSES[ai] == player: return "win"
    return "lose"

# ═══════════════════════════════════════════════════════════════════════════════
#  ACHIEVEMENT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def unlock(key):
    if key not in st.session_state.achievements:
        st.session_state.achievements.append(key)
        st.session_state.new_achievement = key

def check_round_ach(result, choice):
    ss = st.session_state
    h  = ss.history
    if result == "win":
        unlock("FIRST_BLOOD")
    if ss.streak >= 3:  unlock("HAT_TRICK")
    if ss.streak >= 5:  unlock("ON_FIRE")
    if ss.streak >= 10: unlock("UNSTOPPABLE")
    if ss.total_rounds >= 100: unlock("CENTURION")
    if h.count("R") >= 15: unlock("ROCK_STEADY")
    if h.count("P") >= 15: unlock("PAPER_TRAIL")
    if h.count("S") >= 15: unlock("SNIP_SNIP")
    if ss.total_ties_all >= 10: unlock("TIEMASTER")
    if len(h) >= 5:
        last5 = h[-5:]
        if all(last5[i] != last5[i+1] for i in range(4)):
            unlock("CHAOS_AGENT")
    if ss.unpredict_streak >= 5: unlock("MIND_READER")
    # Speedster
    if ss.last_reaction_ms is not None and ss.last_reaction_ms < 1000:
        unlock("SPEEDSTER")
    # Career
    lt = load_lt_history()
    if len(lt) >= 500: unlock("VETERAN")

def check_set_ach():
    ss = st.session_state
    if ss.set_winner == "player":
        if ss.set_ai_w == 0:
            unlock("PERFECT_SET")
        if ss.comeback_possible:
            unlock("COMEBACK_KID")
        if ss.difficulty == "HARD":
            unlock("UPSET")
    total_sets = ss.player_sets + ss.ai_sets
    if total_sets >= 10: unlock("MARATHON")
    if ss.player_sets >= 3: unlock("SET_MASTER")

# ═══════════════════════════════════════════════════════════════════════════════
#  THEME SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
THEME_VARS = {
    "CYBER": """
        --bg:#06060f;--surface:#0d0d1e;--panel:#131326;
        --blue:#00eeff;--pink:#ff2060;--gold:#ffcc00;
        --grn:#00ff88;--pur:#cc44ff;--text:#d8deff;--muted:#3a3a6a;
        --btn-bg:#0d0d1e;--btn-border:#ffffff10;--card-bg:#131326;
    """,
    "LIGHT": """
        --bg:#f2f5ff;--surface:#ffffff;--panel:#e8ecfc;
        --blue:#0044cc;--pink:#cc0040;--gold:#886600;
        --grn:#006622;--pur:#6600bb;--text:#111133;--muted:#7788aa;
        --btn-bg:#ffffff;--btn-border:#c0cce8;--card-bg:#ffffff;
    """,
    "MINIMAL": """
        --bg:#0b0b0b;--surface:#141414;--panel:#1c1c1c;
        --blue:#dddddd;--pink:#999999;--gold:#bbbbbb;
        --grn:#cccccc;--pur:#888888;--text:#cccccc;--muted:#3a3a3a;
        --btn-bg:#141414;--btn-border:#282828;--card-bg:#1c1c1c;
    """,
}

def get_css(theme):
    tv  = THEME_VARS[theme]
    ext = ""
    if theme == "LIGHT":
        ext = """
        body::after{display:none!important;}
        .game-title{background:linear-gradient(135deg,var(--blue),var(--pink))!important;
            -webkit-background-clip:text!important;-webkit-text-fill-color:transparent!important;}
        """
    elif theme == "MINIMAL":
        ext = """
        @keyframes tpulse{0%,100%{filter:none}}
        .game-title{font-family:'Share Tech Mono',monospace!important;letter-spacing:10px!important;
            background:none!important;-webkit-text-fill-color:var(--text)!important;font-size:1.8rem!important;}
        body::after{display:none!important;}
        """
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Bungee&family=Share+Tech+Mono:wght@400&display=swap');
:root{{ {tv} }}
html,body,[data-testid="stAppViewContainer"]{{background:var(--bg)!important;color:var(--text);font-family:'Share Tech Mono',monospace;}}
[data-testid="stHeader"]{{background:transparent!important;}}
[data-testid="stSidebar"]{{display:none!important;}}
.block-container{{max-width:840px;padding-top:.6rem!important;}}
/* scanlines */
body::after{{content:"";position:fixed;inset:0;pointer-events:none;z-index:9999;
  background:repeating-linear-gradient(to bottom,transparent 0,transparent 2px,rgba(0,0,0,.1) 2px,rgba(0,0,0,.1) 3px);}}
/* grid bg */
body::before{{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
  background-image:linear-gradient(rgba(0,200,255,.025) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,200,255,.025) 1px,transparent 1px);
  background-size:50px 50px;}}
/* ── TITLE ── */
.game-title{{font-family:'Orbitron',sans-serif;font-weight:900;
  font-size:clamp(1.6rem,5vw,2.8rem);text-align:center;letter-spacing:5px;
  background:linear-gradient(90deg,var(--blue),#fff 40%,var(--pink));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-size:200%;
  animation:tpulse 3s ease-in-out infinite,shimmer 4s linear infinite;
  margin:.2rem 0;}}
@keyframes tpulse{{0%,100%{{filter:drop-shadow(0 0 8px #00eeff44);}}50%{{filter:drop-shadow(0 0 22px #ff206066);}}}}
@keyframes shimmer{{0%{{background-position:0%}}100%{{background-position:200%}}}}
.subtitle{{text-align:center;color:var(--muted);font-size:.6rem;letter-spacing:7px;
  text-transform:uppercase;margin-bottom:.6rem;}}
/* ── PROFILE BAR ── */
.profile-bar{{background:var(--surface);border:1px solid var(--muted)33;border-radius:14px;
  padding:.6rem 1.2rem;display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:.5rem;margin-bottom:.8rem;}}
.profile-name{{font-family:'Orbitron',sans-serif;font-weight:700;font-size:.75rem;
  letter-spacing:3px;color:var(--blue);}}
.profile-stat{{font-size:.58rem;letter-spacing:2px;color:var(--muted);}}
.profile-stat span{{color:var(--text);font-weight:700;}}
/* ── SETTINGS BAR ── */
.settings-row{{background:var(--surface);border:1px solid var(--muted)22;border-radius:14px;
  padding:.6rem 1rem;display:flex;gap:1.5rem;align-items:center;
  justify-content:center;flex-wrap:wrap;margin-bottom:.8rem;}}
.diff-badge{{display:inline-block;padding:.15rem .55rem;border-radius:6px;
  font-family:'Bungee',cursive;font-size:.55rem;letter-spacing:1px;border:1px solid;}}
/* ── SET TRACKER ── */
.set-tracker{{display:flex;align-items:center;justify-content:center;
  gap:.4rem;margin:.3rem 0 .7rem;flex-wrap:wrap;}}
.set-pip{{width:22px;height:22px;border-radius:50%;border:2px solid var(--muted);
  display:flex;align-items:center;justify-content:center;font-size:.55rem;
  font-family:'Bungee',cursive;transition:all .3s;}}
.set-pip.pw{{background:var(--blue);border-color:var(--blue);box-shadow:0 0 10px #00eeff66;color:#000;}}
.set-pip.aw{{background:var(--pink);border-color:var(--pink);box-shadow:0 0 10px #ff206066;color:#fff;}}
.set-pip.tw{{background:var(--muted);border-color:var(--muted);color:#fff;}}
/* ── ROUND DOTS ── */
.round-progress{{display:flex;align-items:center;justify-content:center;gap:.4rem;margin-bottom:.8rem;}}
.round-dot{{width:14px;height:14px;border-radius:50%;border:1.5px solid var(--muted);transition:all .35s;}}
.round-dot.wd{{background:var(--grn); border-color:var(--grn); box-shadow:0 0 6px #00ff8866;}}
.round-dot.ld{{background:var(--pink);border-color:var(--pink);box-shadow:0 0 6px #ff206066;}}
.round-dot.td{{background:var(--gold);border-color:var(--gold);}}
.round-dot.cd{{border-color:var(--gold);animation:cdPulse 1s ease-in-out infinite;}}
@keyframes cdPulse{{0%,100%{{box-shadow:0 0 4px #ffcc0055;}}50%{{box-shadow:0 0 14px #ffcc00cc;}}}}
.round-lbl{{font-size:.58rem;letter-spacing:3px;color:var(--muted);font-family:'Bungee',cursive;}}
/* ── SCOREBOARD ── */
.scoreboard{{display:grid;grid-template-columns:1fr auto 1fr;gap:.8rem;margin:.5rem 0;}}
.score-card{{background:var(--panel);border-radius:14px;padding:.9rem .6rem;
  text-align:center;border:1px solid;position:relative;overflow:hidden;}}
.score-card::before{{content:"";position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,.04),transparent);pointer-events:none;}}
.score-card.pl{{border-color:var(--blue);box-shadow:0 0 14px #00eeff1e;}}
.score-card.ai{{border-color:var(--pink);box-shadow:0 0 14px #ff20601e;}}
.score-card.ms{{border-color:var(--muted)33;}}
.sc-lbl{{font-family:'Bungee',cursive;font-size:.52rem;letter-spacing:3px;opacity:.4;margin-bottom:.2rem;}}
.sc-num{{font-family:'Orbitron',sans-serif;font-weight:900;font-size:2.6rem;line-height:1;}}
.score-card.pl .sc-num{{color:var(--blue);text-shadow:0 0 10px #00eeff44;}}
.score-card.ai .sc-num{{color:var(--pink);text-shadow:0 0 10px #ff206044;}}
.score-card.ms .sc-num{{color:var(--muted);font-size:1.5rem;}}
.vs-badge{{display:flex;align-items:center;justify-content:center;font-family:'Orbitron',sans-serif;
  font-weight:900;font-size:1.2rem;color:var(--gold);text-shadow:0 0 12px #ffcc0055;
  animation:vsp 1.6s ease-in-out infinite;}}
@keyframes vsp{{0%,100%{{transform:scale(1);}}50%{{transform:scale(1.25);}}}}
.mini-stats{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.5rem;margin-bottom:.8rem;}}
/* ── TIMER BAR ── */
.timer-wrap{{height:4px;background:var(--muted)33;border-radius:2px;
  margin:-.3rem 0 .8rem;overflow:hidden;}}
.timer-bar{{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--grn),var(--gold),var(--pink));
  transition:width .1s linear;}}
/* ── ARENA ── */
.arena{{background:var(--panel);border:1px solid #ffffff08;border-radius:22px;
  padding:1.8rem 1rem 1.2rem;text-align:center;position:relative;overflow:hidden;margin-bottom:1rem;}}
.arena::before{{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse at 50% 0%,#00eeff07 0%,transparent 65%);}}
.arena::after{{content:"ARENA";position:absolute;bottom:.6rem;right:1.2rem;
  font-family:'Orbitron',sans-serif;font-size:.4rem;letter-spacing:5px;color:#ffffff06;}}
.arena-row{{display:flex;align-items:center;justify-content:space-between;
  gap:1rem;min-height:160px;position:relative;}}
.fighter-box{{flex:1;display:flex;flex-direction:column;align-items:center;gap:.4rem;}}
.fighter-tag{{font-family:'Orbitron',sans-serif;font-size:.55rem;font-weight:700;letter-spacing:5px;}}
.fighter-tag.pt{{color:var(--blue);}}
.fighter-tag.at{{color:var(--pink);}}
/* hand container */
.hand-wrap{{width:130px;height:150px;display:flex;align-items:center;justify-content:center;
  position:relative;border-radius:18px;}}
.hand-wrap.ph{{background:radial-gradient(ellipse at center,#00eeff08,transparent 70%);
  border:1px solid #00eeff15;}}
.hand-wrap.ah{{background:radial-gradient(ellipse at center,#ff206008,transparent 70%);
  border:1px solid #ff206015;}}
.hand-emoji{{font-size:6.5rem;line-height:1;display:block;user-select:none;}}
.hand-wrap.ph .hand-emoji{{filter:drop-shadow(0 0 14px #00eeff66);}}
.hand-wrap.ah .hand-emoji{{filter:drop-shadow(0 0 14px #ff206066);transform:scaleX(-1);}}
/* States */
.hand-emoji.idle{{animation:float 2.8s ease-in-out infinite;}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-12px)}}}}
.hand-wrap.ah .hand-emoji.idle{{animation:floatR 2.8s ease-in-out infinite;}}
@keyframes floatR{{0%,100%{{transform:scaleX(-1) translateY(0)}}50%{{transform:scaleX(-1) translateY(-12px)}}}}
.hand-emoji.reveal{{animation:popIn .5s cubic-bezier(.22,1.8,.36,1) forwards;}}
@keyframes popIn{{0%{{transform:scale(0) rotate(-200deg);opacity:0;}}100%{{transform:scale(1) rotate(0);opacity:1;}}}}
.hand-wrap.ah .hand-emoji.reveal{{animation:popInR .5s cubic-bezier(.22,1.8,.36,1) forwards;}}
@keyframes popInR{{0%{{transform:scaleX(-1) scale(0) rotate(200deg);opacity:0;}}100%{{transform:scaleX(-1) scale(1) rotate(0);opacity:1;}}}}
.hand-emoji.winner{{animation:winPulse .9s ease-in-out infinite alternate;}}
@keyframes winPulse{{from{{transform:scale(1);filter:drop-shadow(0 0 16px #00ff88aa);}}
  to{{transform:scale(1.2);filter:drop-shadow(0 0 36px #00ff88ff) brightness(1.3);}}}}
.hand-wrap.ah .hand-emoji.winner{{animation:winPulseR .9s ease-in-out infinite alternate;}}
@keyframes winPulseR{{from{{transform:scaleX(-1) scale(1);filter:drop-shadow(0 0 16px #00ff88aa);}}
  to{{transform:scaleX(-1) scale(1.2);filter:drop-shadow(0 0 36px #00ff88ff) brightness(1.3);}}}}
.hand-emoji.loser{{animation:loseFade .6s ease forwards;}}
@keyframes loseFade{{to{{opacity:.12;transform:scale(.75);filter:grayscale(1) blur(1px);}}}}
.hand-wrap.ah .hand-emoji.loser{{animation:loseFadeR .6s ease forwards;}}
@keyframes loseFadeR{{to{{opacity:.12;transform:scaleX(-1) scale(.75);filter:grayscale(1) blur(1px);}}}}
/* VS center */
.vs-center{{display:flex;flex-direction:column;align-items:center;gap:.3rem;min-width:60px;}}
.vs-txt{{font-family:'Orbitron',sans-serif;font-weight:900;font-size:1.5rem;
  color:var(--gold);text-shadow:0 0 12px #ffcc0066;animation:vsp 1.6s ease-in-out infinite;}}
.vs-line{{width:2px;height:50px;background:linear-gradient(to bottom,transparent,var(--gold),transparent);opacity:.35;}}
.choice-lbl{{font-family:'Orbitron',sans-serif;font-size:.5rem;font-weight:700;
  letter-spacing:3px;color:var(--muted);min-height:.9rem;}}
/* ── RESULT BANNER ── */
.result-wrap{{text-align:center;padding-top:.8rem;}}
.result-banner{{font-family:'Orbitron',sans-serif;font-weight:900;
  font-size:clamp(1.1rem,4vw,1.7rem);letter-spacing:5px;
  padding:.55rem 2rem;border-radius:8px;display:inline-block;
  animation:bSlam .35s cubic-bezier(.22,1.8,.36,1) forwards;
  position:relative;overflow:hidden;}}
.result-banner::before{{content:"";position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(255,255,255,.12),transparent 50%);}}
@keyframes bSlam{{from{{transform:scale(.2) rotate(-4deg);opacity:0;}}to{{transform:none;opacity:1;}}}}
.result-banner.win{{background:#00ff8818;color:var(--grn);
  border:2px solid var(--grn);box-shadow:0 0 24px #00ff8833,inset 0 0 30px #00ff8810;}}
.result-banner.lose{{background:#ff206018;color:var(--pink);
  border:2px solid var(--pink);box-shadow:0 0 24px #ff206033,inset 0 0 30px #ff206010;}}
.result-banner.tie{{background:#ffcc0018;color:var(--gold);
  border:2px solid var(--gold);box-shadow:0 0 24px #ffcc0033,inset 0 0 30px #ffcc0010;}}
.result-sub{{font-size:.68rem;letter-spacing:3px;opacity:.45;margin-top:.3rem;}}
.reaction-time{{font-size:.58rem;letter-spacing:2px;color:var(--muted);margin-top:.2rem;}}
/* ── STREAK ── */
.streak-bar{{text-align:center;font-size:.66rem;letter-spacing:2px;
  color:var(--gold);min-height:1.3rem;margin-bottom:.4rem;}}
/* ── SET OVER ── */
.set-over-wrap{{background:var(--surface);border-radius:22px;padding:2.5rem 1.5rem;
  text-align:center;margin-bottom:1rem;position:relative;overflow:hidden;
  animation:sOverIn .5s cubic-bezier(.22,1.8,.36,1);}}
@keyframes sOverIn{{from{{transform:scale(.6) translateY(40px);opacity:0;}}to{{transform:none;opacity:1;}}}}
.set-over-wrap::before{{content:"";position:absolute;inset:-50%;
  background:conic-gradient(from 0deg,transparent,rgba(0,200,255,.03) 25%,transparent 50%,rgba(255,32,96,.03) 75%,transparent);
  animation:rotBg 8s linear infinite;}}
@keyframes rotBg{{to{{transform:rotate(360deg);}}}}
.set-over-wrap.pw{{border:2px solid var(--blue);box-shadow:0 0 50px #00eeff18;}}
.set-over-wrap.aw{{border:2px solid var(--pink);box-shadow:0 0 50px #ff206018;}}
.set-over-wrap.tw{{border:2px solid var(--gold);box-shadow:0 0 50px #ffcc0018;}}
.so-title{{font-family:'Orbitron',sans-serif;font-weight:900;
  font-size:clamp(1.6rem,5vw,2.6rem);letter-spacing:6px;position:relative;}}
.so-sub{{font-family:'Share Tech Mono',monospace;font-size:.72rem;
  letter-spacing:4px;opacity:.45;margin:.5rem 0 .8rem;}}
.so-score-row{{display:flex;justify-content:center;gap:2rem;margin:.6rem 0 1.2rem;
  font-family:'Orbitron',sans-serif;font-weight:900;font-size:2.2rem;}}
/* ── WEAPON BUTTONS ── */
[data-testid="stBaseButton-secondary"]{{
  background:var(--btn-bg)!important;border:1px solid var(--btn-border)!important;
  border-radius:18px!important;padding:1.6rem .5rem!important;
  font-family:'Orbitron',sans-serif!important;color:var(--muted)!important;
  font-size:.68rem!important;letter-spacing:3px!important;
  min-height:120px!important;transition:all .2s cubic-bezier(.4,0,.2,1)!important;
  position:relative!important;}}
[data-testid="stBaseButton-secondary"]:hover{{
  background:linear-gradient(135deg,var(--btn-bg),#051020)!important;
  border-color:var(--blue)!important;
  box-shadow:0 0 20px #00eeff44,0 -3px 0 var(--blue) inset!important;
  color:var(--blue)!important;transform:translateY(-7px) scale(1.05)!important;}}
[data-testid="stBaseButton-secondary"]:active{{transform:scale(.95)!important;}}
/* ── MULTIPLAYER ── */
.mp-player-block{{background:var(--panel);border-radius:16px;padding:1.5rem;
  text-align:center;position:relative;overflow:hidden;}}
.mp-player-block.p1b{{border:1px solid var(--blue);box-shadow:0 0 20px #00eeff18;}}
.mp-player-block.p2b{{border:1px solid var(--pink);box-shadow:0 0 20px #ff206018;}}
.mp-waiting{{font-family:'Orbitron',sans-serif;font-size:3rem;
  animation:float 2s ease-in-out infinite;display:block;}}
.mp-chosen{{font-size:3rem;display:block;animation:popIn .4s cubic-bezier(.22,1.8,.36,1);}}
/* ── ANALYTICS ── */
.acc-wrap{{background:var(--surface);border-radius:10px;height:10px;overflow:hidden;margin:.25rem 0;}}
.acc-fill{{height:100%;border-radius:10px;transition:width .7s ease;}}
.acc-fill.ai-fill{{background:linear-gradient(90deg,var(--pink),#ff006688);}}
.acc-fill.pl-fill{{background:linear-gradient(90deg,var(--blue),#0066ff88);}}
.insight-card{{background:var(--surface);border-radius:12px;
  padding:.7rem 1rem;margin:.4rem 0;font-size:.7rem;line-height:1.65;
  border-left:3px solid;}}
.insight-card.warn{{border-left-color:var(--pink);}}
.insight-card.ok  {{border-left-color:var(--grn);}}
.insight-card.info{{border-left-color:var(--gold);}}
.ins-label{{font-family:'Bungee',cursive;font-size:.5rem;letter-spacing:3px;
  color:var(--muted);margin-bottom:.3rem;}}
/* ── ACHIEVEMENTS ── */
.ach-grid{{display:flex;flex-wrap:wrap;gap:.5rem;}}
.ach-badge{{background:var(--surface);border:1px solid var(--muted)44;border-radius:10px;
  padding:.4rem .7rem;font-size:.6rem;display:flex;align-items:center;gap:.4rem;transition:all .2s;}}
.ach-badge.on{{border-color:var(--gold)77;background:var(--panel);box-shadow:0 0 10px #ffcc0020;}}
.ach-badge.off{{opacity:.3;filter:grayscale(.7);}}
.ach-icon{{font-size:1rem;}}
.new-ach{{background:var(--panel);border:2px solid var(--gold);border-radius:14px;
  padding:.7rem 1.2rem;text-align:center;margin-bottom:.8rem;
  animation:achPop .5s cubic-bezier(.22,1.8,.36,1);}}
@keyframes achPop{{from{{transform:scale(.5) translateY(-20px);opacity:0;}}to{{transform:none;opacity:1;}}}}
/* ── LEADERBOARD ── */
.lb-row{{display:flex;align-items:center;gap:.6rem;padding:.45rem .8rem;
  border-radius:10px;margin-bottom:.2rem;background:var(--surface);font-size:.7rem;}}
.lb-row.me{{border-left:3px solid var(--blue);}}
.lb-rank{{font-family:'Orbitron',sans-serif;font-weight:700;width:24px;
  color:var(--gold);font-size:.65rem;}}
.lb-name{{flex:1;font-family:'Orbitron',sans-serif;font-size:.65rem;letter-spacing:2px;}}
/* ── LOG ── */
.log-row{{display:flex;justify-content:space-between;align-items:center;
  padding:.35rem .7rem;border-radius:8px;font-size:.72rem;margin-bottom:.2rem;background:var(--surface);}}
.log-row.wr{{border-left:3px solid var(--grn);}}
.log-row.lr{{border-left:3px solid var(--pink);}}
.log-row.tr{{border-left:3px solid var(--muted);}}
.log-res{{font-family:'Bungee',cursive;font-size:.58rem;letter-spacing:2px;}}
.log-res.w{{color:var(--grn);}} .log-res.l{{color:var(--pink);}} .log-res.t{{color:var(--gold);}}
/* ── MISC ── */
.sec-head{{font-family:'Bungee',cursive;font-size:.56rem;letter-spacing:5px;
  color:var(--muted);text-align:center;margin:.8rem 0 .4rem;opacity:.7;}}
.confirm-box{{background:var(--surface);border:2px solid var(--pink);border-radius:14px;
  padding:1rem 1.2rem;text-align:center;margin:.5rem 0;}}
.ai-warn{{text-align:center;font-size:.55rem;letter-spacing:4px;color:var(--muted);
  opacity:.25;margin:.8rem 0 .2rem;}}
.mode-tab{{display:inline-block;padding:.3rem .8rem;border-radius:8px;font-family:'Bungee',cursive;
  font-size:.6rem;letter-spacing:2px;cursor:pointer;margin:.15rem;border:1px solid;transition:all .2s;}}
.mode-tab.active{{background:var(--blue);border-color:var(--blue);color:#000;}}
.mode-tab.inactive{{border-color:var(--muted);color:var(--muted);}}
{ext}
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  SOUND ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
SOUNDS = {
    "win":     "[523,659,784,1047].forEach((f,i)=>{var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=f;o.type='sine';g.gain.setValueAtTime(0,a.currentTime+i*.1);g.gain.linearRampToValueAtTime(.18,a.currentTime+i*.1+.02);g.gain.exponentialRampToValueAtTime(.001,a.currentTime+i*.1+.25);o.start(a.currentTime+i*.1);o.stop(a.currentTime+i*.1+.3);});",
    "lose":    "[330,277,247,220].forEach((f,i)=>{var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=f;o.type='sawtooth';g.gain.setValueAtTime(0,a.currentTime+i*.12);g.gain.linearRampToValueAtTime(.12,a.currentTime+i*.12+.02);g.gain.exponentialRampToValueAtTime(.001,a.currentTime+i*.12+.28);o.start(a.currentTime+i*.12);o.stop(a.currentTime+i*.12+.35);});",
    "tie":     "var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=440;o.type='triangle';g.gain.setValueAtTime(.13,a.currentTime);g.gain.exponentialRampToValueAtTime(.001,a.currentTime+.3);o.start();o.stop(a.currentTime+.35);",
    "set_win": "[523,659,784,523,659,784,1047].forEach((f,i)=>{var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=f;o.type='sine';g.gain.setValueAtTime(0,a.currentTime+i*.09);g.gain.linearRampToValueAtTime(.2,a.currentTime+i*.09+.02);g.gain.exponentialRampToValueAtTime(.001,a.currentTime+i*.09+.2);o.start(a.currentTime+i*.09);o.stop(a.currentTime+i*.09+.28);});",
    "set_lose":"[196,185,165,147].forEach((f,i)=>{var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=f;o.type='sawtooth';g.gain.setValueAtTime(0,a.currentTime+i*.15);g.gain.linearRampToValueAtTime(.14,a.currentTime+i*.15+.03);g.gain.exponentialRampToValueAtTime(.001,a.currentTime+i*.15+.3);o.start(a.currentTime+i*.15);o.stop(a.currentTime+i*.15+.42);});",
    "click":   "var o=a.createOscillator(),g=a.createGain();o.connect(g);g.connect(a.destination);o.frequency.value=1100;o.type='sine';g.gain.setValueAtTime(.07,a.currentTime);g.gain.exponentialRampToValueAtTime(.001,a.currentTime+.05);o.start();o.stop(a.currentTime+.06);",
}

def play_sound(stype):
    if not st.session_state.sound_enabled:
        return
    js = SOUNDS.get(stype, "")
    if js:
        components.html(
            f"<script>try{{(function(){{var a=new(window.AudioContext||window.webkitAudioContext)();{js}}}())}}catch(e){{}}</script>",
            height=0
        )

def fire_confetti():
    components.html("""
<script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.2/dist/confetti.browser.min.js"></script>
<script>setTimeout(function(){
  if(typeof confetti!=='undefined'){
    confetti({particleCount:200,spread:90,origin:{y:.5},colors:['#00eeff','#ff2060','#ffcc00','#00ff88','#cc44ff']});
    setTimeout(()=>confetti({particleCount:80,spread:60,origin:{y:.4},angle:60}),400);
    setTimeout(()=>confetti({particleCount:80,spread:60,origin:{y:.4},angle:120}),700);
  }
},100);</script>""", height=0)

# ═══════════════════════════════════════════════════════════════════════════════
#  TIMER JS  (visual countdown bar)
# ═══════════════════════════════════════════════════════════════════════════════
def inject_timer_js(duration_s=10):
    components.html(f"""
<script>
(function(){{
  var bar=document.querySelector('.timer-bar');
  if(!bar)return;
  var start=Date.now(), dur={duration_s}*1000;
  function tick(){{
    var elapsed=Date.now()-start;
    var pct=Math.max(0,100-(elapsed/dur*100));
    if(bar)bar.style.width=pct+'%';
    if(pct>0)requestAnimationFrame(tick);
  }}
  requestAnimationFrame(tick);
}})();
</script>""", height=0)

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
EMOJI  = {"R": "✊", "P": "✋", "S": "✌️"}
NAME   = {"R": "ROCK", "P": "PAPER", "S": "SCISSORS"}
WMSG   = {"win":  ["K.O.!", "VICTORY!", "PERFECT!", "LETHAL!", "UNSTOPPABLE!"],
           "lose": ["A.I. WINS!", "PREDICTED!", "OUTSMARTED!", "TOO EASY!", "CALCULATED!"],
           "tie":  ["DRAW!", "STALEMATE!", "DEADLOCK!", "MIRROR MATCH!"]}
SMSG   = {"player": ["SET WIN!", "CHAMPION!", "CRUSHING IT!", "DOMINANT!"],
           "ai":    ["AI WINS SET!", "DOMINATED!", "PERFECT AI!", "OBLITERATED!"],
           "tie":   ["SET TIED!", "DEAD HEAT!", "EVEN FORCES!"]}
DC     = {"EASY": "#00ff88", "MEDIUM": "#ffcc00", "HARD": "#ff2060"}
DDESC  = {"EASY":   "🎯 22% smart — mostly random",
           "MEDIUM": "🧠 82% pattern detection",
           "HARD":   "☠️ 96%+ adaptive · 3-step Markov · entropy tuned"}

# ═══════════════════════════════════════════════════════════════════════════════
#  PLAY LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
def play_vs_ai(choice: str):
    ss  = st.session_state
    rps = ss.rounds_per_set
    ss.confirm_reset    = False
    ss.new_achievement  = None

    # Reaction time
    if ss.round_start_time is not None:
        react_ms = int((time.time() - ss.round_start_time) * 1000)
        ss.last_reaction_ms = react_ms
        if ss.best_reaction_ms is None or react_ms < ss.best_reaction_ms:
            ss.best_reaction_ms = react_ms
    ss.round_start_time = time.time()

    ai_move = smart_ai_choice(ss.history, ss.difficulty)
    result  = determine_result(choice, ai_move)

    # AI prediction accuracy
    ss.ai_predicted += 1
    if ss.last_ai_pred == choice:
        ss.ai_correct += 1
        ss.unpredict_streak = 0
    else:
        ss.unpredict_streak += 1

    ss.last_player   = choice
    ss.last_ai       = ai_move
    ss.last_result   = result
    ss.total_rounds += 1
    ss.history.append(choice)
    ss.round_in_set += 1
    ss.round_log.append({"result": result, "player": choice, "ai": ai_move})

    # Append to long-term history
    append_lt_history([choice])

    if result == "win":
        ss.set_player_w  += 1
        ss.streak        += 1
        ss.total_wins    += 1
        ss.best_streak    = max(ss.streak, ss.best_streak)
        ss.pending_sound  = "win"
    elif result == "lose":
        ss.set_ai_w      += 1
        ss.streak         = 0
        ss.total_losses  += 1
        ss.pending_sound  = "lose"
        if ss.set_player_w == 0 and ss.set_ai_w >= 2:
            ss.comeback_possible = True
    else:
        ss.set_ties      += 1
        ss.streak         = 0
        ss.total_ties_all += 1
        ss.pending_sound  = "tie"

    check_round_ach(result, choice)

    wins_needed   = (rps // 2) + 1
    pw, aw        = ss.set_player_w, ss.set_ai_w
    rounds_played = ss.round_in_set
    if pw >= wins_needed or aw >= wins_needed or rounds_played >= rps:
        sw = "player" if pw > aw else "ai" if aw > pw else "tie"
        ss.set_winner = sw
        ss.set_over   = True
        if sw == "player":
            ss.player_sets += 1
            ss.pending_sound  = "set_win"
            ss.pending_confetti = True
        elif sw == "ai":
            ss.ai_sets += 1
            ss.pending_sound = "set_lose"
        ss.set_log.append({"set": len(ss.set_log)+1, "winner": sw,
                           "score": f"{pw}-{aw}", "rounds": rounds_played,
                           "diff": ss.difficulty})
        check_set_ach()
        ss.comeback_possible = False

        # Update leaderboard
        total_s = ss.player_sets + ss.ai_sets
        wp = (ss.player_sets / total_s * 100) if total_s else 0
        update_leaderboard(ss.player_name, ss.player_sets, wp, ss.total_rounds)

        # Save profile
        save_profile(ss.player_name, ss.total_wins, ss.total_losses,
                     ss.total_ties_all, ss.player_sets, ss.best_streak, ss.total_rounds)

# Multiplayer play logic
def play_mp_choose(player_num: int, choice: str):
    ss = st.session_state
    if player_num == 1:
        ss.mp_p1_choice = choice
        ss.mp_stage     = "p2"
    else:
        ss.mp_p2_choice = choice
        ss.mp_stage     = "reveal"

def play_mp_resolve():
    ss = st.session_state
    rps    = ss.rounds_per_set
    p1, p2 = ss.mp_p1_choice, ss.mp_p2_choice

    # From P1 perspective: P1 = "player", P2 = "ai"
    result = determine_result(p1, p2)

    ss.last_player   = p1
    ss.last_ai       = p2
    ss.last_result   = result
    ss.total_rounds += 1
    ss.round_in_set += 1
    ss.round_log.append({"result": result, "player": p1, "ai": p2})

    if result == "win":
        ss.set_player_w += 1
        ss.streak       += 1
        ss.total_wins   += 1
        ss.best_streak   = max(ss.streak, ss.best_streak)
        ss.pending_sound = "win"
    elif result == "lose":
        ss.set_ai_w     += 1
        ss.streak        = 0
        ss.total_losses += 1
        ss.pending_sound = "lose"
    else:
        ss.set_ties    += 1
        ss.streak       = 0
        ss.pending_sound = "tie"

    wins_needed   = (rps // 2) + 1
    pw, aw        = ss.set_player_w, ss.set_ai_w
    rounds_played = ss.round_in_set
    if pw >= wins_needed or aw >= wins_needed or rounds_played >= rps:
        sw = "player" if pw > aw else "ai" if aw > pw else "tie"
        ss.set_winner = sw
        ss.set_over   = True
        if sw == "player":
            ss.player_sets += 1
            ss.pending_sound    = "set_win"
            ss.pending_confetti = True
        elif sw == "ai":
            ss.ai_sets += 1
            ss.pending_sound = "set_lose"
        ss.set_log.append({"set": len(ss.set_log)+1, "winner": sw,
                           "score": f"{pw}-{aw}", "rounds": rounds_played, "diff": "MP"})

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER RENDERERS
# ═══════════════════════════════════════════════════════════════════════════════
def round_dots_html(log, rps):
    dots = ""
    for i in range(rps):
        if i < len(log):
            r   = log[i]["result"]
            cls = "wd" if r=="win" else "ld" if r=="lose" else "td"
        elif i == len(log) and len(log) < rps:
            cls = "cd"
        else:
            cls = ""
        dots += f'<div class="round-dot {cls}"></div>'
    return (f'<div class="round-progress">'
            f'<span class="round-lbl">RD</span>{dots}'
            f'<span class="round-lbl">/{rps}</span></div>')

def set_pips_html():
    log = st.session_state.set_log
    if not log:
        return ""
    pips = ""
    for s in log:
        w   = s["winner"]
        cls = "pw" if w=="player" else "aw" if w=="ai" else "tw"
        lbl = "P" if w=="player" else "A" if w=="ai" else "="
        pips += f'<div class="set-pip {cls}">{lbl}</div>'
    return f'<div class="set-tracker"><span style="font-family:Bungee,cursive;font-size:.55rem;letter-spacing:2px;color:var(--muted)">SETS ▸</span>{pips}</div>'

def arena_block():
    ss = st.session_state
    p  = ss.last_player
    a  = ss.last_ai
    r  = ss.last_result

    if r is None:
        p_em, a_em   = "✊", "✊"
        p_cls, a_cls = "idle", "idle"
        p_lbl, a_lbl = "READY?", "READY?"
        res_block    = ""
    else:
        p_em   = EMOJI[p];  a_em  = EMOJI[a]
        p_lbl  = NAME[p];   a_lbl = NAME[a]
        p_cls  = "reveal " + ("winner" if r=="win"  else "loser" if r=="lose" else "")
        a_cls  = "reveal " + ("winner" if r=="lose" else "loser" if r=="win"  else "")
        desc   = (NAME[p]+" beats "+NAME[a] if r=="win" else
                  NAME[a]+" beats "+NAME[p] if r=="lose" else
                  "Both chose "+NAME[p])
        msg    = random.choice(WMSG[r])
        react  = (f'<div class="reaction-time">⚡ {ss.last_reaction_ms}ms reaction'
                  +(f' · BEST: {ss.best_reaction_ms}ms' if ss.best_reaction_ms else '')
                  +'</div>') if ss.last_reaction_ms else ""
        res_block = (
            '<div class="result-wrap">'
            f'<div class="result-banner {r}">{msg}</div>'
            f'<p class="result-sub">{desc}</p>'
            f'{react}'
            '</div>'
        )

    p2_label = ("P2" if ss.game_mode == "multi" else "A.I.")
    p2_cls   = "at"

    return (
        '<div class="arena">'
        '<div class="arena-row">'
        '<div class="fighter-box">'
        f'<div class="fighter-tag pt">PLAYER</div>'
        f'<div class="hand-wrap ph"><span class="hand-emoji {p_cls}">{p_em}</span></div>'
        f'<div class="choice-lbl">{p_lbl}</div>'
        '</div>'
        '<div class="vs-center">'
        '<div class="vs-line"></div>'
        '<div class="vs-txt">VS</div>'
        '<div class="vs-line"></div>'
        '</div>'
        '<div class="fighter-box">'
        f'<div class="fighter-tag {p2_cls}">{p2_label}</div>'
        f'<div class="hand-wrap ah"><span class="hand-emoji {a_cls}">{a_em}</span></div>'
        f'<div class="choice-lbl">{a_lbl}</div>'
        '</div>'
        '</div>'
        + res_block +
        '</div>'
    )

def strategy_insights():
    h = st.session_state.history
    if len(h) < 5:
        return []
    ins      = []
    total    = len(h)
    r_p      = h.count("R")/total*100
    p_p      = h.count("P")/total*100
    s_p      = h.count("S")/total*100
    dominant = max([("Rock", r_p), ("Paper", p_p), ("Scissors", s_p)], key=lambda x:x[1])
    if dominant[1] > 42:
        ins.append(("warn", f'⚠️ You overuse <b>{dominant[0]}</b> ({dominant[1]:.0f}%). The AI exploits this heavily.'))
    reps    = sum(1 for i in range(1, len(h)) if h[i]==h[i-1])
    rep_pct = reps/(total-1)*100
    if rep_pct > 35:
        ins.append(("warn", f'⚠️ You repeat the same move <b>{rep_pct:.0f}%</b> of the time — very predictable!'))
    elif rep_pct < 18:
        ins.append(("ok",   f'✅ Excellent variety! Repetition rate: <b>{rep_pct:.0f}%</b>'))
    ent    = calculate_entropy(h)
    max_e  = math.log2(3)
    if ent/max_e < 0.7:
        ins.append(("warn", f'🎯 Predictability score: <b>{ent:.2f}/{max_e:.2f}</b>. Mix your moves more!'))
    else:
        ins.append(("ok",   f'🎲 Great randomness! Entropy: <b>{ent:.2f}/{max_e:.2f}</b> — hard to predict!'))
    # Long-term pattern
    lt = load_lt_history()
    if len(lt) >= 20:
        lt_r = lt.count("R")/len(lt)*100
        if lt_r > 40:
            ins.append(("info", f'📊 Career data: You pick Rock <b>{lt_r:.0f}%</b> long-term across sessions.'))
    return ins

# ═══════════════════════════════════════════════════════════════════════════════
#  ██████████  RENDER START  ██████████
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# ── PLAYER PROFILE SETUP ──────────────────────────────────────────────────────
if not st.session_state.profile_set:
    saved = load_save().get("profile", {})
    st.markdown('<h1 class="game-title">⚔ RPS ARENA ⚔</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Enter your name to begin</p>', unsafe_allow_html=True)
    st.markdown('<br>', unsafe_allow_html=True)
    name_input = st.text_input("YOUR NAME", value=saved.get("name",""), max_chars=16,
                               placeholder="e.g. PLAYER ONE")
    diff_setup = st.select_slider("DIFFICULTY",
                                  options=["EASY","MEDIUM","HARD"],
                                  value=st.session_state.difficulty)
    rps_setup  = st.select_slider("ROUNDS PER SET",
                                  options=[3,5,7,9],
                                  value=st.session_state.rounds_per_set)
    if st.button("▶  START GAME", use_container_width=True):
        name = name_input.strip().upper() or "PLAYER"
        st.session_state.player_name    = name
        st.session_state.difficulty     = diff_setup
        st.session_state.rounds_per_set = rps_setup
        st.session_state.profile_set    = True
        # Load saved career stats
        if saved:
            st.session_state.total_wins    = saved.get("wins", 0)
            st.session_state.total_losses  = saved.get("losses", 0)
            st.session_state.total_ties_all= saved.get("ties", 0)
            st.session_state.best_streak   = saved.get("best_streak", 0)
        st.rerun()
    st.stop()

ss = st.session_state

# ── TITLE ─────────────────────────────────────────────────────────────────────
st.markdown('<h1 class="game-title">⚔ RPS ARENA ⚔</h1>', unsafe_allow_html=True)
dc = DC.get(ss.difficulty, "#ffcc00")
mode_lbl = "2-PLAYER LOCAL" if ss.game_mode=="multi" else f'{ss.difficulty} MODE · ADAPTIVE AI'
st.markdown(
    f'<p class="subtitle">⚡ BEST OF {ss.rounds_per_set} · '
    f'<span style="color:{dc}">{mode_lbl}</span> ⚡</p>',
    unsafe_allow_html=True
)

# ── PROFILE BAR ───────────────────────────────────────────────────────────────
total_s  = ss.player_sets + ss.ai_sets
sp_pct   = (ss.player_sets/total_s*100) if total_s else 0
ai_a_pct = (ss.ai_correct/ss.ai_predicted*100) if ss.ai_predicted else 0

st.markdown(
    f'<div class="profile-bar">'
    f'<div class="profile-name">👤 {ss.player_name}</div>'
    f'<div class="profile-stat">SETS <span>{ss.player_sets}W–{ss.ai_sets}L</span></div>'
    f'<div class="profile-stat">WIN% <span>{sp_pct:.0f}%</span></div>'
    f'<div class="profile-stat">STREAK <span>🔥{ss.streak}</span></div>'
    f'<div class="profile-stat">BEST <span>⚡{ss.best_streak}</span></div>'
    f'</div>',
    unsafe_allow_html=True
)

# ── SETTINGS ──────────────────────────────────────────────────────────────────
with st.expander("⚙️  SETTINGS", expanded=False):
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        d = st.selectbox("DIFFICULTY", ["EASY","MEDIUM","HARD"],
                         index=["EASY","MEDIUM","HARD"].index(ss.difficulty), key="dsel")
        if d != ss.difficulty: ss.difficulty = d; st.rerun()
    with sc2:
        opts = [3,5,7,9]
        r = st.selectbox("ROUNDS/SET", opts,
                         index=opts.index(ss.rounds_per_set) if ss.rounds_per_set in opts else 1,
                         key="rsel")
        if r != ss.rounds_per_set: ss.rounds_per_set = r; st.rerun()
    with sc3:
        t = st.selectbox("THEME", ["CYBER","LIGHT","MINIMAL"],
                         index=["CYBER","LIGHT","MINIMAL"].index(ss.theme), key="tsel")
        if t != ss.theme: ss.theme = t; st.rerun()
    with sc4:
        snd = st.toggle("SOUND 🔊", value=ss.sound_enabled, key="snd")
        if snd != ss.sound_enabled: ss.sound_enabled = snd; st.rerun()
    st.markdown(
        f'<div style="text-align:center;margin:.4rem 0;font-size:.6rem;color:var(--muted);">'
        f'{DDESC[ss.difficulty]}'
        f'</div>', unsafe_allow_html=True
    )

# ── GAME MODE TABS ─────────────────────────────────────────────────────────────
col_m1, col_m2 = st.columns(2)
with col_m1:
    if st.button("🤖  VS AI",     key="mode_ai",  use_container_width=True):
        ss.game_mode = "solo"; st.rerun()
with col_m2:
    if st.button("🧑‍🤝‍🧑  2-PLAYER LOCAL", key="mode_mp", use_container_width=True):
        ss.game_mode = "multi"; st.rerun()

# ── SET HISTORY PIPS ──────────────────────────────────────────────────────────
st.markdown(set_pips_html(), unsafe_allow_html=True)

# ── NEW ACHIEVEMENT BANNER ────────────────────────────────────────────────────
if ss.new_achievement:
    ach = ACHIEVEMENTS.get(ss.new_achievement, {})
    st.markdown(
        f'<div class="new-ach">'
        f'<div style="font-size:.52rem;letter-spacing:4px;color:var(--gold);margin-bottom:.2rem;">🏆 ACHIEVEMENT UNLOCKED</div>'
        f'<div style="font-family:Orbitron,sans-serif;font-weight:700;font-size:1.2rem;color:var(--gold)">'
        f'{ach.get("icon","🏅")} {ach.get("name","")}</div>'
        f'<div style="font-size:.65rem;color:var(--muted);margin-top:.2rem">{ach.get("desc","")}</div>'
        f'</div>', unsafe_allow_html=True
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  SET OVER SCREEN
# ═══════════════════════════════════════════════════════════════════════════════
if ss.set_over:
    snd = ss.pending_sound
    if snd:
        play_sound(snd); ss.pending_sound = None
    if ss.pending_confetti:
        fire_confetti(); ss.pending_confetti = False

    sw      = ss.set_winner
    pw, aw  = ss.set_player_w, ss.set_ai_w
    ov_cls  = "pw" if sw=="player" else "aw" if sw=="ai" else "tw"
    color   = "var(--blue)" if sw=="player" else "var(--pink)" if sw=="ai" else "var(--gold)"
    msg     = random.choice(SMSG[sw])
    lbl     = f"🏆 {ss.player_name} WINS THE SET!" if sw=="player" else \
              ("🤖 A.I. WINS THE SET!" if ss.game_mode=="solo" else "🧑‍🤝‍🧑 PLAYER 2 WINS!") if sw=="ai" else "🤝 SET TIED!"
    ai_acc  = (ss.ai_correct/ss.ai_predicted*100) if ss.ai_predicted else 0

    score_row = (
        f'<span style="color:var(--blue);font-size:2.4rem;font-weight:900">{ss.player_sets}</span>'
        f'<span style="color:var(--muted);font-size:.9rem;align-self:center">SETS</span>'
        f'<span style="color:var(--pink);font-size:2.4rem;font-weight:900">{ss.ai_sets}</span>'
    )

    st.markdown(
        f'<div class="set-over-wrap {ov_cls}">'
        f'<div class="so-title" style="color:{color}">{msg}</div>'
        f'<div class="so-sub">{lbl}</div>'
        f'<div class="so-score-row">{score_row}</div>'
        f'<div style="font-size:.66rem;color:var(--muted);letter-spacing:2px;margin-bottom:.3rem;">'
        f'ROUNDS THIS SET: YOU {pw} — OPP {aw}</div>'
        + (f'<div style="font-size:.6rem;color:var(--muted);letter-spacing:2px;">'
           f'AI READ YOUR MOVES: {ai_acc:.0f}% ACCURACY</div>'
           if ss.game_mode == "solo" else "") +
        '</div>', unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶  NEXT SET", key="ns", use_container_width=True):
            for k in ["round_in_set","set_player_w","set_ai_w","set_ties",
                      "set_over","set_winner","last_result","last_player",
                      "last_ai","round_log","new_achievement","mp_p1_choice",
                      "mp_p2_choice","comeback_possible"]:
                ss[k] = ([] if k=="round_log" else
                          None if k in ("last_result","last_player","last_ai","set_winner","mp_p1_choice","mp_p2_choice") else
                          False if k in ("set_over","new_achievement","comeback_possible") else 0)
            ss.mp_stage = "p1"
            st.rerun()
    with c2:
        if st.button("↺  FULL RESET", key="fr", use_container_width=True):
            for k, v in DEFAULTS.items(): ss[k] = v
            st.rerun()
    st.stop()

# ── Play pending sound ─────────────────────────────────────────────────────────
if ss.pending_sound:
    play_sound(ss.pending_sound); ss.pending_sound = None

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN GAME AREA
# ═══════════════════════════════════════════════════════════════════════════════

# Scoreboard
st.markdown(
    f'<div class="scoreboard">'
    f'<div class="score-card pl"><div class="sc-lbl">{ss.player_name}</div>'
    f'<div class="sc-num">{ss.player_sets}</div></div>'
    f'<div class="vs-badge">VS</div>'
    f'<div class="score-card ai"><div class="sc-lbl">{"A.I." if ss.game_mode=="solo" else "PLAYER 2"}</div>'
    f'<div class="sc-num">{ss.ai_sets}</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

total_r  = ss.player_sets + ss.ai_sets
wr       = (ss.player_sets/total_r*100) if total_r else 0
ai_a2    = (ss.ai_correct/ss.ai_predicted*100) if ss.ai_predicted else 0
st.markdown(
    f'<div class="mini-stats">'
    f'<div class="score-card ms"><div class="sc-lbl">THIS SET YOU</div>'
    f'<div class="sc-num">{ss.set_player_w}</div></div>'
    f'<div class="score-card ms"><div class="sc-lbl">ROUND</div>'
    f'<div class="sc-num">{ss.round_in_set}/{ss.rounds_per_set}</div></div>'
    f'<div class="score-card ms"><div class="sc-lbl">THIS SET OPP</div>'
    f'<div class="sc-num">{ss.set_ai_w}</div></div>'
    f'</div>',
    unsafe_allow_html=True
)

# Round dots
st.markdown(round_dots_html(ss.round_log, ss.rounds_per_set), unsafe_allow_html=True)

# Timer bar
st.markdown('<div class="timer-wrap"><div class="timer-bar" style="width:100%"></div></div>',
            unsafe_allow_html=True)
inject_timer_js(10)

# Streak
if ss.streak > 1:
    st.markdown(f'<div class="streak-bar">🔥 {ss.streak} WIN STREAK &nbsp;|&nbsp; BEST: {ss.best_streak}</div>', unsafe_allow_html=True)
elif ss.best_streak > 0:
    st.markdown(f'<div class="streak-bar">BEST STREAK: {ss.best_streak}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="streak-bar">&nbsp;</div>', unsafe_allow_html=True)

# ── ARENA ─────────────────────────────────────────────────────────────────────
st.markdown(arena_block(), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  WEAPON BUTTONS  — Solo vs AI
# ═══════════════════════════════════════════════════════════════════════════════
if ss.game_mode == "solo":
    st.markdown('<div style="text-align:center;font-size:.56rem;letter-spacing:5px;'
                'color:var(--muted);margin-bottom:.7rem;">— CHOOSE YOUR WEAPON —</div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✊\n\nROCK", key="rock", use_container_width=True):
            play_sound("click"); play_vs_ai("R"); st.rerun()
    with c2:
        if st.button("✋\n\nPAPER", key="paper", use_container_width=True):
            play_sound("click"); play_vs_ai("P"); st.rerun()
    with c3:
        if st.button("✌️\n\nSCISSORS", key="scissors", use_container_width=True):
            play_sound("click"); play_vs_ai("S"); st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  MULTIPLAYER MODE  — 2-player local
# ═══════════════════════════════════════════════════════════════════════════════
else:
    stage = ss.mp_stage

    if stage == "p1":
        st.markdown('<div style="text-align:center;font-family:Orbitron,sans-serif;'
                    'font-size:.7rem;letter-spacing:4px;color:var(--blue);margin:.6rem 0;">'
                    '👤 PLAYER 1 — CHOOSE YOUR WEAPON</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✊  ROCK",     key="mp_r1", use_container_width=True):
                play_mp_choose(1,"R"); st.rerun()
        with c2:
            if st.button("✋  PAPER",    key="mp_p1", use_container_width=True):
                play_mp_choose(1,"P"); st.rerun()
        with c3:
            if st.button("✌️  SCISSORS", key="mp_s1", use_container_width=True):
                play_mp_choose(1,"S"); st.rerun()

    elif stage == "p2":
        st.markdown('<div style="background:var(--surface);border-radius:12px;'
                    'padding:.6rem;text-align:center;font-size:.65rem;letter-spacing:3px;'
                    'color:var(--grn);margin:.4rem 0;">✅ P1 LOCKED IN — PASS TO PLAYER 2</div>',
                    unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;font-family:Orbitron,sans-serif;'
                    'font-size:.7rem;letter-spacing:4px;color:var(--pink);margin:.6rem 0;">'
                    '👤 PLAYER 2 — CHOOSE YOUR WEAPON</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("✊  ROCK",     key="mp_r2", use_container_width=True):
                play_mp_choose(2,"R"); play_mp_resolve(); st.rerun()
        with c2:
            if st.button("✋  PAPER",    key="mp_p2", use_container_width=True):
                play_mp_choose(2,"P"); play_mp_resolve(); st.rerun()
        with c3:
            if st.button("✌️  SCISSORS", key="mp_s2", use_container_width=True):
                play_mp_choose(2,"S"); play_mp_resolve(); st.rerun()

    elif stage == "reveal":
        # Auto-advance to next round
        if st.button("▶  NEXT ROUND", key="mp_next", use_container_width=True):
            ss.mp_stage = "p1"; st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════
if ss.total_rounds >= 3:
    st.markdown('<div class="sec-head">— ANALYTICS & INSIGHTS —</div>', unsafe_allow_html=True)

    with st.expander("📊  STATS, CHARTS & AI ANALYSIS", expanded=False):
        h     = ss.history
        total = len(h)

        if total > 0:
            rc, pc, sc = h.count("R"), h.count("P"), h.count("S")
            th = ss.theme
            fc = {"CYBER":["#00eeff","#ff2060","#ffcc00"],
                  "LIGHT":["#0044cc","#cc0040","#886600"],
                  "MINIMAL":["#dddddd","#999999","#666666"]}.get(th, ["#00eeff","#ff2060","#ffcc00"])
            bg = "#0d0d1e" if th=="CYBER" else ("#ffffff" if th=="LIGHT" else "#141414")
            tx = "#d8deff" if th!="LIGHT" else "#111133"

            # Bar chart: move distribution
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=["✊ ROCK","✋ PAPER","✌️ SCISSORS"],
                y=[rc, pc, sc],
                marker_color=fc,
                marker_line_width=0,
                text=[f"{v}<br>{v/total*100:.0f}%" for v in [rc,pc,sc]],
                textposition="outside",
                textfont=dict(family="Courier New", size=11, color=tx),
            ))
            fig.update_layout(
                title=dict(text="YOUR MOVE DISTRIBUTION", font=dict(family="Courier New",size=12,color=tx), x=.5),
                paper_bgcolor=bg, plot_bgcolor=bg,
                font=dict(family="Courier New", color=tx),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                xaxis=dict(showgrid=False, zeroline=False),
                margin=dict(t=45,b=15,l=15,r=15), height=230,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Pie chart: outcomes
            tw, tl, tt = ss.total_wins, ss.total_losses, ss.total_ties_all
            if tw+tl+tt > 0:
                pc2 = {"CYBER":["#00ff88","#ff2060","#ffcc00"],
                       "LIGHT":["#006622","#cc0040","#886600"],
                       "MINIMAL":["#cccccc","#888888","#444444"]}.get(th, ["#00ff88","#ff2060","#ffcc00"])
                fig2 = go.Figure(data=[go.Pie(
                    labels=["WINS","LOSSES","TIES"], values=[tw,tl,tt],
                    marker=dict(colors=pc2, line=dict(color=bg,width=2)),
                    hole=.52,
                    textfont=dict(family="Courier New",size=11,color=tx),
                )])
                fig2.update_layout(
                    title=dict(text="ROUND OUTCOMES", font=dict(family="Courier New",size=12,color=tx), x=.5),
                    paper_bgcolor=bg, plot_bgcolor=bg,
                    font=dict(family="Courier New",color=tx),
                    legend=dict(font=dict(color=tx,family="Courier New")),
                    margin=dict(t=45,b=10,l=10,r=10), height=240,
                )
                st.plotly_chart(fig2, use_container_width=True)

        # AI Prediction Accuracy bars
        ai_acc = (ss.ai_correct/ss.ai_predicted*100) if ss.ai_predicted else 0
        you_pct = 100 - ai_acc
        st.markdown(
            f'<div class="ins-label">AI PREDICTION ACCURACY</div>'
            f'<div style="background:var(--surface);border-radius:12px;padding:.8rem 1rem;margin:.3rem 0;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:.3rem;">'
            f'<span>🤖 AI read you correctly</span><span style="color:var(--pink);font-weight:700">{ai_acc:.0f}%</span></div>'
            f'<div class="acc-wrap"><div class="acc-fill ai-fill" style="width:{ai_acc:.0f}%"></div></div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:.5rem;margin-bottom:.3rem;">'
            f'<span>✅ You were unpredictable</span><span style="color:var(--blue);font-weight:700">{you_pct:.0f}%</span></div>'
            f'<div class="acc-wrap"><div class="acc-fill pl-fill" style="width:{you_pct:.0f}%"></div></div>'
            f'<div style="margin-top:.5rem;font-size:.58rem;color:var(--muted);">'
            f'Based on {ss.ai_predicted} predictions · Random baseline = 33%</div>'
            f'</div>', unsafe_allow_html=True
        )

        # Reaction time
        if ss.best_reaction_ms:
            st.markdown(
                f'<div style="background:var(--surface);border-radius:12px;padding:.7rem 1rem;margin:.3rem 0;">'
                f'<div class="ins-label">REACTION TIMES</div>'
                f'<div style="display:flex;justify-content:space-between;font-size:.72rem;">'
                f'<span>⚡ Fastest: <b style="color:var(--grn)">{ss.best_reaction_ms}ms</b></span>'
                f'<span>🕐 Last: <b>{ss.last_reaction_ms}ms</b></span>'
                f'</div></div>', unsafe_allow_html=True
            )

        # Strategy insights
        ins = strategy_insights()
        if ins:
            st.markdown('<div class="ins-label" style="margin-top:.7rem;">STRATEGY INSIGHTS</div>', unsafe_allow_html=True)
            for kind, text in ins:
                st.markdown(f'<div class="insight-card {kind}">{text}</div>', unsafe_allow_html=True)

        # Dynamic tip
        tip = ("💡 <b>Tip:</b> You're very predictable. Try completely random moves — don't think, just click!"
               if ai_acc > 60 else
               "💡 <b>Tip:</b> Moderate predictability. Avoid patterns after wins — mix Rock with unexpected Scissors."
               if ai_acc > 40 else
               "💡 <b>Tip:</b> Excellent unpredictability! The AI can barely track you. Keep trusting your gut.")
        st.markdown(f'<div style="background:var(--surface);border-radius:10px;padding:.7rem 1rem;'
                    f'font-size:.68rem;opacity:.8;margin-top:.5rem;">{tip}</div>',
                    unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  ACHIEVEMENTS
# ═══════════════════════════════════════════════════════════════════════════════
n_ach = len(ss.achievements)
with st.expander(f"🏅  ACHIEVEMENTS  ({n_ach}/{len(ACHIEVEMENTS)})", expanded=False):
    badges = ""
    for key, ach in ACHIEVEMENTS.items():
        unlocked = key in ss.achievements
        cls      = "on" if unlocked else "off"
        badges  += (f'<div class="ach-badge {cls}">'
                    f'<span class="ach-icon">{ach["icon"]}</span>'
                    f'<div><div style="font-family:Bungee,cursive;font-size:.56rem;letter-spacing:1px">{ach["name"]}</div>'
                    f'<div style="font-size:.52rem;color:var(--muted)">{ach["desc"]}</div></div>'
                    f'</div>')
    st.markdown(f'<div class="ach-grid">{badges}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  LEADERBOARD
# ═══════════════════════════════════════════════════════════════════════════════
board = load_leaderboard()
if board:
    with st.expander("🏆  LEADERBOARD  (TOP 10)", expanded=False):
        for i, e in enumerate(board, 1):
            rank_icon = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            is_me     = e.get("name","") == ss.player_name
            cls       = "lb-row me" if is_me else "lb-row"
            st.markdown(
                f'<div class="{cls}">'
                f'<div class="lb-rank">{rank_icon}</div>'
                f'<div class="lb-name">{e["name"]}</div>'
                f'<div style="font-size:.6rem;color:var(--muted)">{e["sets_won"]}W · {e["win_pct"]}% · {e["total_rounds"]}R</div>'
                f'</div>', unsafe_allow_html=True
            )

# ═══════════════════════════════════════════════════════════════════════════════
#  BATTLE LOGS
# ═══════════════════════════════════════════════════════════════════════════════
if ss.round_log:
    with st.expander("📋  CURRENT SET LOG", expanded=False):
        rows = ""
        for i, e in enumerate(ss.round_log):
            p2 = "A.I." if ss.game_mode=="solo" else "P2"
            rows += (f'<div class="log-row {e["result"][0]}r">'
                     f'<span style="color:var(--muted);width:40px">RD {i+1}</span>'
                     f'<span>{EMOJI[e["player"]]} {NAME[e["player"]]}</span>'
                     f'<span style="color:var(--muted)">vs</span>'
                     f'<span>{EMOJI[e["ai"]]} {NAME[e["ai"]]}</span>'
                     f'<span class="log-res {e["result"][0]}">{e["result"].upper()}</span>'
                     f'</div>')
        st.markdown(rows, unsafe_allow_html=True)

if ss.set_log:
    with st.expander("🏆  SET HISTORY", expanded=False):
        rows = ""
        for s in reversed(ss.set_log):
            w   = s["winner"]
            cls = "wr" if w=="player" else "lr" if w=="ai" else "tr"
            lbl = ss.player_name if w=="player" else ("A.I." if s.get("diff")!="MP" else "P2") if w=="ai" else "TIE"
            rc  = "w" if w=="player" else "l" if w=="ai" else "t"
            rows += (f'<div class="log-row {cls}">'
                     f'<span style="color:var(--muted)">SET {s["set"]}</span>'
                     f'<span>Score {s["score"]} ({s.get("rounds","?")} rds) [{s.get("diff","?")}]</span>'
                     f'<span class="log-res {rc}">{lbl} WINS</span>'
                     f'</div>')
        st.markdown(rows, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  FOOTER + RESET
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="ai-warn">⚠️ AI USES 3-STEP MARKOV · SPAM DETECTION · ENTROPY TUNING · CROSS-SESSION LEARNING ⚠️</div>',
            unsafe_allow_html=True)

if ss.confirm_reset:
    st.markdown(
        '<div class="confirm-box">'
        '<div style="font-family:Orbitron,sans-serif;font-weight:700;color:var(--pink);font-size:.9rem;letter-spacing:3px">CONFIRM RESET?</div>'
        '<div style="font-size:.65rem;color:var(--muted);margin:.4rem 0">All session stats will be cleared. Career data is preserved.</div>'
        '</div>', unsafe_allow_html=True
    )
    cr1, cr2 = st.columns(2)
    with cr1:
        if st.button("✅  YES, RESET", key="cy", use_container_width=True):
            for k, v in DEFAULTS.items(): ss[k] = v
            st.rerun()
    with cr2:
        if st.button("❌  CANCEL", key="cn", use_container_width=True):
            ss.confirm_reset = False; st.rerun()
else:
    if st.button("↺  RESET SESSION", key="reset"):
        ss.confirm_reset = True; st.rerun()
