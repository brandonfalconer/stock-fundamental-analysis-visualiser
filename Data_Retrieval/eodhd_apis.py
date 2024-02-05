from Data_Retrieval.shared_functions import save_response_to_file
from datetime import datetime


def get_exchange_data(api_token: str) -> dict:
	url = f'https://eodhd.com/api/exchanges-list/?api_token={api_token}&fmt=json'
	file_path = "Data/exchanges.json"
	return save_response_to_file(url, file_path)


def get_tickers_by_exchange(api_token: str, exchange_code: str) -> dict:
	url = f"https://eodhd.com/api/exchange-symbol-list/{exchange_code}?api_token={api_token}&fmt=json"
	file_path = f"Data/tickers_{exchange_code}.json"
	return save_response_to_file(url, file_path)


def get_end_of_day_data(api_token: str, exchange_code: str, ticker_code: str) -> dict:
	url = f"https://eodhd.com/api/eod/{ticker_code}.{exchange_code}?api_token={api_token}&fmt=json"
	file_path = f"Data/EOD/Date/{exchange_code}/{datetime.now().day}.{datetime.now().month}.{datetime.now().year}/{ticker_code}.json"
	return save_response_to_file(url, file_path)


def get_real_time_data(api_token: str, exchange_code: str, ticker_code: str) -> dict:
	url = f"https://eodhd.com/api/real-time/{ticker_code}.{exchange_code}?api_token={api_token}&fmt=json"
	file_path = f"Data/Real_Time/{exchange_code}/{datetime.now().day}.{datetime.now().month}.{datetime.now().year}/{ticker_code}.json"
	return save_response_to_file(url, file_path)


def get_fundamental_data(api_token: str, exchange_code: str, ticker_code: str) -> dict:
	url = f"https://eodhd.com/api/fundamentals/{ticker_code}.{exchange_code}?api_token={api_token}&fmt=json"
	file_path = f"Data/Fundamentals/{exchange_code}/{datetime.now().month}.{datetime.now().year}/{ticker_code}.json"
	return save_response_to_file(url, file_path)


def get_stock_close_price(api_token: str, exchange_code: str, ticker_code: str) -> float:
	json = get_real_time_data(api_token, exchange_code, ticker_code)
	try:
		close_price = float(json['close'])
	except ValueError:
		close_price = None

	return close_price


def get_exchange_common_stock_count(api_token: str, exchange_code: str) -> int:
	json = get_tickers_by_exchange(api_token, exchange_code)
	common_stock_au = [stock for stock in json if
					   stock['Type'] == 'Common Stock' and stock['Exchange'] == exchange_code]
	return len(common_stock_au)
