import sys
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

"""
bot.py
──────
CricketPulse AI — Telegram Bot entry point.
Run: python bot.py
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters,
)
from telegram.constants import ParseMode

import data_bridge
import agent_brain
import utils
from config import (
    TELEGRAM_TOKEN, MOCK_MODE,
    MODE_ANALYST, MODE_BEGINNER, MODE_MEME, DEFAULT_MODE,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── Per-chat state ──────────────────────────────────────────────────
USER_STATE: dict[int, dict] = {}

def get_state(chat_id: int) -> dict:
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {
            "mode":           DEFAULT_MODE,
            "selected_match": None,
            "history":        [],
        }
    return USER_STATE[chat_id]


async def send_html(update: Update, text: str, reply_markup=None):
    await update.effective_message.reply_text(
        utils.truncate(text),
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )


# ── Keyboard builders ───────────────────────────────────────────────

def _dashboard_keyboard(match_id: str) -> InlineKeyboardMarkup:
    """Buttons that appear below the Match Dashboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Stats",   callback_data=f"stat_{match_id}"),
            InlineKeyboardButton("😂 Meme",    callback_data=f"meme_{match_id}"),
            InlineKeyboardButton("🛰️ War Room",  callback_data=f"warrm_{match_id}"),
        ],
        [
            InlineKeyboardButton("🧠 Coach",   callback_data=f"xcoach_{match_id}"),
            InlineKeyboardButton("🔮 Predict", callback_data=f"predict_{match_id}"),
            InlineKeyboardButton("🔄 Refresh", callback_data=f"match_{match_id}"),
        ],
    ])


