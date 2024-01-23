import json

import pandas as pd
from bokeh.io import show, save, output_file
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, DataTable, TableColumn, HTMLTemplateFormatter
from bokeh.models import Div

from Data_Retrieval.shared_functions import (convert_to_numeric_divide_by_one_million, return_mean_std_industry_valuations,
											 format_rows, format_cell, convert_none_to_zero, handle_divide_by_zero)
from Data_Retrieval.web_scraper import get_all_asx_companies
from Data_Retrieval.constant_data_structures import (financials_row_mapping, income_statement_order,
													 cash_flow_statement_order, balance_sheet_order)
from Data_Retrieval.html_styling import INDIVIDUAL_COMPANY_TABLE_STYLE


def format_asx_listed_company_basic_data():
	selected_information, all_stock_df = get_all_asx_companies()

	# Define a custom HTMLTemplateFormatter for the 'change' column
	change_template = """
		<div style="background:
			<% if (value > 0) { %> rgba(0, 230, 0, <%= value/5 %>) <% }
			else if (value < 0) { %> rgba(230, 0, 0, <%= -value/5 %>) <% } 
			else { %> rgba(255, 255, 255, 0.5) <% } %>;
			color: black;
			font-weight: bold;">
			<%= value %>
		</div>
	"""

	one_yr_change_template = """
		<div style="background:
			<% if (value > 0) { %> rgba(0, 230, 0, <%= value/100 %>) <% }
			else if (value < 0) { %> rgba(230, 0, 0, <%= -value/100 %>) <% } 
			else { %> rgba(255, 255, 255, 0.5) <% } %>;
			color: black;
			font-weight: bold;">
			<%= value %>
			</div>
		"""

	# Add the formatted 'change' column to the columns list
	columns = []
	for col in selected_information:
		if col == 'change_percent':
			formatter = HTMLTemplateFormatter(template=change_template)
			columns.append(TableColumn(field=col, title=col, formatter=formatter))
		elif col == '1yr_percent_change':
			formatter = HTMLTemplateFormatter(template=one_yr_change_template)
			columns.append(TableColumn(field=col, title=col, formatter=formatter))
		else:
			columns.append(TableColumn(field=col, title=col))

	data_table = DataTable(source=ColumnDataSource(all_stock_df), columns=columns, width=1900, height=900)
	show(data_table)


def retrieve_holder_information(json_data: dict):
	print(json.dumps(json_data['Holders'], indent=4))
	for key, value in json_data['Holders'].items():
		print(f'{key}: {value}')


def create_company_summary(json_data: dict):
	columns = [
		"Code", "Type", "Name", "Exchange", "CountryName", "PrimaryTicker",
		"FiscalYearEnd", "IPODate", "InternationalDomestic", "Sector", "Industry", "Description", "FullTimeEmployees",
		"UpdatedAt",
	]
	df = pd.DataFrame([json_data['General']], columns=columns)
	return df


def create_financial_statement_df(json_data: dict, statement: str, row_order: list) -> pd.DataFrame:
	summarised_flattened_data = []
	for i, (date, details) in enumerate(json_data['Financials'][statement]['yearly'].items()):
		summarised_entry = {"date": details["date"]}
		summarised_entry.update(details)
		summarised_flattened_data.append(summarised_entry)

		# Use previous 20 years
		if i == 19:
			break

	df = pd.DataFrame(summarised_flattened_data)
	df.set_index("date", inplace=True)
	df = df.T.iloc[:, ::-1]

	numeric_columns = df.columns.difference(["date"])
	df[numeric_columns] = df[numeric_columns].applymap(convert_to_numeric_divide_by_one_million)
	df = df.reindex(row_order)
	df = df.dropna(how='all')
	df = df.fillna('')
	df.rename(index=financials_row_mapping, inplace=True)

	format_rows(df, [], large_positive=True)
	return df


