import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import TELEGRAM_TOKEN, TICKERS, NEWS_INTERVAL_HOURS
from market_data import get_quote, get_forecast, get_news

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

subscribers: set[int] = set()


def format_quote(q: dict) -> str:
    arrow = "🟢" if q["change"] >= 0 else "🔴"
    return (
        f"{arrow} <b>{q['ticker']}</b>: ${q['price']}  "
        f"({q['change']:+.2f} / {q['change_pct']:+.2f}%)\n"
        f"   H: ${q['high']}  L: ${q['low']}  Vol: {q['volume']:,}"
    )


def format_forecast(f: dict) -> str:
    lines = [f"🔮 <b>{f['ticker']}</b> — {f['outlook']}"]
    lines.append(f"   RSI: {f['rsi']}  MACD: {f['macd']} / signal: {f['macd_signal']}")
    lines.append(f"   SMA20: ${f['sma_20']}" + (f"  SMA50: ${f['sma_50']}" if f['sma_50'] else ""))
    for s in f["signals"]:
        lines.append(f"   • {s}")
    return "\n".join(lines)


def format_news(ticker: str, items: list[dict]) -> str:
    if not items:
        return f"📰 <b>{ticker}</b>: нет свежих новостей"
    lines = [f"📰 <b>{ticker}</b> — последние новости:"]
    for n in items:
        pub = f" ({n['publisher']})" if n["publisher"] else ""
        if n["link"]:
            lines.append(f'   • <a href="{n["link"]}">{n["title"]}</a>{pub}')
        else:
            lines.append(f"   • {n['title']}{pub}")
    return "\n".join(lines)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    subscribers.add(update.effective_chat.id)
    await update.message.reply_text(
        "👋 Привет! Я бот для новостей и прогнозов по акциям.\n\n"
        f"Отслеживаемые тикеры: {', '.join(TICKERS)}\n\n"
        "Команды:\n"
        "/prices — текущие котировки\n"
        "/forecast — технический прогноз\n"
        "/news — последние новости\n"
        "/all — всё сразу\n"
        "/subscribe — подписка на авторассылку\n"
        "/unsubscribe — отписка\n"
        "/ticker AAPL — инфо по конкретному тикеру",
        parse_mode="HTML",
    )


async def cmd_prices(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tickers = [ctx.args[0].upper()] if ctx.args else TICKERS
    await update.message.reply_text("⏳ Загружаю котировки...")
    parts = []
    for t in tickers:
        q = get_quote(t)
        parts.append(format_quote(q) if q else f"❌ {t}: данные недоступны")
    await update.message.reply_text("\n\n".join(parts), parse_mode="HTML")


async def cmd_forecast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tickers = [ctx.args[0].upper()] if ctx.args else TICKERS
    await update.message.reply_text("⏳ Анализирую...")
    parts = []
    for t in tickers:
        f = get_forecast(t)
        parts.append(format_forecast(f) if f else f"❌ {t}: недостаточно данных")
    await update.message.reply_text(
        "⚠️ <i>Прогноз основан на технических индикаторах и не является инвестиционной рекомендацией.</i>\n\n"
        + "\n\n".join(parts),
        parse_mode="HTML",
    )


async def cmd_news(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tickers = [ctx.args[0].upper()] if ctx.args else TICKERS
    await update.message.reply_text("⏳ Собираю новости...")
    parts = []
    for t in tickers:
        items = get_news(t)
        parts.append(format_news(t, items))
    await update.message.reply_text("\n\n".join(parts), parse_mode="HTML", disable_web_page_preview=True)


async def cmd_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Загружаю полный отчёт...")
    parts = []
    for t in TICKERS:
        section = []
        q = get_quote(t)
        if q:
            section.append(format_quote(q))
        f = get_forecast(t)
        if f:
            section.append(format_forecast(f))
        items = get_news(t)
        section.append(format_news(t, items))
        parts.append("\n".join(section))
    text = (
        "⚠️ <i>Прогнозы не являются инвестиционной рекомендацией.</i>\n\n"
        + "\n\n━━━━━━━━━━━━━━━\n\n".join(parts)
    )
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i : i + 4000], parse_mode="HTML", disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)


async def cmd_ticker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Укажите тикер: /ticker AAPL")
        return
    t = ctx.args[0].upper()
    await update.message.reply_text(f"⏳ Загружаю {t}...")
    parts = []
    q = get_quote(t)
    parts.append(format_quote(q) if q else f"❌ {t}: данные недоступны")
    f = get_forecast(t)
    if f:
        parts.append(format_forecast(f))
    items = get_news(t)
    parts.append(format_news(t, items))
    await update.message.reply_text("\n\n".join(parts), parse_mode="HTML", disable_web_page_preview=True)


async def cmd_subscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    subscribers.add(update.effective_chat.id)
    await update.message.reply_text(f"✅ Подписка оформлена! Рассылка каждые {NEWS_INTERVAL_HOURS}ч.")


async def cmd_unsubscribe(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    subscribers.discard(update.effective_chat.id)
    await update.message.reply_text("❌ Подписка отменена.")


async def scheduled_broadcast(app: Application):
    if not subscribers:
        return
    parts = []
    for t in TICKERS:
        section = []
        q = get_quote(t)
        if q:
            section.append(format_quote(q))
        f = get_forecast(t)
        if f:
            section.append(format_forecast(f))
        items = get_news(t)
        if items:
            section.append(format_news(t, items[:3]))
        parts.append("\n".join(section))

    text = "📊 <b>Автоматический отчёт</b>\n\n" + "\n\n━━━━━━━━━━━━━━━\n\n".join(parts)

    for chat_id in list(subscribers):
        try:
            if len(text) > 4000:
                for i in range(0, len(text), 4000):
                    await app.bot.send_message(chat_id, text[i : i + 4000], parse_mode="HTML", disable_web_page_preview=True)
            else:
                await app.bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            log.warning("Failed to send to %s: %s", chat_id, e)
            subscribers.discard(chat_id)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("prices", cmd_prices))
    app.add_handler(CommandHandler("forecast", cmd_forecast))
    app.add_handler(CommandHandler("news", cmd_news))
    app.add_handler(CommandHandler("all", cmd_all))
    app.add_handler(CommandHandler("ticker", cmd_ticker))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))

    async def post_init(application):
        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduled_broadcast, "interval", hours=NEWS_INTERVAL_HOURS, args=[application])
        scheduler.start()

    app.post_init = post_init

    log.info("Bot started. Tracking: %s", ", ".join(TICKERS))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