def _back_keyboard(match_id: str) -> InlineKeyboardMarkup:
    """Back-to-dashboard button."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ Dashboard", callback_data=f"match_{match_id}"),
        InlineKeyboardButton("🔄 Refresh",   callback_data=f"match_{match_id}"),
    ]])


# ── /start ──────────────────────────────────────────────────────────
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_chat.id)
    icons = {MODE_ANALYST: "🧠", MODE_BEGINNER: "🌱", MODE_MEME: "😂"}
    icon  = icons.get(state["mode"], "🧠")

    text = (
        "🏏 <b>CricketPulse AI — Your Digital Cricket Coach</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<i>\"Everyone has a score bot. We built a Digital Coach\n"
        "that thinks like a captain.\"</i>\n\n"
        "<b>Commands:</b>\n"
        "🔴 /live       — Live Match Dashboard with inline controls\n"
        "📋 /match      — Full batting &amp; bowling scorecard\n"
        "🔮 /predict    — AI next-over prediction\n"
        "🚨 /momentum   — Turning point &amp; momentum detection\n"
        "🎯 /coach      — Tactical advice for both teams\n"
        "⚙️ /mode       — Switch Analyst / Beginner / Meme mode\n"
        "❓ /help       — Full command guide\n\n"
        f"<b>Current Mode:</b> {icon} {state['mode']}\n\n"
        "<b>Or just ask me:</b>\n"
        "<i>\"How should they approach the death overs?\"\n"
        "\"Should they bring in a spinner now?\"\n"
        "\"Bhai, yeh match kaun jeetega?\"</i>"
    )
    await send_html(update, text)


# ── /help ───────────────────────────────────────────────────────────
async def help_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🏏 <b>CricketPulse AI — Help</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Live Data</b>\n"
        "/live       — Dashboard: scores, win bar, last 12 balls\n"
        "/match      — Full scorecard with batting &amp; bowling\n\n"
        "<b>AI Coaching</b>\n"
        "/predict    — Next over: runs range + wicket probability\n"
        "/momentum   — Turning points &amp; momentum analysis\n"
        "/coach      — Tactical advice right now\n\n"
        "<b>Settings</b>\n"
        "/mode       — Analyst 🧠 / Beginner 🌱 / Meme 😂\n\n"
        "<b>Free Chat</b>\n"
        "• <i>\"Who should bowl the 19th over?\"</i>\n"
        "• <i>\"Explain the DLS method\"</i>\n"
        "• <i>\"Kohli ko kaise out karein?\"</i>"
    )
    await send_html(update, text)


# ── /live — Shows list, each opens dashboard ─────────────────────
async def live_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.effective_message.reply_text("📡 Fetching live matches...")
    matches = await data_bridge.get_live_matches()

    if not matches:
        await msg.edit_text("😔 No live matches right now. Check back soon!")
        return

    # One button per match → opens dashboard
    buttons = [
        [InlineKeyboardButton(
            f"{'🔴' if m.get('match_started') and not m.get('match_ended') else '🔵'} "
            f"{m.get('short_name', m.get('match_name','Match'))}",
            callback_data=f"match_{m['match_id']}"
        )]
        for m in matches
    ]

    text_lines = ["<b>🏏 Live &amp; Upcoming IPL Matches</b>\n"]
    for m in matches:
        text_lines.append(utils.format_live_match_card(m))
        text_lines.append("")
    text_lines.append("👇 <i>Tap a match for the full Dashboard:</i>")

    await msg.edit_text(
        utils.truncate("\n".join(text_lines)),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ── /match ──────────────────────────────────────────────────────────
async def match_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state    = get_state(update.effective_chat.id)
    match_id = state.get("selected_match")

    if not match_id:
        matches  = await data_bridge.get_live_matches()
        match_id = matches[0]["match_id"] if matches else None

    if not match_id:
        await send_html(update, "❌ No match selected. Use /live first.")
        return

    msg = await update.effective_message.reply_text("📋 Loading scorecard...")
    sc  = await data_bridge.get_scorecard(match_id)
    await msg.edit_text(
        utils.truncate(utils.format_scorecard(sc)),
        parse_mode=ParseMode.HTML,
        reply_markup=_back_keyboard(match_id),
    )


# ── /predict ────────────────────────────────────────────────────────
async def predict_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_chat.id)
    msg   = await update.effective_message.reply_text("🔮 Calculating prediction...")
    resp  = await agent_brain.analyze_predict(state["mode"], state.get("history"))
    state = get_state(update.effective_chat.id)
    mid   = state.get("selected_match", "")
    await msg.edit_text(
        utils.truncate(resp),
        parse_mode=ParseMode.HTML,
        reply_markup=_back_keyboard(mid) if mid else None,
    )

# ── /simulate (Butterfly Effect) ────────────────────────────────────
async def simulate_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await send_html(update, "🦋 <b>Butterfly Effect Simulation</b>\nUsage: <code>/simulate What if Dhoni comes to bat next?</code>")
        return
        
    user_text = " ".join(ctx.args)
    chat_id = update.effective_chat.id
    state = get_state(chat_id)
    
    msg = await update.effective_message.reply_text("🦋 Entering alternative timeline...")
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    resp = await agent_brain.process_message(f"/simulate {user_text}", state["mode"], state.get("history"))
    mid = state.get("selected_match", "")
    await msg.edit_text(
        utils.truncate(resp),
        parse_mode=ParseMode.HTML,
        reply_markup=_back_keyboard(mid) if mid else None,
    )


# ── /momentum ───────────────────────────────────────────────────────
async def momentum_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_chat.id)
    msg   = await update.effective_message.reply_text("🚨 Analyzing momentum shifts...")
    resp  = await agent_brain.analyze_momentum(state["mode"], state.get("history"))
    mid   = state.get("selected_match", "")
    await msg.edit_text(
        utils.truncate(resp),
        parse_mode=ParseMode.HTML,
        reply_markup=_back_keyboard(mid) if mid else None,
    )


# ── /coach ──────────────────────────────────────────────────────────
async def coach_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_chat.id)
    msg   = await update.effective_message.reply_text("🎯 Coach is analyzing...")
    resp  = await agent_brain.analyze_coach(state["mode"], state.get("history"))
    mid   = state.get("selected_match", "")
    await msg.edit_text(
        utils.truncate(resp),
        parse_mode=ParseMode.HTML,
        reply_markup=_back_keyboard(mid) if mid else None,
    )


# ── /mode ───────────────────────────────────────────────────────────
async def mode_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_chat.id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 Analyst   — Deep tactical stats",  callback_data="mode_ANALYST")],
        [InlineKeyboardButton("🌱 Beginner  — Explain everything",   callback_data="mode_BEGINNER")],
        [InlineKeyboardButton("😂 Meme      — Full Hinglish banter", callback_data="mode_MEME")],
        [InlineKeyboardButton("🛰️ Strategy — War Room Forecasts",   callback_data="mode_STRATEGY")],
    ])
    await send_html(
        update,
        f"<b>Select coaching mode:</b>\nCurrently: <b>{state['mode']}</b>",
        reply_markup=keyboard,
    )


# ── Callback router ──────────────────────────────────────────────────
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = update.effective_chat.id
    state   = get_state(chat_id)
    data    = query.data or ""

    # ── Mode switch ──────────────────────────────────────────────
    if data.startswith("mode_"):
        await query.answer()
        new_mode = data.replace("mode_", "")
        state["mode"] = new_mode
        labels = {
            MODE_ANALYST:  "🧠 <b>Analyst mode</b> — tactical deep-dives incoming.",
            MODE_BEGINNER: "🌱 <b>Beginner mode</b> — I'll explain every term.",
            MODE_MEME:     "😂 <b>Meme mode ON!</b> Ab Hinglish mein full banter!",
            "STRATEGY":    "🛰️ <b>Strategy mode</b> — Tactical forecasting enabled.",
        }
        await query.edit_message_text(
            labels.get(new_mode, "Mode updated."), parse_mode=ParseMode.HTML
        )
        return

    # ── Dashboard (match select + refresh) — EDIT in place ───────
    if data.startswith("match_"):
        await query.answer("Loading dashboard...")
        match_id = data.replace("match_", "")
        state["selected_match"] = match_id

        await query.edit_message_text("📡 Loading dashboard...", parse_mode=ParseMode.HTML)

        sc    = await data_bridge.get_scorecard(match_id)
        last5 = await data_bridge.get_last_5_overs(match_id)
        text  = utils.format_match_dashboard(sc, last5)

        await query.edit_message_text(
            utils.truncate(text, 4096),
            parse_mode=ParseMode.HTML,
            reply_markup=_dashboard_keyboard(match_id),
        )
        return

    # ── Stats — EDIT dashboard in place ──────────────────────────
    if data.startswith("stat_"):
        await query.answer("Loading scorecard...")
        match_id = data.replace("stat_", "")
        await query.edit_message_text("📊 Loading full scorecard...", parse_mode=ParseMode.HTML)
        sc   = await data_bridge.get_scorecard(match_id)
        text = utils.format_scorecard(sc)
        await query.edit_message_text(
            utils.truncate(text, 4096),
            parse_mode=ParseMode.HTML,
            reply_markup=_back_keyboard(match_id),
        )
        return

    # ── War Room — INSTANT deterministic strategy ────────────────
    if data.startswith("warrm_"):
        await query.answer("Deploying War Room...")
        match_id = data.replace("warrm_", "")
        
        await query.edit_message_text("🛰️ Analyzing momentum...", parse_mode=ParseMode.HTML)
        sc    = await data_bridge.get_scorecard(match_id)
        last5 = await data_bridge.get_last_5_overs(match_id)
        
        text = utils.format_war_room_report(sc, last5)
        
        await query.edit_message_text(
            utils.truncate(text, 4096),
            parse_mode=ParseMode.HTML,
            reply_markup=_back_keyboard(match_id),
        )
        return

    # ── AI buttons — SEND NEW MESSAGE (keeps dashboard alive) ─────
    # Meme (WITH VOICE NOTE)
    if data.startswith("meme_"):
        await query.answer("Generating Indore Banter & Voice Note...")
        match_id = data.replace("meme_", "")
        await ctx.bot.send_chat_action(chat_id=chat_id, action="record_voice")
        
        resp = await agent_brain.process_message(
            "Iss match ke baare mein full Hinglish meme commentary do — "
            "players roast karo, dramatic predictions karo, banter ON!",
            MODE_MEME, state.get("history"),
        )
        
        # Strip HTML for TTS
        clean_text = resp.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("<code>", "").replace("</code>", "")
        # Remove emojis for cleaner TTS (rough heuristic)
        import re
        clean_text = re.sub(r'[^\w\s.,!?\'"\-]', '', clean_text)
        
        # Generate Audio
        try:
            import os
            from gtts import gTTS
            tts = gTTS(text=clean_text[:400], lang="hi", slow=False)
            filename = f"meme_{chat_id}.mp3"
            tts.save(filename)
            
            with open(filename, "rb") as audio:
                await ctx.bot.send_voice(chat_id=chat_id, voice=audio, caption="🎤 <b>Coach Voice Note</b>", parse_mode=ParseMode.HTML)
                
            os.remove(filename)
        except Exception as e:
            log.error(f"TTS failed: {e}")
        
        # Send text as well
        await ctx.bot.send_message(chat_id=chat_id, text=utils.truncate(resp, 4096), parse_mode=ParseMode.HTML)
        return

    # Coach
    if data.startswith("xcoach_"):
        await query.answer("Coach analyzing... (may take 5-10s)")  # instant popup
        match_id = data.replace("xcoach_", "")
        await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
        resp = await agent_brain.analyze_coach(state["mode"], state.get("history"))
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=utils.truncate(resp, 4096),
            parse_mode=ParseMode.HTML,
        )
        return

    # Predict
    if data.startswith("predict_"):
        await query.answer("Calculating prediction... (may take 5-10s)")  # instant popup
        match_id = data.replace("predict_", "")
        await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
        resp = await agent_brain.analyze_predict(state["mode"], state.get("history"))
        await ctx.bot.send_message(
            chat_id=chat_id,
            text=utils.truncate(resp, 4096),
            parse_mode=ParseMode.HTML,
        )
        return


# ── Free-text → Gemini ───────────────────────────────────────────────
async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    chat_id   = update.effective_chat.id
    state     = get_state(chat_id)

    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")

    response = await agent_brain.process_message(
        user_text, state["mode"], state.get("history")
    )

    from google.genai import types as gt
    state["history"].append(gt.Content(role="user",  parts=[gt.Part(text=user_text)]))
    state["history"].append(gt.Content(role="model", parts=[gt.Part(text=response)]))
    state["history"] = state["history"][-10:]

    mid = state.get("selected_match", "")
    await send_html(
        update,
        response,
        reply_markup=_back_keyboard(mid) if mid else None,
    )


# ── Bot setup ─────────────────────────────────────────────────────────
async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start",    "Start CricketPulse AI"),
        BotCommand("live",     "Live Match Dashboard"),
        BotCommand("match",    "Full scorecard"),
        BotCommand("predict",  "Next-over AI prediction"),
        BotCommand("momentum", "Turning point detection"),
        BotCommand("coach",    "Tactical coaching advice"),
        BotCommand("mode",     "Switch analysis mode"),
        BotCommand("help",     "Help & command guide"),
    ])
    log.info("CricketPulse AI ready | Mode: %s", "MOCK" if MOCK_MODE else "LIVE API")


def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",    start_handler))
    app.add_handler(CommandHandler("help",     help_handler))
    app.add_handler(CommandHandler("live",     live_handler))
    app.add_handler(CommandHandler("match",    match_handler))
    app.add_handler(CommandHandler("predict",  predict_handler))
    app.add_handler(CommandHandler("simulate", simulate_handler))
    app.add_handler(CommandHandler("momentum", momentum_handler))
    app.add_handler(CommandHandler("coach",    coach_handler))
    app.add_handler(CommandHandler("mode",     mode_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("=" * 52)
    print(" CricketPulse AI -- Digital Coach")
    print(f" Data: {'MOCK' if MOCK_MODE else 'LIVE API'}")
    print(" Running... Ctrl+C to stop")
    print("=" * 52)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
