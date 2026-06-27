import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8884952156:AAGZ3-HhDIW9Bpr-E9hM1tSaLoQXcXzmde8")

TICKERS = ["SPY", "TSLA", "MSFT", "NVDA", "SPCX", "META"]

# Интервал автоматической рассылки (в часах)
NEWS_INTERVAL_HOURS = 4

# Часовой пояс для расписания
TIMEZONE = "US/Eastern"
