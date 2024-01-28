import copy
import json
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from bokeh.io import save, output_file
from bokeh.layouts import column
from bokeh.models import Div

from Data_Formatting.css_styling import INDIVIDUAL_COMPANY_TABLE_STYLE
from Data_Retrieval.constant_data_structures import (financials_row_mapping, earnings_estimates_row_mappings,
													 income_statement_order, cash_flow_statement_order,
													 balance_sheet_order,
													 earnings_estimates_order)
from Data_Retrieval.shared_functions import (convert_to_numeric_divide_by_one_million,
											 return_mean_std_industry_valuations,
											 format_rows, format_cell, convert_none_to_zero, handle_divide_by_zero,
											 create_pie_chart, add_company_to_valuation_list)


def retrieve_holder_information(json_data: dict):
	print(json.dumps(json_data['Holders'], indent=4))
	for key, value in json_data['Holders'].items():
		print(f'{key}: {value}')


def create_company_summary(json_data: dict):
	columns = [
		"Code", "Type", "Name", "Exchange", "PrimaryTicker",
		"FiscalYearEnd", "IPODate", "InternationalDomestic", "GicSector", "GicGroup", "Description",
		"FullTimeEmployees",
		"UpdatedAt",
	]
	df = pd.DataFrame([json_data['General']], columns=columns)
	return df


def create_financial_statement_df(json_data: dict, statement: str, row_order: list,
								  large_negative_rows_to_format: list) -> (pd.DataFrame, pd.DataFrame):
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
	unformated_df = copy.copy(df)

	format_rows(df, large_negative_rows_to_format, large_positive=False)
	format_rows(df, list(set(df.index.to_list()) - set(large_negative_rows_to_format)), large_positive=True)
	return df, unformated_df


