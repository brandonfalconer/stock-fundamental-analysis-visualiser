import os
from dotenv import load_dotenv

import Data_Retrieval.html_formatter as fm
import Data_Retrieval.shared_functions as helper
import Data_Retrieval.eodhd_apis as eodhd

load_dotenv()


def main():

	#eodhd.get_real_time_data(api_token, "AU", "CDA")
	#eodhd.get_fundamental_data(api_token, "AU", "CDA")
	#print(eodhd.get_exchange_common_stock_count(api_token, 'AU'))

	#fm.retrieve_basic_fundamental_data(json)
	#fm.retrieve_holder_information(json)

	# fm.format_asx_listed_company_basic_data()

	relative_path = "Data\Fundamentals\\1.24\CDA.AU.json"
	json = helper.return_json_data(relative_path)
	EODHD_API_TOKEN = os.getenv('eodhd_api_token')
	fm.print_individual_finances(json, current_price=eodhd.get_stock_close_price(EODHD_API_TOKEN, 'AU', 'CDA'))


if __name__ == "__main__":
	main()
