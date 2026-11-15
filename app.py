"""
app.py  --  TIC·TAC·TOE: THE UPSIDE DOWN
A "Stranger Things meets cyber board" Streamlit front-end for gamelogic.py

Run with:   streamlit run app.py
Needs:      streamlit >= 1.39 (uses st.container(key=...)), numpy
"""

import math
import random

import streamlit as st

from gamelogic import (
    DEFAULT_WIN_LENGTH,
    EMPTY,
    SYMBOLS,
    SUPPORTED_SIZES,
    O,
    X,
    Difficulty,
    TicTacToeGame,
)

st.set_page_config(
    page_title="Tic-Tac-Toe: The Upside Down",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

MODE_AI = "Play vs Computer"
MODE_2P = "Two Player"
SIZE_OPTIONS = {f"{n}x{n}": n for n in SUPPORTED_SIZES}
DIFFICULTY_BY_NAME = {
    "Easy": Difficulty.BEGINNER,
    "Moderate": Difficulty.INTERMEDIATE,
    "Tough": Difficulty.TOUGH,
}

# Board width / glyph size per board dimension (px, rem)
BOARD_STYLE = {4: (460, 2.8), 5: (520, 2.3), 6: (600, 1.9), 8: (660, 1.35)}


# --------------------------------------------------------------------------- #
# Static CSS (theme)
# --------------------------------------------------------------------------- #
BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Share+Tech+Mono&display=swap');

:root {
  --red: #ff1f3d;
  --red-hot: #ff5c77;
  --cyan: #35e6ff;
  --green: #39ff14;
  --ink: #e6ebff;
}

/* ---------- background: deep blue -> black ---------- */
html, body {
  background: radial-gradient(ellipse at 50% -10%, #0f2057 0%, #081033 38%, #03061a 70%, #000000 100%) fixed !important;
  min-height: 100vh;
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
  background: transparent !important;
}
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
.block-container { padding-top: 1.6rem !important; max-width: 1100px !important; }

html, body, .stApp, .stApp p, .stApp label, .stApp span, .stApp li {
  font-family: 'Share Tech Mono', 'Courier New', monospace;
  color: var(--ink);
}

/* hide the zero-height element holding the FX layer so it adds no gap */
[data-testid="stElementContainer"]:has(.fx-layer),
.element-container:has(.fx-layer) {
  position: absolute !important; width: 0 !important; height: 0 !important; overflow: visible !important;
}

/* ---------- FX layer (vines, bolts, hanging letters) ---------- */
.fx-layer { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; }
.flash { position: absolute; inset: 0;
  background: radial-gradient(ellipse at 50% 20%, rgba(255,31,61,.35), rgba(255,31,61,0) 65%);
  opacity: 0; animation: flash 9s infinite; }
.bolt { position: absolute; top: 0; height: 55vh; width: 120px; opacity: 0;
  filter: drop-shadow(0 0 6px #ff1f3d) drop-shadow(0 0 16px #ff1f3d); animation: flash 9s infinite; }
.bolt polyline { fill: none; stroke: #ff6a80; stroke-width: 2.4; stroke-linejoin: round; stroke-linecap: round; }
.bolt-1 { left: 18%; animation-delay: 0s; }
.bolt-2 { right: 14%; animation-delay: 4.6s; transform: scaleX(-1); }
@keyframes flash {
  0%, 86%, 100% { opacity: 0; }
  87% { opacity: 1; } 88% { opacity: .15; } 89.5% { opacity: .95; } 91% { opacity: 0; } 93% { opacity: .5; } 94.5% { opacity: 0; }
}

/* vines */
.vine { position: absolute; filter: drop-shadow(0 0 4px #39ff14) drop-shadow(0 0 12px rgba(57,255,20,.55));
  animation: breathe 5s ease-in-out infinite alternate; }
.vine-l { left: 0; top: 0; height: 100%; width: 150px; }
.vine-r { right: 0; top: 0; height: 100%; width: 150px; transform: scaleX(-1); }
.vine-t { left: 0; top: 0; width: 100%; height: 130px; }
.vine-b { left: 0; bottom: 0; width: 100%; height: 130px; transform: scaleY(-1); }
.vine .stem, .vine .twig { fill: none; stroke: #2bff5a; stroke-linecap: round; stroke-linejoin: round;
  stroke-dasharray: 1; stroke-dashoffset: 0; animation: grow 7s ease-out both; }
.vine .stem { stroke-width: 3.2; }
.vine .twig { stroke-width: 1.7; stroke: #6dff8a; animation-duration: 5s; animation-delay: 1.5s; }
.vine .leaf { fill: rgba(57,255,20,.5); stroke: #b4ffc3; stroke-width: .7; animation: fadein 3s ease-out both; }
@keyframes grow { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
@keyframes fadein { from { opacity: 0; } to { opacity: 1; } }
@keyframes breathe { from { opacity: .72; } to { opacity: 1; } }

/* hanging letters */
.hang { position: absolute; top: 0; width: 0; transform-origin: 50% 0; transform: rotate(var(--a));
  animation: sway var(--d) ease-in-out var(--dl) infinite alternate; }
.hang .string { display: block; width: 1px; height: var(--len); margin: 0 auto;
  background: linear-gradient(#8f98c8, #2c3366); }
.hang .ltr { position: absolute; left: 0; top: var(--len); transform-origin: 50% 0;
  transform: translateX(-50%) rotate(var(--t)); font-family: 'Orbitron', sans-serif; font-weight: 900;
  line-height: 1; color: var(--c);
  text-shadow: 0 0 6px var(--c), 0 0 18px var(--c), 0 0 38px var(--c); animation: glowpulse 3.4s ease-in-out infinite alternate; }
@keyframes sway { from { transform: rotate(calc(var(--a) - 5deg)); } to { transform: rotate(calc(var(--a) + 5deg)); } }
@keyframes glowpulse { from { opacity: .65; } to { opacity: 1; } }

/* ---------- neon title ---------- */
.neon-title { text-align: center; font-family: 'Orbitron', sans-serif; font-weight: 900;
  font-size: clamp(1.9rem, 5.6vw, 3.8rem); letter-spacing: .14em; line-height: 1.1; margin: .2rem 0 0;
  color: #ffe3e8;
  text-shadow: 0 0 4px #fff, 0 0 12px var(--red), 0 0 26px var(--red), 0 0 54px #ff0033, 0 0 90px #ff0033;
  animation: flicker 5s infinite; }
.neon-sub { text-align: center; font-family: 'Orbitron', sans-serif; letter-spacing: .5em; font-size: .85rem;
  color: #bff7ff; text-shadow: 0 0 6px var(--cyan), 0 0 16px var(--cyan); margin: .35rem 0 .2rem; }
.zigzag { height: 14px; margin: .5rem auto 1.1rem; max-width: 560px; filter: drop-shadow(0 0 5px #ff1f3d);
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='44' height='14' viewBox='0 0 44 14'%3E%3Cpolyline points='0,7 9,7 13,1 19,13 23,5 27,9 31,7 44,7' fill='none' stroke='%23ff4d68' stroke-width='2' stroke-linejoin='round'/%3E%3C/svg%3E") repeat-x center; }
@keyframes flicker {
  0%, 18%, 22%, 62%, 64%, 100% { opacity: 1; }
  20%, 63% { opacity: .55; } 21% { opacity: .9; }
}

/* ---------- panels, cards, banners ---------- */
.panel-glow, .st-key-board_panel {
  border: 2px solid var(--red); border-radius: 16px; background: rgba(5, 8, 28, .78);
  box-shadow: 0 0 10px var(--red), 0 0 28px rgba(255,31,61,.45), inset 0 0 22px rgba(255,31,61,.22);
  backdrop-filter: blur(3px);
}
.scores { display: flex; gap: .7rem; margin: 0 auto 1rem; max-width: var(--bw, 560px); }
.score { flex: 1; text-align: center; padding: .55rem .3rem; border-radius: 12px;
  border: 1.5px solid rgba(255,31,61,.7); background: rgba(5,8,28,.78);
  box-shadow: 0 0 10px rgba(255,31,61,.35), inset 0 0 12px rgba(255,31,61,.12); transition: all .3s; }
.score .nm { font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; opacity: .85; }
.score .val { font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 1.9rem; }
.score.sx .val { color: #ff5c77; text-shadow: 0 0 10px var(--red), 0 0 24px var(--red); }
.score.so .val { color: #8cf2ff; text-shadow: 0 0 10px var(--cyan), 0 0 24px var(--cyan); }
.score.sd .val { color: #fff; text-shadow: 0 0 10px #fff; }
.score.active { border-color: #fff; box-shadow: 0 0 14px #fff, 0 0 30px var(--red), inset 0 0 18px rgba(255,31,61,.35);
  transform: translateY(-2px); }

.turn { text-align: center; max-width: var(--bw, 560px); margin: 0 auto .9rem; padding: .55rem 1rem;
  font-family: 'Orbitron', sans-serif; letter-spacing: .12em; border-radius: 10px;
  border: 1.5px solid var(--red); background: rgba(255,31,61,.1); text-shadow: 0 0 8px var(--red);
  box-shadow: 0 0 14px rgba(255,31,61,.4); }
.turn b { font-size: 1.25em; }
.turn.tx b { color: #ff5c77; text-shadow: 0 0 10px var(--red), 0 0 22px var(--red); }
.turn.to b { color: #8cf2ff; text-shadow: 0 0 10px var(--cyan), 0 0 22px var(--cyan); }

.banner { text-align: center; max-width: var(--bw, 560px); margin: 0 auto .8rem; padding: 1rem 1rem;
  font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: clamp(1rem, 2.6vw, 1.5rem); letter-spacing: .1em;
  border-radius: 12px; border: 2px solid #fff; animation: zapbanner .7s infinite alternate; }
.banner small { display: block; font-weight: 500; font-size: .7em; letter-spacing: .15em; margin-top: .35rem; opacity: .9; }
.banner.win { color: #fff; background: rgba(255,31,61,.28); text-shadow: 0 0 10px #fff, 0 0 24px var(--red); }
.banner.lose { color: #ffd0d8; background: rgba(120,0,30,.5); text-shadow: 0 0 10px var(--red); }
.banner.draw { color: #d8fbff; background: rgba(20,120,150,.3); border-color: var(--cyan);
  text-shadow: 0 0 10px var(--cyan); animation-name: zapcyan; }
@keyframes zapbanner {
  from { box-shadow: 0 0 10px #fff, 0 0 22px var(--red), inset 0 0 14px rgba(255,31,61,.4); }
  to { box-shadow: 0 0 20px #fff, 0 0 50px var(--red), 0 0 80px var(--red), inset 0 0 28px rgba(255,31,61,.7); }
}
@keyframes zapcyan {
  from { box-shadow: 0 0 10px var(--cyan), inset 0 0 12px rgba(53,230,255,.3); }
  to { box-shadow: 0 0 26px var(--cyan), 0 0 56px var(--cyan), inset 0 0 22px rgba(53,230,255,.5); }
}
.hint-msg { text-align: center; max-width: var(--bw, 560px); margin: .6rem auto 0; padding: .5rem .8rem;
  border-radius: 10px; border: 1.5px dashed #ffe14a; color: #fff6c2; background: rgba(255,225,74,.08);
  text-shadow: 0 0 8px #ffe14a; }

/* ---------- widgets ---------- */
.stButton, .stButton > button { width: 100% !important; }
.stButton > button {
  font-family: 'Orbitron', sans-serif; letter-spacing: .06em; color: #fff;
  background: linear-gradient(180deg, rgba(40,6,18,.95), rgba(10,4,22,.95));
  border: 2px solid var(--red); border-radius: 10px;
  box-shadow: 0 0 8px var(--red), inset 0 0 10px rgba(255,31,61,.3); transition: all .2s;
}
.stButton > button:hover:not(:disabled) { color: #fff; border-color: #fff; transform: translateY(-1px);
  box-shadow: 0 0 14px #fff, 0 0 30px var(--red), inset 0 0 16px rgba(255,31,61,.5); }
.stButton > button:disabled { opacity: .45; cursor: not-allowed; }

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #060c2c 0%, #02030f 100%) !important;
  border-right: 2px solid var(--red); box-shadow: 0 0 22px rgba(255,31,61,.55);
}
[data-testid="stSidebar"] *, [data-testid="stSidebar"] label p { color: var(--ink); }
.side-title { font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 1.15rem; letter-spacing: .12em;
  color: #ffe3e8; text-shadow: 0 0 8px var(--red), 0 0 20px var(--red); margin-bottom: .6rem; }
[data-baseweb="select"] > div { background: #0a1034 !important; border: 1.5px solid var(--red) !important;
  box-shadow: 0 0 8px rgba(255,31,61,.45); color: #fff !important; }
[data-baseweb="select"] * { color: #fff !important; }
[data-baseweb="popover"] ul, [data-baseweb="menu"] { background: #0a1034 !important; }
[data-baseweb="popover"] li { color: #fff !important; }
[data-baseweb="popover"] li:hover { background: rgba(255,31,61,.3) !important; }

/* ---------- board ---------- */
.st-key-board_panel { padding: 1rem; margin: 0 auto; max-width: var(--bw, 560px); }
.st-key-board_panel [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .4rem !important; }
.st-key-board_panel [data-testid="stColumn"], .st-key-board_panel [data-testid="column"] {
  min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }
.st-key-board_panel [data-testid="stVerticalBlock"] { gap: .4rem !important; }
.st-key-board_panel .stButton > button {
  aspect-ratio: 1 / 1; height: auto !important; min-height: 0 !important; padding: 0 !important;
  display: flex; align-items: center; justify-content: center; border-radius: 10px;
  background: rgba(4, 6, 26, .9);
}
.st-key-board_panel .stButton > button p {
  font-family: 'Orbitron', sans-serif !important; font-weight: 900 !important;
  font-size: var(--glyph, 2rem) !important; line-height: 1 !important; margin: 0 !important;
}
.st-key-board_panel .stButton > button:disabled { opacity: .6; }
.st-key-controls, .st-key-banner_box { max-width: var(--bw, 560px); margin: 1rem auto 0; }

@keyframes zap {
  from { box-shadow: 0 0 8px #fff, 0 0 20px var(--red), 0 0 34px var(--red); }
  to { box-shadow: 0 0 16px #fff, 0 0 44px var(--red), 0 0 74px #ff0033; }
}
@keyframes hintpulse {
  from { box-shadow: 0 0 6px #ffe14a, inset 0 0 8px rgba(255,225,74,.3); }
  to { box-shadow: 0 0 20px #ffe14a, 0 0 40px #ffe14a, inset 0 0 18px rgba(255,225,74,.55); }
}
@media (max-width: 640px) {
  .neon-sub { letter-spacing: .25em; font-size: .7rem; }
  .vine-t, .vine-b { display: none; }
}
"""


# --------------------------------------------------------------------------- #
# FX layer builders (vines, lightning, hanging letters)
# --------------------------------------------------------------------------- #
def _compact(html: str) -> str:
    """Collapse to one line so Markdown never treats it as code or splits HTML blocks."""
    return " ".join(line.strip() for line in html.splitlines() if line.strip())


def _vine_svg(rng: random.Random, css_class: str, vertical: bool) -> str:
    """Procedural glowing vine hugging one edge. Local coords: u along the edge, v away from it."""
    length, thick = 1000, 150 if vertical else 130
    viewbox = f"0 0 {thick} {length}" if vertical else f"0 0 {length} {thick}"

    def xy(u: float, v: float) -> str:
        return f"{v:.1f},{u:.1f}" if vertical else f"{u:.1f},{v:.1f}"

    out_angle = 0 if vertical else 90  # direction pointing away from the edge
    parts = []
    for s in range(3):
        base = 8 + s * 12
        amp = 9 + s * 5
        wave = 55 + s * 28
        phase = rng.uniform(0, 6.28)

        def v_at(u: float) -> float:
            return base + amp * math.sin(u / wave + phase)

        pts = " L".join(xy(u, v_at(u)) for u in range(0, length + 1, 10))
        parts.append(f'<path class="stem" pathLength="1" d="M{pts}" style="animation-delay:{s * 0.8:.1f}s"/>')

        for _ in range(13):
            u = rng.uniform(30, length - 30)
            v0 = v_at(u)
            eu = u + rng.uniform(-60, 70)
            ev = base + rng.uniform(26, thick - 14)
            cu, cv = u + rng.uniform(-35, 35), (v0 + ev) / 2 + rng.uniform(-12, 12)
            parts.append(
                f'<path class="twig" pathLength="1" d="M{xy(u, v0)} Q{xy(cu, cv)} {xy(eu, ev)}"/>'
            )
            for lu, lv in ((eu, ev), ((u + eu) / 2, (v0 + ev) / 2)):
                ang = out_angle + rng.uniform(-80, 80)
                sc = rng.uniform(0.9, 1.7)
                px, py = (lv, lu) if vertical else (lu, lv)
                parts.append(
                    f'<path class="leaf" d="M0 0 Q5 -7 14 0 Q5 7 0 0Z" '
                    f'transform="translate({px:.1f} {py:.1f}) rotate({ang:.0f}) scale({sc:.2f})" '
                    f'style="animation-delay:{rng.uniform(1, 6):.1f}s"/>'
                )
    return (
        f'<svg class="vine {css_class}" viewBox="{viewbox}" preserveAspectRatio="xMinYMin slice" '
        f'xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'
    )


def _bolt_svg(rng: random.Random, css_class: str) -> str:
    w, h = 100, 420
    x, y = w / 2, 0.0
    pts = [(x, y)]
    while y < h:
        y += rng.uniform(26, 52)
        x = max(10.0, min(w - 10.0, x + rng.uniform(-30, 30)))
        pts.append((x, y))
    main = " ".join(f"{px:.0f},{py:.0f}" for px, py in pts)
    bx, by = pts[len(pts) // 2]
    branch = " ".join(
        f"{bx + i * rng.uniform(8, 18):.0f},{by + i * rng.uniform(22, 36):.0f}" for i in range(4)
    )
    return (
        f'<svg class="bolt {css_class}" viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
        f'xmlns="http://www.w3.org/2000/svg"><polyline points="{main}"/><polyline points="{branch}"/></svg>'
    )


def _hanging_letters(rng: random.Random, count: int = 15) -> str:
    colors = ["#ff1f3d", "#35e6ff", "#ff3df2", "#ffe14a", "#ff1f3d", "#35e6ff"]
    items = []
    for i in range(count):
        left = 3 + (94 * i / count) + rng.uniform(-2.5, 2.5)
        items.append(
            f'<div class="hang" style="left:{left:.1f}%;--a:{rng.uniform(-38, 38):.0f}deg;'
            f"--d:{rng.uniform(4.5, 9):.1f}s;--dl:-{rng.uniform(0, 8):.1f}s;--len:{rng.randint(70, 330)}px\">"
            f'<span class="string"></span>'
            f'<span class="ltr" style="--t:{rng.uniform(-48, 48):.0f}deg;--c:{rng.choice(colors)};'
            f'font-size:{rng.randint(34, 78)}px">{rng.choice("XO")}</span></div>'
        )
    return "".join(items)


@st.cache_data(show_spinner=False)
def build_fx_html(seed: int) -> str:
    rng = random.Random(seed)
    layer = (
        '<div class="fx-layer">'
        '<div class="flash"></div>'
        + _hanging_letters(rng)
        + _bolt_svg(rng, "bolt-1")
        + _bolt_svg(rng, "bolt-2")
        + _vine_svg(rng, "vine-l", True)
        + _vine_svg(rng, "vine-r", True)
        + _vine_svg(rng, "vine-t", False)
        + _vine_svg(rng, "vine-b", False)
        + "</div>"
    )
    return _compact(f"<style>{BASE_CSS}</style>") + layer


# --------------------------------------------------------------------------- #
# Session state & callbacks
# --------------------------------------------------------------------------- #
def init_state() -> None:
    ss = st.session_state
    ss.setdefault("fx_seed", random.randrange(10**6))
    ss.setdefault("scores", {X: 0, O: 0, "draw": 0})
    ss.setdefault("config", None)
    ss.setdefault("hint_cell", None)
    ss.setdefault("recorded", False)


def sync_game(mode: str, size: int, win_length: int) -> None:
    """(Re)create the game when structural settings change; scores restart too."""
    ss = st.session_state
    config = (mode, size, win_length)
    if ss.config != config:
        ss.config = config
        ss.game = TicTacToeGame(size=size, win_length=win_length)
        ss.scores = {X: 0, O: 0, "draw": 0}
        ss.hint_cell = None
        ss.recorded = False


def record_result() -> None:
    ss = st.session_state
    g = ss.game
    if g.is_over and not ss.recorded:
        ss.recorded = True
        if g.is_draw:
            ss.scores["draw"] += 1
        else:
            ss.scores[g.winner] += 1


def on_cell_click(r: int, c: int) -> None:
    ss = st.session_state
    g = ss.game
    if not g.make_move(r, c):
        return
    ss.hint_cell = None
    record_result()
    if ss.mode == MODE_AI and not g.is_over:
        g.play_ai_turn(DIFFICULTY_BY_NAME[ss.ai_difficulty])
        record_result()


def on_hint() -> None:
    ss = st.session_state
    ss.hint_cell = ss.game.get_hint()


def on_reset_round() -> None:
    ss = st.session_state
    ss.game.reset()
    ss.hint_cell = None
    ss.recorded = False


def on_reset_scores() -> None:
    st.session_state.scores = {X: 0, O: 0, "draw": 0}


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #
def player_labels(vs_ai: bool) -> dict:
    return {X: "You (X)", O: "Computer (O)"} if vs_ai else {X: "Player X", O: "Player O"}


def scoreboard_html(g: TicTacToeGame, labels: dict, scores: dict) -> str:
    def card(cls: str, name: str, val: int, active: bool) -> str:
        return (
            f'<div class="score {cls}{" active" if active else ""}">'
            f'<div class="nm">{name}</div><div class="val">{val}</div></div>'
        )

    play = not g.is_over
    return (
        '<div class="scores">'
        + card("sx", labels[X], scores[X], play and g.current_player == X)
        + card("sd", "Draws", scores["draw"], False)
        + card("so", labels[O], scores[O], play and g.current_player == O)
        + "</div>"
    )


def status_html(g: TicTacToeGame, labels: dict, vs_ai: bool) -> str:
    if g.winner is not None:
        sym = SYMBOLS[g.winner]
        if vs_ai:
            if g.winner == X:
                msg, cls = "⚡ YOU DEFEATED THE DEMOGORGON! ⚡", "win"
            else:
                msg, cls = "👾 THE UPSIDE DOWN CLAIMED YOU", "lose"
        else:
            msg, cls = f"⚡ PLAYER {sym} CONQUERS THE GATE! ⚡", "win"
        sub = f"{labels[g.winner]} connected {g.win_length} in a row"
        return f'<div class="banner {cls}">{msg}<small>{sub}</small></div>'
    if g.is_draw:
        return '<div class="banner draw">🌀 STALEMATE — THE GATE STAYS OPEN<small>It\'s a draw</small></div>'
    sym = SYMBOLS[g.current_player]
    who = "YOUR TURN" if (vs_ai and g.current_player == X) else f"{labels[g.current_player].split(' (')[0].upper()}'S TURN"
    return f'<div class="turn t{sym.lower()}">▶ {who} — <b>{sym}</b></div>'


def dynamic_css(g: TicTacToeGame, hint_cell) -> str:
    """Per-render CSS: board sizing plus per-cell colours / win glow / hint pulse."""
    n = g.size
    width, glyph = BOARD_STYLE[n]

    def sel(cells, suffix="button"):
        return ", ".join(f".st-key-cell_{r}_{c} {suffix}" for r, c in cells) or ".st-key-none"

    x_cells = [(r, c) for r in range(n) for c in range(n) if g.board[r, c] == X]
    o_cells = [(r, c) for r in range(n) for c in range(n) if g.board[r, c] == O]
    css = [
        f":root{{--bw:{width}px;--glyph:{glyph}rem;}}",
        f"{sel(x_cells)}{{border-color:#ff3b5c !important;opacity:1 !important;}}",
        f"{sel(x_cells, 'button p')}{{color:#ff4d68 !important;text-shadow:0 0 8px #ff1f3d,0 0 20px #ff1f3d,0 0 36px #ff0033;}}",
        f"{sel(o_cells)}{{border-color:#35e6ff !important;opacity:1 !important;box-shadow:0 0 8px #35e6ff,inset 0 0 12px rgba(53,230,255,.3) !important;}}",
        f"{sel(o_cells, 'button p')}{{color:#8cf2ff !important;text-shadow:0 0 8px #35e6ff,0 0 20px #35e6ff,0 0 36px #35e6ff;}}",
    ]
    if g.winning_line:
        css.append(
            f"{sel(g.winning_line)}{{border-color:#fff !important;background:rgba(255,31,61,.3) !important;"
            f"animation:zap .45s infinite alternate !important;}}"
        )
        css.append(f"{sel(g.winning_line, 'button p')}{{color:#fff !important;}}")
    if hint_cell is not None and not g.is_over:
        css.append(
            f"{sel([tuple(hint_cell)])}{{border-color:#ffe14a !important;background:rgba(255,225,74,.12) !important;"
            f"animation:hintpulse .8s infinite alternate !important;}}"
        )
    return "".join(css)


# --------------------------------------------------------------------------- #
# Main app
# --------------------------------------------------------------------------- #
init_state()
st.markdown(build_fx_html(st.session_state.fx_seed), unsafe_allow_html=True)

# ----- Header -----
st.markdown(
    '<div class="neon-title">TIC·TAC·TOE</div>'
    '<div class="neon-sub">THE UPSIDE DOWN EDITION</div>'
    '<div class="zigzag"></div>',
    unsafe_allow_html=True,
)

# ----- Main-page game setup -----
setup_cols = st.columns(4)
with setup_cols[0]:
    mode = st.selectbox("Game Mode", [MODE_AI, MODE_2P], key="mode")
with setup_cols[1]:
    st.selectbox(
        "AI Difficulty",
        list(DIFFICULTY_BY_NAME),
        index=1,
        key="ai_difficulty",
        disabled=(mode == MODE_2P),
        help="Choose Easy, Moderate, or Tough when playing against the computer.",
    )
with setup_cols[2]:
    size_label = st.selectbox("Board Size", list(SIZE_OPTIONS), key="size_label")
    size = SIZE_OPTIONS[size_label]
with setup_cols[3]:
    win_options = list(range(3, size + 1))
    default_win_length = DEFAULT_WIN_LENGTH[size]
    win_length = st.selectbox(
        "Win Target",
        win_options,
        index=win_options.index(default_win_length),
        key=f"win_{size}",
        format_func=lambda n: f"{n} in a row",
    )
st.caption("Choose a board size and win target. Changing the mode, size, or target starts a fresh game.")
score_col, _ = st.columns([1, 3])
with score_col:
    st.button("♻️ Reset Scores", key="reset_scores", on_click=on_reset_scores)

sync_game(mode, size, win_length)
game: TicTacToeGame = st.session_state.game
vs_ai = mode == MODE_AI
labels = player_labels(vs_ai)

# ----- Scoreboard + status (turn indicator / win-draw banner) -----
st.markdown(
    f"<style>{dynamic_css(game, st.session_state.hint_cell)}</style>"
    + scoreboard_html(game, labels, st.session_state.scores)
    + status_html(game, labels, vs_ai),
    unsafe_allow_html=True,
)
if game.is_over:
    with st.container(key="banner_box"):
        st.button("🔄 Play Again", key="reset_over", on_click=on_reset_round)

# ----- Board -----
with st.container(key="board_panel"):
    for r in range(game.size):
        for c, col in enumerate(st.columns(game.size, gap="small")):
            value = int(game.board[r, c])
            with col:
                st.button(
                    SYMBOLS[value] or "\u00a0",
                    key=f"cell_{r}_{c}",
                    on_click=on_cell_click,
                    args=(r, c),
                    disabled=game.is_over or value != EMPTY,
                )

# ----- Controls: hint + reset -----
with st.container(key="controls"):
    hint_col, reset_col = st.columns(2)
    with hint_col:
        st.button(
            "💡 Hint (1x Use)" if not game.hint_used else "💡 Hint Used",
            key="hint_btn",
            on_click=on_hint,
            disabled=not game.hint_available,
        )
    with reset_col:
        st.button("🔄 Restart Round", key="reset_round", on_click=on_reset_round)

hint = st.session_state.hint_cell
if hint is not None and not game.is_over:
    st.markdown(
        f'<div class="hint-msg">💡 Suggested move: row <b>{hint[0] + 1}</b>, column <b>{hint[1] + 1}</b> '
        f"(glowing yellow)</div>",
        unsafe_allow_html=True,
    )