import yfinance as yf
import pandas as pd
import ta
from deep_translator import GoogleTranslator

_translator = GoogleTranslator(source="en", target="ru")


def translate(text: str) -> str:
    try:
        return _translator.translate(text)
    except Exception:
        return text


def get_quote(ticker: str) -> dict | None:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist = t.history(period="2d")
        if hist.empty:
            return None
        last = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else last
        change = last["Close"] - prev["Close"]
        change_pct = (change / prev["Close"]) * 100
        return {
            "ticker": ticker,
            "price": round(last["Close"], 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": int(last["Volume"]),
            "high": round(last["High"], 2),
            "low": round(last["Low"], 2),
        }
    except Exception:
        return None


def get_forecast(ticker: str) -> dict | None:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="3mo")
        if len(hist) < 20:
            return None

        close = hist["Close"]
        rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]
        macd_ind = ta.trend.MACD(close)
        macd = macd_ind.macd().iloc[-1]
        macd_signal = macd_ind.macd_signal().iloc[-1]
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        price = close.iloc[-1]

        signals = []
        if rsi < 30:
            signals.append("RSI перепродан — возможен отскок вверх")
        elif rsi > 70:
            signals.append("RSI перекуплен — возможна коррекция")
        else:
            signals.append(f"RSI нейтральный ({rsi:.0f})")

        if macd > macd_signal:
            signals.append("MACD — бычий сигнал")
        else:
            signals.append("MACD — медвежий сигнал")

        if price > sma_20:
            signals.append(f"Цена выше SMA20 ({sma_20:.2f})")
        else:
            signals.append(f"Цена ниже SMA20 ({sma_20:.2f})")

        if sma_50:
            if sma_20 > sma_50:
                signals.append("SMA20 > SMA50 — восходящий тренд")
            else:
                signals.append("SMA20 < SMA50 — нисходящий тренд")

        bullish = sum(1 for s in signals if any(w in s for w in ["бычий", "отскок", "выше", "восходящий"]))
        bearish = sum(1 for s in signals if any(w in s for w in ["медвежий", "коррекция", "ниже", "нисходящий"]))

        if bullish > bearish:
            outlook = "📈 Преимущественно БЫЧИЙ"
        elif bearish > bullish:
            outlook = "📉 Преимущественно МЕДВЕЖИЙ"
        else:
            outlook = "➡️ НЕЙТРАЛЬНЫЙ"

        return {
            "ticker": ticker,
            "rsi": round(rsi, 1),
            "macd": round(macd, 3),
            "macd_signal": round(macd_signal, 3),
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2) if sma_50 else None,
            "signals": signals,
            "outlook": outlook,
        }
    except Exception:
        return None


def get_news(ticker: str) -> list[dict]:
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        result = []
        for item in news[:5]:
            content = item.get("content", {})
            title_en = content.get("title", item.get("title", "N/A"))
            result.append({
                "title": translate(title_en),
                "title_en": title_en,
                "link": content.get("canonicalUrl", {}).get("url", item.get("link", "")),
                "publisher": content.get("provider", {}).get("displayName", ""),
            })
        return result
    except Exception:
        return []
