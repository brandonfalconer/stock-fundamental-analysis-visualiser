import os
from dotenv import load_dotenv

import Data_Formatting.html_formatter_individual as fm
import Data_Retrieval.shared_functions as helper
import Data_Retrieval.eodhd_apis as eodhd

load_dotenv()
EODHD_API_TOKEN = os.getenv('eodhd_api_token')


def save_formatted_individual_finances_by_ticker(exchange: str, ticker: str):
	ticker = helper.validate_ticker(ticker)

	company_json = eodhd.get_fundamental_data(EODHD_API_TOKEN, exchange, ticker)
	company_price = eodhd.get_stock_close_price(EODHD_API_TOKEN, exchange, ticker)
	fm.print_individual_finances(company_json, current_price=company_price)


def save_formatted_individual_finances_by_exchange(exchange):
	asx_tickers = eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, exchange)
	for company in asx_tickers:
		code = company['Code']
		ticker = helper.validate_ticker(code)
		if not ticker:
			continue
		company_json = eodhd.get_fundamental_data(EODHD_API_TOKEN, exchange, ticker)

		if not company_json:
			print(f'Could not find company data for {ticker}')
			continue

		if company_json['General']['Type'] != "Common Stock":
			print(f'{ticker} is not a common stock')
			continue

		company_price = eodhd.get_stock_close_price(EODHD_API_TOKEN, exchange, ticker)

		if not company_price or str(company_price) == "NA":
			print(f"Can't find the price for {ticker}")
			continue

		fm.print_individual_finances(company_json, current_price=company_price)


def main():
	exchange = 'AU'
	ticker = 'ADC'

	save_formatted_individual_finances_by_ticker(exchange, ticker)

	save_formatted_individual_finances_by_exchange(exchange)


if __name__ == "__main__":
	main()
