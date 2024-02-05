import os
from dotenv import load_dotenv

import Data_Formatting.html_formatter_individual as fm
import Data_Retrieval.shared_functions as helper
import Data_Retrieval.eodhd_apis as eodhd

load_dotenv()
EODHD_API_TOKEN = os.getenv('eodhd_api_token')


def validate_common_stock_tickers(company_json: dict, ticker: str) -> bool:
	if not company_json:
		print(f'Could not find company data for {ticker}')
		return False

	return True


def save_formatted_individual_finances_by_ticker(region: str, exchange: str, ticker: str) -> None:
	tickers = eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, exchange)
	for i, company in enumerate(tickers):
		if company['Code'] == ticker:
			ticker = helper.validate_ticker(company, exchange)

			company_json = eodhd.get_fundamental_data(EODHD_API_TOKEN, region, ticker)
			if not validate_common_stock_tickers(company_json, ticker):
				return
			company_price = eodhd.get_stock_close_price(EODHD_API_TOKEN, region, ticker)
			fm.print_individual_finances(company_json, current_price=company_price)
			return

	print(f'Could not find ticker information for {ticker}')


def save_formatted_individual_finances_by_exchange(region: str, exchange: str, max_tickers: (int, None) = None) -> None:
	tickers = eodhd.get_tickers_by_exchange(EODHD_API_TOKEN, region)
	company_count = 0
	for company in tickers:
		if max_tickers is not None and company_count >= max_tickers:
			break

		ticker = helper.validate_ticker(company, exchange)
		if not ticker:
			continue

		company_price = eodhd.get_stock_close_price(EODHD_API_TOKEN, region, ticker)
		if not company_price:
			print(f"Can't find the price for {ticker}")
			continue

		company_json = eodhd.get_fundamental_data(EODHD_API_TOKEN, region, ticker)
		if not validate_common_stock_tickers(company_json, ticker):
			continue

		fm.print_individual_finances(company_json, current_price=company_price)
		company_count += 1


def show_formatted_individual_finances(exchange: str, ticker: str):
	return


def main():
	region = 'US'
	exchange = 'NASDAQ'
	ticker = 'GTX'

	# save_formatted_individual_finances_by_ticker(region, exchange, ticker)

	# fm.calculate_industry_average(EODHD_API_TOKEN, exchange, industry='Industrials')
	# eodhd.get_exchange_data(EODHD_API_TOKEN)
	# print(eodhd.get_stock_close_price(EODHD_API_TOKEN, region, 'aapl'))

	save_formatted_individual_finances_by_exchange(region, exchange)


if __name__ == "__main__":
	main()