def create_valuation_df(json_data: dict, valuation_df: pd.DataFrame, current_price: int) -> pd.DataFrame:
	# Earnings
	revenues = valuation_df.loc['totalRevenue'].iloc[-1]
	earnings = valuation_df.loc['netIncome'].iloc[-1]
	shares_outstanding = valuation_df.loc['commonStockSharesOutstanding'].iloc[-1]

	trailing_eps = handle_divide_by_zero(earnings, shares_outstanding)
	try:
		market_cap = shares_outstanding * current_price
	except (ValueError, TypeError):
		market_cap = json_data['Highlights']['MarketCapitalization'] or 0

	total_cash = valuation_df.loc['cash'].iloc[-1]
	try:
		total_debt = valuation_df.loc['shortLongTermDebtTotal'].iloc[-1] or valuation_df.loc['shortTermDebt'].iloc[-1] + \
					 valuation_df.loc['longTermDebtTotal'].iloc[-1]
	except (ValueError, TypeError):
		total_debt = 0

	try:
		enterprise_value = market_cap + total_debt - total_cash
	except (ValueError, TypeError):
		enterprise_value = market_cap

	ebitda = valuation_df.loc['ebitda'].iloc[-1]
	ev_ebitda = handle_divide_by_zero(enterprise_value, ebitda)
	trailing_price_earnings = handle_divide_by_zero(current_price, trailing_eps)
	forward_eps = json_data['Highlights']['EPSEstimateNextYear']
	forward_price_earnings = handle_divide_by_zero(current_price, forward_eps)
	price_sales = handle_divide_by_zero(market_cap, revenues)

	# Balance Sheet
	current_assets = valuation_df.loc['totalCurrentAssets'].iloc[-1]
	total_assets = valuation_df.loc['totalAssets'].iloc[-1]
	current_debt = valuation_df.loc['shortTermDebt'].iloc[-1]
	# current_liabilities = valuation_df.loc['totalCurrentLiabilities'].iloc[-1]
	total_liabilities = valuation_df.loc['totalLiab'].iloc[-1]
	try:
		book_value = total_assets - total_liabilities
	except (ValueError, TypeError):
		book_value = None

	intangible_assets = valuation_df.loc['intangibleAssets'].iloc[-1]
	goodwill = valuation_df.loc['goodWill'].iloc[-1]
	try:
		tangible_assets = total_assets - intangible_assets - goodwill
	except (ValueError, TypeError):
		try:
			tangible_assets = total_assets - intangible_assets
		except (ValueError, TypeError):
			tangible_assets = total_assets
	try:
		tangible_book = tangible_assets - total_liabilities
	except (ValueError, TypeError):
		tangible_book = None
	price_tangible_book = handle_divide_by_zero(market_cap, tangible_book)
	price_book = handle_divide_by_zero(market_cap, book_value)
	price_cash = handle_divide_by_zero(market_cap, total_cash)
	try:
		net_cash = total_cash - total_debt
	except (ValueError, TypeError):
		net_cash = None
	price_net_cash = handle_divide_by_zero(market_cap, net_cash)
	preferred_stock_equity = valuation_df.loc['preferredStockTotalEquity'].iloc[-1]
	try:
		net_net = current_assets - (
			total_liabilities if total_liabilities is not None else 0 + preferred_stock_equity if preferred_stock_equity is not None else 0)
	except (ValueError, TypeError):
		net_net = None
	price_net_net = handle_divide_by_zero(market_cap, net_net)
	debt_to_equity = handle_divide_by_zero(total_liabilities, valuation_df.loc['totalStockholderEquity'].iloc[-1])

	# Cash Flow
	price_operating_cash_flow = handle_divide_by_zero(market_cap,
													  valuation_df.loc['totalCashFromOperatingActivities'].iloc[-1])
	price_free_cash_flow = handle_divide_by_zero(market_cap, valuation_df.loc['freeCashFlow'].iloc[-1])
	price_net_cash_flow = handle_divide_by_zero(market_cap, valuation_df.loc['changeInCash'].iloc[-1])
	dividend_per_share = json_data['Highlights']['DividendShare']
	dividend_yield = json_data['Highlights']['DividendYield'] or 0
	try:
		dividend = dividend_per_share * shares_outstanding
	except (ValueError, TypeError):
		dividend = None
	price_dividend = handle_divide_by_zero(market_cap, dividend)
	interest_coverage = handle_divide_by_zero(valuation_df.loc['ebit'].iloc[-1],
											  valuation_df.loc['interestExpense'].iloc[-1])
	'''
	DSCR =  Net Operating Income / Debt Service
	where:
	
	Net Operating Income = Adj. EBITDA = (Gross Operating Revenue) − (Operating Expenses)
	Debt Service = (Principal Repayment) + (Interest Payments) + (Lease Payments)
	'''
	debt_service_coverage = handle_divide_by_zero(valuation_df.loc['operatingIncome'].iloc[-1], current_debt)
	try:
		asset_coverage = tangible_assets - current_debt
	except (ValueError, TypeError):
		asset_coverage = None
	asset_coverage_ratio = handle_divide_by_zero(asset_coverage, total_debt)

	df_dict = {
		'Price': current_price,
		'MktCap': market_cap,
		'Enterprise Value': enterprise_value,
		'Revenue': revenues,
		'Dividend Yield': str(round((dividend_yield * 100), 2)) + '%',
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

	industry = json_data['General']['GicSector']
	if not industry or industry == 'null':
		industry = json_data['General']['Sector']
	industry = industry.replace(' ', '_')

	update_dict = {'Code': code}
	ordered_dict = {**update_dict, **df_dict}

	add_company_to_valuation_list(ordered_dict, exchange, code, industry)
	industry_average_valuation_dict = return_mean_std_industry_valuations(exchange, industry)
	large_positive = ['Revenue', 'Dividend Yield']

	if industry_average_valuation_dict:
		for col, mean in industry_average_valuation_dict['Mean'].items():
			if col in large_positive:
				format_cell(result_df, col, mean, industry_average_valuation_dict['StdDev'][col])
			else:
				format_cell(result_df, col, mean, industry_average_valuation_dict['StdDev'][col], False)

	return result_df


def create_highlights_df(hl_df: pd.DataFrame):
	hl_df.fillna(sys.float_info.epsilon)
	hl_df.replace(0, sys.float_info.epsilon, inplace=True)
	hl_df.replace(0.0, sys.float_info.epsilon, inplace=True)
	hl_df.loc['Revenue Increase'] = hl_df.loc['totalRevenue'].pct_change()
	hl_df.loc['Revenue Increase'].iloc[0] = 0
	# Calculate rolling percentage increase over the past 3 cells
	hl_df.loc['Rolling Revenue Increase 3yr'] = hl_df.loc['totalRevenue'].rolling(window=3,
																				  min_periods=1).mean().pct_change()

	hl_df.loc['Turonver Avg3'] = (hl_df.loc['netIncome'] / hl_df.loc['totalRevenue']).rolling(window=3,
																							  min_periods=1).mean()
	hl_df.loc['ROE Avg3'] = hl_df.loc['netIncome'] / hl_df.loc['totalStockholderEquity'].rolling(window=3,
																								 min_periods=1).mean()
	net_operating_profit_after_tax = hl_df.loc['operatingIncome'] - hl_df.loc['incomeTaxExpense']
	non_interest_bearing_current_liabilities = hl_df.loc['totalCurrentLiabilities'] - hl_df.loc['shortTermDebt']
	invested_capital = hl_df.loc['totalAssets'] - (hl_df.loc['cash'] + non_interest_bearing_current_liabilities)
	other_invested_capital = hl_df.loc['netWorkingCapital'] + hl_df.loc['propertyPlantAndEquipmentNet']
	if (invested_capital == 0.0).any():
		hl_df.loc['ROIC Avg3'] = 0
		hl_df.loc['CROIC Avg3'] = 0
	else:
		hl_df.loc['ROIC Avg3'] = (net_operating_profit_after_tax / invested_capital).rolling(window=3,
																							 min_periods=1).mean()
		hl_df.loc['CROIC Avg3'] = (hl_df.loc['freeCashFlow'] / invested_capital).rolling(window=3, min_periods=1).mean()

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
	# Book /sh
	hl_df.loc['Book /sh'] = book_value / hl_df.loc['commonStockSharesOutstanding']
	hl_df.loc['Tang Book /sh'] = tangible_book / hl_df.loc['commonStockSharesOutstanding']

	# Calculate 'Debt Overhang' by subtracting 'cashAndShortTermInvestments' from the sum of the other two
	highlight_values = hl_df.loc[['shortTermDebt', 'nonCurrentLiabilitiesTotal', 'cashAndShortTermInvestments']]
	highlight_values = highlight_values.applymap(convert_none_to_zero)
	hl_df.loc['Debt Overhang'] = highlight_values.loc['shortTermDebt'] + highlight_values.loc[
		'nonCurrentLiabilitiesTotal'] - highlight_values.loc['cashAndShortTermInvestments']

	percent_columns = [
		'Revenue Increase', 'Rolling Revenue Increase 3yr', 'Turonver Avg3', 'ROE Avg3', 'ROIC Avg3', 'CROIC Avg3',
		'Gross Margin', 'EBITDA Margin', 'Net Inc Margin', 'CFO Margin', 'FCF Margin', 'NCF Margin', 'RND % Revenue',
		'Selling Marketing % Revenue', 'Selling General % Revenue',
	]

	# Multiply selected rows by 100
	hl_df.loc[percent_columns] *= 100

	# Reorder the DataFrame columns
	new_order = [
		'commonStockSharesOutstanding', 'totalRevenue', 'Revenue Increase', 'Rolling Revenue Increase 3yr',
		'Turonver Avg3', 'ROE Avg3', 'ROIC Avg3', 'CROIC Avg3',
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
									 'Turonver Avg3', 'ROE Avg3', 'ROIC Avg3', 'CROIC Avg3',
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

	return hl_df


def create_balance_sheet_pie_charts(balance_sheet_df: pd.DataFrame) -> str:
	latest_data = balance_sheet_df.iloc[:, -1:]
	asset_components = ['Cash', 'Net Receivables', 'Inventory', 'Other Current Assets',
						'Property, Plant, and Equipment', 'Intangible Assets', 'Goodwill',
						'Non-Current Assets Other']
	asset_pie_chart = create_pie_chart(latest_data, asset_components)

	liability_components = ['Short-Term Debt', 'Accounts Payable', 'Current Deferred Revenue',
							'Other Current Liabilities',
							'Long-Term Debt', 'Capital Lease Obligations', 'Deferred Long-Term Liabilities']
	liability_pie_chart = create_pie_chart(latest_data, liability_components)

	# HTML content with side-by-side charts
	html_content = """
	    <div style="display: flex; justify-content: center; align-items: center;">
	        """
	if asset_pie_chart is not None:
		html_content += f"""
	        <div style="text-align: center;">
	            <h2>Total Assets Composition Pie Chart</h2>
	            <img src="data:image/png;base64,{asset_pie_chart}" alt='Total Assets Pie Chart' style="width: 100%;">
	        </div>
	    """
	if liability_pie_chart is not None:
		html_content += f"""
	        <div style="text-align: center;">
	            <h2>Total Liabilities Composition Pie Chart</h2>
	            <img src="data:image/png;base64,{liability_pie_chart}" alt='Total Liabilities Pie Chart' style="width: 100%;">
	        </div>
	    """
	html_content += """
	    </div>
	"""
	return html_content


def create_earnings_estimates_df(json_data: dict):
	current_date_str = str(datetime.now().date())
	earnings_dict = [value for period, value in json_data['Earnings']['Trend'].items() if period >= current_date_str]
	earnings_df = pd.DataFrame(earnings_dict)
	if not earnings_df.empty:
		earnings_df.set_index("date", inplace=True)
		earnings_df = earnings_df.T.iloc[:, ::-1]

		earnings_df = earnings_df.reindex(earnings_estimates_order)
		earnings_df.rename(index=earnings_estimates_row_mappings, inplace=True)

	return earnings_df


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
	try:
		hl_df.set_index("date", inplace=True)
	except KeyError:
		print(f"Invalid data format for ticker")
		return

	# Transpose and invert the DataFrame
	hl_df = hl_df.T.iloc[:, ::-1]

	# Convert strings to numbers and divide by 1 million
	numeric_columns = hl_df.columns.difference(["date"])
	hl_df[numeric_columns] = hl_df[numeric_columns].applymap(convert_to_numeric_divide_by_one_million)

	# Create valuation df based off highlights df
	valuation_df = create_valuation_df(json_data, hl_df, current_price)

	hl_df = create_highlights_df(hl_df)

	# Access the DataFrames for each financial statement
	financial_statements = {
		'Balance_Sheet': balance_sheet_order,
		'Income_Statement': income_statement_order,
		'Cash_Flow': cash_flow_statement_order
	}

	large_negative_rows_to_format = [
		['Short-Term Debt', 'Long-Term Debt', 'Long-Term Debt Total', 'Capital Lease Obligations',
		 'Short-Long Term Debt Total', 'Deferred Long-Term Liabilities', 'Non-Current Liabilities Total',
		 'Other Current Liabilities', 'Total Current Liabilities', 'Accounts Payable', 'Current Deferred Revenue',
		 'Other Liabilities', 'Total Liabilities', 'Common Stock Shares Outstanding'],
		['Cost of Revenues', 'Other Operating Expenses', 'Research and Development', 'Selling and Marketing Expenses',
		 'Selling, General, and Administrative', 'Total Operating Expenses', 'Interest Expense',
		 'Tax Provision'],
		['Change to Net Income', 'Change to Operating Activities', 'Change to Inventory',
		 'Capital Expenditures', 'Depreciation', 'Net Borrowings', 'Stock-Based Compensation']]

	financial_statement_dataframes = []
	html_pie_charts = ''
	for i, (key, order) in enumerate(financial_statements.items()):
		df, unformatted_df = create_financial_statement_df(json_data, key, order, large_negative_rows_to_format[i])
		financial_statement_dataframes.append(df)

		if key == "Balance_Sheet":
			html_pie_charts = create_balance_sheet_pie_charts(unformatted_df)

	summary_df = create_company_summary(json_data)
	summary_col_widths = {'Description': 900}

	earnings_estimates_df = create_earnings_estimates_df(json_data)

	# Combine all dataframes into one
	combined_html = summary_df.to_html(col_space=summary_col_widths, index=False, na_rep='N/A') + "<br>" + \
					"<h2>Company Valuation</h2>" + valuation_df.to_html(index=False, escape=False,
																		na_rep='N/A') + "<br>" + \
					"<h2>Company Summary</h2>" + hl_df.to_html(classes='highlight-table', escape=False, na_rep='N/A') + \
					"<h2>Future Earnings Estimates</h2>"  # + earnings_estimates_df.to_html(index=False, escape=False,
	# na_rep='N/A')

	for df, title in zip(financial_statement_dataframes, financial_statements.keys()):
		classes = title + '-table'
		if title == "Balance_Sheet":
			combined_html += f"<br><h2>{title.replace('_', ' ')}</h2>" + df.to_html(classes=classes, escape=False,
																					na_rep='N/A') + html_pie_charts
		else:
			combined_html += f"<br><h2>{title.replace('_', ' ')}</h2>" + df.to_html(classes=classes, escape=False,
																					na_rep='N/A')

	# Display the DataFrame in a Bokeh Div widget
	div_widget = Div(text=INDIVIDUAL_COMPANY_TABLE_STYLE + combined_html, width=1500, height=900)

	# Save the layout containing the Div widget
	stock_code = summary_df.iloc[0, 0]
	output_file("Data_Output/Individual/AU/" + str(stock_code) + ".html")
	save(column(div_widget))