def create_valuation_df(json_data: dict, valuation_df: pd.DataFrame, current_price: int) -> pd.DataFrame:
	# Earnings
	revenues = valuation_df.loc['totalRevenue'].iloc[-1]
	earnings = valuation_df.loc['netIncome'].iloc[-1]
	shares_outstanding = valuation_df.loc['commonStockSharesOutstanding'].iloc[-1]
	trailing_eps = earnings / shares_outstanding
	market_cap = shares_outstanding * current_price
	total_cash = valuation_df.loc['cash'].iloc[-1]
	total_debt = valuation_df.loc['shortLongTermDebtTotal'].iloc[-1]
	enterprise_value = market_cap + total_debt - total_cash
	ebitda = valuation_df.loc['ebitda'].iloc[-1]
	ev_ebitda = enterprise_value / ebitda
	trailing_price_earnings = current_price / trailing_eps
	forward_eps = json_data['Highlights']['EPSEstimateNextYear']
	forward_price_earnings = current_price / forward_eps
	price_sales = market_cap / revenues

	# Balance Sheet
	current_assets = valuation_df.loc['totalCurrentAssets'].iloc[-1]
	total_assets = valuation_df.loc['totalAssets'].iloc[-1]
	current_debt = valuation_df.loc['shortTermDebt'].iloc[-1]
	# current_liabilities = valuation_df.loc['totalCurrentLiabilities'].iloc[-1]
	total_liabilities = valuation_df.loc['totalLiab'].iloc[-1]
	book_value = total_assets - total_liabilities
	tangible_assets = total_assets - valuation_df.loc['intangibleAssets'].iloc[-1] - valuation_df.loc['goodWill'].iloc[-1]
	tangible_book = tangible_assets - total_liabilities
	price_tangible_book = market_cap / tangible_book
	price_book = handle_divide_by_zero(market_cap, book_value)
	price_cash = market_cap / total_cash
	price_net_cash = market_cap / (total_cash - total_debt)
	preferred_stock_equity = valuation_df.loc['preferredStockTotalEquity'].iloc[-1]
	price_net_net = market_cap / (
			current_assets - (total_liabilities + preferred_stock_equity if preferred_stock_equity is not None else 0))
	debt_to_equity = total_liabilities / valuation_df.loc['totalStockholderEquity'].iloc[-1]

	# Cash Flow
	price_operating_cash_flow = market_cap / valuation_df.loc['totalCashFromOperatingActivities'].iloc[-1]
	price_free_cash_flow = market_cap / valuation_df.loc['freeCashFlow'].iloc[-1]
	price_net_cash_flow = market_cap / valuation_df.loc['changeInCash'].iloc[-1]
	dividend_per_share = json_data['Highlights']['DividendShare']
	dividend_yield = json_data['Highlights']['DividendYield']
	price_dividend = market_cap / (dividend_per_share * shares_outstanding)

	interest_coverage = valuation_df.loc['ebit'].iloc[-1] / valuation_df.loc['interestExpense'].iloc[-1]
	'''
	DSCR =  Net Operating Income / Debt Service
	where:
	
	Net Operating Income = Adj. EBITDA = (Gross Operating Revenue) − (Operating Expenses)
	Debt Service = (Principal Repayment) + (Interest Payments) + (Lease Payments)
	'''
	debt_service_coverage = valuation_df.loc['operatingIncome'].iloc[-1] / current_debt
	asset_coverage_ratio = (tangible_assets - current_debt) / total_debt

	df_dict = {
		'Price': current_price,
		'MktCap': market_cap,
		'Enterprise Value': enterprise_value,
		'Revenue': revenues,
		'Dividend Yield': str(dividend_yield * 100) + '%',
		'P/S': price_sales,
		'EV/EBITDA': ev_ebitda,
		'P/TB': price_tangible_book,
		'P/B': price_book,
		'Debt/Equity': debt_to_equity,
		'Trailing P/E': trailing_price_earnings,
		'Forward P/E': forward_price_earnings,
		'P/CFO': price_operating_cash_flow,
		'P/FCF': price_free_cash_flow,
		'P/NCF': price_net_cash_flow,
		'P/Div': price_dividend,
		'P/Cash': price_cash,
		'P/NCash': price_net_cash,
		'P/NN': price_net_net,
		'Interest Coverage': interest_coverage,
		'Debt Service Cov': debt_service_coverage,
		'Asset Cov': asset_coverage_ratio,
	}
	df_dict = {key: round(value, 2) if isinstance(value, (float, int)) else value for key, value in df_dict.items()}
	result_df = pd.DataFrame.from_dict([df_dict])

	# Copy updated information into valuation tracker to calculate industry mean and std
	exchange = json_data['General']['Exchange']
	code = json_data['General']['Code']
	industry = json_data['General']['Sector']

	update_dict = {'Code': code}
	ordered_dict = {**update_dict, **df_dict}

	file_path = f"Data/Fundamentals/Valuation/{exchange}/{industry}.json"
	try:
		with open(file_path, 'r') as json_file:
			json_data = json.load(json_file)
			existing_entry = next((entry for entry in json_data['Companies'] if entry['Code'] == code), None)
			if existing_entry:
				# Update the existing entry
				existing_entry.update(ordered_dict)
			else:
				# Append the new entry
				json_data['Companies'].append(ordered_dict)

		with open(file_path, 'w') as json_file:
			json.dump(json_data, json_file, indent=2)

	except FileNotFoundError:
		print(f"File not found: {file_path}")

	industry_average_valuation_dict = return_mean_std_industry_valuations(exchange, industry)
	large_positive = ['Revenue', 'Dividend Yield']

	for col, mean in industry_average_valuation_dict['Mean'].items():
		if col in large_positive:
			format_cell(result_df, col, mean, industry_average_valuation_dict['StdDev'][col])
		else:
			format_cell(result_df, col, mean, industry_average_valuation_dict['StdDev'][col], False)

	return result_df


