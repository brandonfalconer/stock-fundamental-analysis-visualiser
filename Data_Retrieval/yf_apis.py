import yfinance as yf


def retrieve_stock_price(exchange: str, ticker: str) -> (float, None):
    if exchange.lower() == "au":
        ticker = ticker + ".AX"

    cda = yf.Ticker(ticker)
    price_history = cda.history(period="1d")
    if not price_history["Close"].empty:
        company_price = price_history["Close"].iloc[0]
    else:
        return None

    return company_price
