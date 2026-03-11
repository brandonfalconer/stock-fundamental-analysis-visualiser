import os
import sys
import time
import shutil

from typing import List

from dotenv import load_dotenv

import Data_Formatting.html_formatter_individual as fm
import Data_Retrieval.eodhd_apis as eodhd
import Data_Retrieval.shared_functions as helper
import Data_Retrieval.yf_apis as yf_apis

load_dotenv()
EODHD_API_TOKEN = os.getenv("eodhd_api_token")


def save_formatted_individual_finances_by_ticker(
    region: str, exchange: str, ticker: str, force_update: bool = False, **kwargs
) -> None:
    tickers = kwargs.get("tickers", None)
    if not tickers:
        tickers = eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, exchange)
        if not tickers:
            print(f"Failed to retrieve tickers: {exchange}")
            return

    ticker = ticker.upper().strip()
    exchange = exchange.upper().strip()
    region = region.upper().strip()
    for company in tickers:
        if company["Code"] == ticker:
            if not helper.validate_ticker(company, exchange):
                continue

            ticker = company["Code"]
            company_json = eodhd.get_fundamental_data(EODHD_API_TOKEN, region, ticker, override=force_update)
            if not helper.validate_common_stock_tickers(company_json, ticker):
                return

            company_price = kwargs.get("price", None)
            if not company_price:
                company_price = yf_apis.retrieve_stock_price(exchange, ticker)

            fm.print_individual_finances(company_json, current_price=company_price)
            return

    print(f"Could not find ticker information for {ticker}")


def save_formatted_individual_finances_by_list_tickers(region: str, exchange: str, tickers: List[str]):
    tickers_on_exchange = eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, exchange)
    for ticker in tickers:
        time.sleep(3.0)
        save_formatted_individual_finances_by_ticker(region, exchange, ticker, True, tickers=tickers_on_exchange)


def save_formatted_individual_finances_by_exchange(
    region: str,
    exchange: str,
    max_tickers: int | None = None,
    min_mkt_cap_mil: int | None = None,
    sleep: bool = False,
    use_eodhd_apis: bool = False,
    override: bool = False, 
) -> None:
    exchange = exchange.upper().strip()
    region = region.upper().strip()
    tickers = eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, region)

    company_count = 0
    if tickers:
        for company in tickers:
            if max_tickers is not None and company_count >= max_tickers:
                break

            if not helper.validate_ticker(company, exchange):
                continue

            ticker = company["Code"]
            company_json = eodhd.get_fundamental_data(EODHD_API_TOKEN, region, ticker, override=override)
            if not helper.validate_common_stock_tickers(company_json, ticker):
                continue

            if use_eodhd_apis:
                print('eodhd')
                company_price = eodhd.get_stock_close_price(
                    EODHD_API_TOKEN, region, ticker
                )
            else:
                if sleep:
                    time.sleep(3.0)
                company_price = yf_apis.retrieve_stock_price(exchange, ticker)

            if not company_price:
                print(f"Can't find the price for {ticker}")
                continue

            if (
                min_mkt_cap_mil
                and helper.calculate_market_cap(company_json, company_price)
                < min_mkt_cap_mil
            ):
                continue

            fm.print_individual_finances(company_json, current_price=company_price)
            company_count += 1
    else:
        print(f"Could not find any ticker on exchange {exchange}")


def remove_fundamentals_data(region: str, exchange: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(
        script_dir, f"Data_Output/Fundamentals/{exchange.upper()}"
    )
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


def update_ticker_data(exchange: str):
    eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, exchange, True)


def initial_setup():
    region = "au"
    exchange = "au"
    min_mkt_cap_mil = 0
    use_eodhd_apis = True
    sleep = not use_eodhd_apis

    save_formatted_individual_finances_by_exchange(
        region,
        exchange,
        min_mkt_cap_mil=min_mkt_cap_mil,
        sleep=sleep,
        use_eodhd_apis=use_eodhd_apis,
    )


def main():
    if len(sys.argv) > 1:
        run_type = sys.argv[1]

        if run_type == "nightly":
            region = sys.argv[2]
            exchange = sys.argv[3]
            min_mkt_cap_mil = int(sys.argv[4])
            use_eodhd_apis = bool(int(sys.argv[5]))

            sleep = not use_eodhd_apis
            save_formatted_individual_finances_by_exchange(
                region,
                exchange,
                min_mkt_cap_mil=min_mkt_cap_mil,
                sleep=sleep,
                use_eodhd_apis=use_eodhd_apis,
            )

        if run_type == "remove_fundamentals":
            region = sys.argv[2]
            exchange = sys.argv[3]
            remove_fundamentals_data(region, exchange)
        
        if run_type == "update_tickers":
            exchange = sys.argv[2].upper()
            update_ticker_data(exchange)

    else:
        save_formatted_individual_finances_by_ticker("au", "au", "ang", use_eodhd_apis=False, price=0.19)

        # Print formatted individual finances from a list of tickers
        # tickers = ["kar", "ehl", "cvl", "whc", "yal", "kau", "mlx", "pnc", "btr", "wgx", "bsa", "tre", "ami", "mce", "cvn", "jms", "pdn", "rsg", "fnd", "hum", "azy", "erm", "min", "mlg", "pgc", "ezl", "syl", "hmc"]
        # save_formatted_individual_finances_by_list_tickers ("au", "au", tickers)

        ### Examples
        # Print formatted individual finances by exchange
        # region = "au"
        # exchange = "au"
        # save_formatted_individual_finances_by_exchange(region, exchange, use_eodhd_apis=False)
        return


if __name__ == "__main__":
    main()