def print_individual_finances(json_data: dict, current_price):
	summarised_flattened_data = []

	for i, (date, details) in enumerate(json_data['Financials']['Income_Statement']['yearly'].items()):
		summarised_entry = {"date": details["date"]}
		summarised_entry.update(details)

		# Add details from other financial statements for the corresponding date
		for statement_type in ['Income_Statement', 'Cash_Flow', 'Balance_Sheet']:
			if date in json_data['Financials'][statement_type]['yearly']:
				summarised_entry.update(json_data['Financials'][statement_type]['yearly'][date])

		summarised_flattened_data.append(summarised_entry)

		# Use previous 20 years
		if i == 19:
			break

	hl_df = pd.DataFrame(summarised_flattened_data)

	# Set the "date" column as the index
	hl_df.set_index("date", inplace=True)

	# Transpose and invert the DataFrame
	hl_df = hl_df.T.iloc[:, ::-1]

	# Convert strings to numbers and divide by 1 million
	numeric_columns = hl_df.columns.difference(["date"])
	hl_df[numeric_columns] = hl_df[numeric_columns].applymap(convert_to_numeric_divide_by_one_million)

	# Create valuation df based off highlights df
	valuation_df = create_valuation_df(json_data, hl_df, current_price)

	# Define the new rows by performing divisions
	# highlights_df.loc['Avg Revenue 3yr'] = highlights_df.loc['totalRevenue'].rolling(window=3, min_periods=1).mean().round(2)

	hl_df.loc['Revenue Increase'] = hl_df.loc['totalRevenue'].pct_change()
	hl_df.loc['Revenue Increase'].iloc[0] = 0

	# Calculate rolling percentage increase over the past 3 cells
	hl_df.loc['Rolling Revenue Increase 3yr'] = hl_df.loc['totalRevenue'].pct_change(periods=3) / 3
	hl_df.loc['Rolling Revenue Increase 3yr'].iloc[:3] = 0

	hl_df.loc['Gross Margin'] = hl_df.loc['grossProfit'] / hl_df.loc['totalRevenue']
	hl_df.loc['EBITDA Margin'] = hl_df.loc['ebitda'] / hl_df.loc['totalRevenue']
	hl_df.loc['Net Inc Margin'] = hl_df.loc['netIncome'] / hl_df.loc['totalRevenue']
	hl_df.loc['CFO Margin'] = hl_df.loc['totalCashFromOperatingActivities'] / hl_df.loc['totalRevenue']
	hl_df.loc['FCF Margin'] = hl_df.loc['freeCashFlow'] / hl_df.loc['totalRevenue']
	hl_df.loc['NCF Margin'] = hl_df.loc['changeInCash'] / hl_df.loc['totalRevenue']

	hl_df.loc['Common EPS'] = hl_df.loc['netIncomeApplicableToCommonShares'] / hl_df.loc['commonStockSharesOutstanding']
	hl_df.loc['EBITDA /sh'] = hl_df.loc['ebitda'] / hl_df.loc['commonStockSharesOutstanding']
	hl_df.loc['CFO /sh'] = hl_df.loc['totalCashFromOperatingActivities'] / hl_df.loc['commonStockSharesOutstanding']
	hl_df.loc['FCF /sh'] = hl_df.loc['freeCashFlow'] / hl_df.loc['commonStockSharesOutstanding']
	hl_df.loc['NCF /sh'] = hl_df.loc['changeInCash'] / hl_df.loc['commonStockSharesOutstanding']
	hl_df.loc['RND % Revenue'] = hl_df.loc['researchDevelopment'] / hl_df.loc['totalRevenue']
	hl_df.loc['Selling Marketing % Revenue'] = hl_df.loc['sellingAndMarketingExpenses'] / hl_df.loc['totalRevenue']
	hl_df.loc['Selling General % Revenue'] = hl_df.loc['sellingGeneralAdministrative'] / hl_df.loc['totalRevenue']

	book_value = hl_df.loc['totalAssets'] - hl_df.loc['totalLiab']
	tangible_book = book_value - hl_df.loc['intangibleAssets']
	hl_df.loc['Assets /sh'] = hl_df.loc['totalAssets'] / hl_df.loc['commonStockSharesOutstanding']
	hl_df.loc['Book /sh'] = book_value / hl_df.loc['commonStockSharesOutstanding']
	hl_df.loc['Tang Book /sh'] = (tangible_book / hl_df.loc['commonStockSharesOutstanding'])

	# Calculate 'Debt Overhang' by subtracting 'cashAndShortTermInvestments' from the sum of the other two
	highlight_values = hl_df.loc[['shortTermDebt', 'nonCurrentLiabilitiesTotal', 'cashAndShortTermInvestments']]
	highlight_values = highlight_values.applymap(convert_none_to_zero)
	hl_df.loc['Debt Overhang'] = highlight_values.loc['shortTermDebt'] + highlight_values.loc[
		'nonCurrentLiabilitiesTotal'] - highlight_values.loc['cashAndShortTermInvestments']

	percent_columns = [
		'Revenue Increase', 'Rolling Revenue Increase 3yr', 'Gross Margin', 'EBITDA Margin', 'Net Inc Margin',
		'CFO Margin', 'FCF Margin', 'NCF Margin', 'RND % Revenue', 'Selling Marketing % Revenue',
		'Selling General % Revenue',
	]

	# Multiply selected rows by 100
	hl_df.loc[percent_columns] *= 100

	# Reorder the DataFrame columns
	new_order = [
		'commonStockSharesOutstanding', 'totalRevenue', 'Revenue Increase', 'Rolling Revenue Increase 3yr',
		'Gross Margin', 'EBITDA Margin', 'Net Inc Margin', 'CFO Margin', 'FCF Margin', 'NCF Margin', 'netIncome',
		'RND % Revenue', 'Selling Marketing % Revenue', 'Selling General % Revenue', 'Common EPS', 'EBITDA /sh',
		'CFO /sh', 'FCF /sh', 'NCF /sh', 'Assets /sh', 'Book /sh', 'Tang Book /sh', 'Debt Overhang'
	]
	hl_df = hl_df.reindex(new_order)

	# Rename the rows
	hl_df.rename(index=financials_row_mapping, inplace=True)
	hl_df = hl_df.fillna('')

	# List of rows to round and format as integers (greater than mean = green)
	large_positive_rows_to_format = ['Revenues', 'Revenue Increase', 'Rolling Revenue Increase 3yr', 'Gross Margin',
									 'EBITDA Margin', 'Net Inc Margin', 'CFO Margin', 'FCF Margin', 'NCF Margin',
									 'RND % Revenue', 'Common EPS', 'EBITDA /sh', 'CFO /sh', 'FCF /sh', 'NCF /sh',
									 'Net Income', 'Assets /sh', 'Book /sh', 'Tang Book /sh']

	hl_df.loc[large_positive_rows_to_format] = hl_df.loc[large_positive_rows_to_format]
	percent_columns_to_format = list(set(percent_columns) & set(large_positive_rows_to_format))
	remaining_columns = list(set(large_positive_rows_to_format) - set(percent_columns_to_format))

	format_rows(hl_df, percent_columns_to_format, large_positive=True, add_percentage=True)
	format_rows(hl_df, remaining_columns, large_positive=True)

	# List of rows to round and format as integers (greater than mean = green)
	large_negative_rows_to_format = ['Common Stock Shares Outstanding', 'Selling Marketing % Revenue',
									 'Selling General % Revenue', 'Debt Overhang']
	hl_df.loc[large_negative_rows_to_format] = hl_df.loc[large_negative_rows_to_format]

	percent_columns_to_format = list(set(percent_columns) & set(large_negative_rows_to_format))
	remaining_columns = list(set(large_negative_rows_to_format) - set(percent_columns_to_format))

	format_rows(hl_df, percent_columns_to_format, large_positive=False, add_percentage=True)
	format_rows(hl_df, remaining_columns, large_positive=False)

	# Access the DataFrames for each financial statement
	financial_statements = {
		'Balance_Sheet': balance_sheet_order,
		'Income_Statement': income_statement_order,
		'Cash_Flow': cash_flow_statement_order
	}

	financial_statement_dataframes = []
	for i, (key, order) in enumerate(financial_statements.items()):
		financial_statement_dataframes.append(create_financial_statement_df(json_data, key, order))

	summary_df = create_company_summary(json_data)
	summary_col_widths = { 'Description': 900 }

	# Combine all dataframes into one
	combined_html = summary_df.to_html(col_space=summary_col_widths, index=False, na_rep='N/A') + "<br>" + \
					"<h2>Company Valuation</h2>" + valuation_df.to_html(index=False, escape=False, na_rep='N/A') + "<br>" + \
					"<h2>Company Summary</h2>" + hl_df.to_html(classes='highlight-table', escape=False, na_rep='N/A')

	for df, title in zip(financial_statement_dataframes, financial_statements.keys()):
		classes = title + '-table'
		combined_html += f"<br><h2>{title.replace('_', ' ')}</h2>" + df.to_html(classes=classes, escape=False, na_rep='N/A')

	# Display the DataFrame in a Bokeh Div widget
	div_widget = Div(text=INDIVIDUAL_COMPANY_TABLE_STYLE + combined_html, width=1500, height=900)

	# Save the layout containing the Div widget
	stock_code = summary_df.iloc[0, 0]
	output_file("Data_Output/Output/Individual/AU/" + str(stock_code) + ".html")
	save(column(div_widget))
