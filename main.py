import os
import sys
import time
import shutil

from dotenv import load_dotenv

import Data_Formatting.html_formatter_individual as fm
import Data_Retrieval.eodhd_apis as eodhd
import Data_Retrieval.shared_functions as helper
import Data_Retrieval.yf_apis as yf_apis

load_dotenv()
EODHD_API_TOKEN = os.getenv("eodhd_api_token")


def validate_common_stock_tickers(company_json: dict, ticker: str) -> bool:
    if not company_json:
        print(f"Could not find company data for {ticker}")
        return False

    return True


def save_formatted_individual_finances_by_ticker(
    region: str, exchange: str, ticker: str, **kwargs
) -> None:
    tickers = eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, exchange)
    ticker = ticker.upper().strip()
    exchange = exchange.upper().strip()
    region = region.upper().strip()
    for i, company in enumerate(tickers):
        if company["Code"] == ticker:
            if not helper.validate_ticker(company, exchange):
                continue
            
            ticker = company["Code"]
            company_json = eodhd.get_fundamental_data(EODHD_API_TOKEN, region, ticker)
            if not validate_common_stock_tickers(company_json, ticker):
                return

            company_price = kwargs.get("price", None)
            if not company_price:
                company_price = yf_apis.retrieve_stock_price(exchange, ticker)

            fm.print_individual_finances(company_json, current_price=company_price)
            return

    print(f"Could not find ticker information for {ticker}")


def save_formatted_individual_finances_by_exchange(
    region: str,
    exchange: str,
    max_tickers: (int, None) = None,
    min_mkt_cap_mil: (int, None) = None,
    sleep: bool = None,
    use_eodhd_apis: bool = False,
) -> None:
    tickers = eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, region)
    exchange = exchange.upper().strip()
    region = region.upper().strip()

    company_count = 0
    if tickers:
        for company in tickers:
            if max_tickers is not None and company_count >= max_tickers:
                break

            if not helper.validate_ticker(company, exchange):
                continue

            ticker = company["Code"]
            if use_eodhd_apis:
                company_price = eodhd.get_stock_close_price(EODHD_API_TOKEN, region, ticker)
            else:
                company_price = yf_apis.retrieve_stock_price(exchange, ticker)

            if sleep:
                time.sleep(1)
            if not company_price:
                print(f"Can't find the price for {ticker}")
                continue

            company_json = eodhd.get_fundamental_data(EODHD_API_TOKEN, region, ticker)
            if not validate_common_stock_tickers(company_json, ticker):
                continue

            if min_mkt_cap_mil and helper.calculate_market_cap(company_json, company_price) < min_mkt_cap_mil:
                continue

            fm.print_individual_finances(company_json, current_price=company_price)
            company_count += 1
    else:
        print(f"Could not find any ticker on exchange {exchange}")


def remove_fundamentals_data(region: str, exchange: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(script_dir, f"Data_Output/Fundamentals/{exchange.upper()}")
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            # If it's a file, remove it
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
            # If it's a directory, remove it and all its contents
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")


def main():
    if len(sys.argv) > 1:
        run_type = sys.argv[1]

        if run_type == "nightly":
            region = sys.argv[2]
            exchange = sys.argv[3]
            min_mkt_cap_mil = int(sys.argv[4])
            use_eodhd_apis = bool(sys.argv[5])
            save_formatted_individual_finances_by_exchange(region, exchange, min_mkt_cap_mil=min_mkt_cap_mil, sleep=True, use_eodhd_apis=use_eodhd_apis)
        
        if run_type == "remove_fundamentals":
            region = sys.argv[2]
            exchange = sys.argv[3]
            remove_fundamentals_data(region, exchange)

    else:
        region = "au"
        exchange = "au"
        ticker = "cda"

        save_formatted_individual_finances_by_ticker(region, exchange, ticker)

        # fm.calculate_industry_average(EODHD_API_TOKEN, exchange, industry='Industrials')
        # save_formatted_individual_finances_by_exchange(region, exchange, min_mkt_cap_mil=100)

if __name__ == "__main__":
    main()
