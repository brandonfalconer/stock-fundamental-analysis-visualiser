import yfinance as yf


def retrieve_stock_price(exchange: str, ticker: str) -> float | None:
    if exchange.lower() == "au":
        ticker = ticker + ".AX"

    if exchange.lower() == "to":
        ticker = ticker + ".TO"

    if exchange.lower() == "v":
        ticker = ticker + ".V"
    
    if exchange.lower() == "lse":
        ticker = ticker + ".L"

    if exchange.lower() == "jse":
        ticker = ticker + ".JO"

    cda = yf.Ticker(ticker)
    try:
        price_history = cda.history(period="1d")
        if not price_history["Close"].empty:
            company_price = price_history["Close"].iloc[0]
        else:
            return None
    except yf.exceptions.YFRateLimitError:
        print("Rate limited, continuing...")
        company_price = None

    # Basic conversions
    # LSE shows price in pence, not pounds
    if exchange.lower() == "lse":
        company_price /= 100

    return company_price
