import copy
import json
import os
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd
from bokeh.io import save, output_file
from bokeh.layouts import column
from bokeh.models import Div

import Data_Retrieval.eodhd_apis as eodhd
from Data_Formatting.css_styling import individual_company_table_css
from Data_Retrieval.constant_data_structures import (
    financials_row_mapping,
    earnings_estimates_row_mappings,
    income_statement_order,
    cash_flow_statement_order,
    balance_sheet_order,
    earnings_estimates_order,
    share_stats_row_mappings,
    share_stats_order,
)
from Data_Retrieval.eodhd_apis import get_tickers_by_exchange
from Data_Retrieval.mean_std_industry_valuation import (
    return_mean_std_industry_valuations,
    add_company_to_valuation_list,
)
from Data_Retrieval.shared_functions import (
    convert_to_numeric_divide_by_one_million,
    format_rows,
    format_cell,
    convert_none_to_zero,
    handle_divide_by_zero,
    create_pie_chart,
    validate_ticker,
    convert_to_percentage,
)


def retrieve_holder_information(json_data: dict) -> None:
    print(json.dumps(json_data["Holders"], indent=4))
    for key, value in json_data["Holders"].items():
        print(f"{key}: {value}")


def create_company_summary(json_data: dict) -> pd.DataFrame:
    columns = [
        "Code",
        "Type",
        "Name",
        "Exchange",
        "PrimaryTicker",
        "FiscalYearEnd",
        "IPODate",
        "InternationalDomestic",
        "GicSector",
        "GicGroup",
        "Description",
        "FullTimeEmployees",
        "UpdatedAt",
    ]
    df = pd.DataFrame([json_data["General"]], columns=columns)
    return df


def create_financial_statement_df(
    json_data: dict,
    statement: str,
    row_order: list,
    large_negative_rows_to_format: list,
) -> (pd.DataFrame, pd.DataFrame, int):
    summarised_flattened_data = []
    number_of_years = 0
    for i, (date, details) in enumerate(
        json_data["Financials"][statement]["yearly"].items()
    ):
        summarised_entry = {"date": details["date"]}
        summarised_entry.update(details)
        summarised_flattened_data.append(summarised_entry)
        number_of_years += 1
        # Use previous 20 years
        if i == 19:
            break

    df = pd.DataFrame(summarised_flattened_data)
    df.set_index("date", inplace=True)
    df = df.T.iloc[:, ::-1]

    numeric_columns = df.columns.difference(["date"])
    df[numeric_columns] = df[numeric_columns].applymap(
        convert_to_numeric_divide_by_one_million
    )
    df = df.reindex(row_order)
    # df = df.dropna(how='all')
    df = df.fillna("")
    df.rename(index=financials_row_mapping, inplace=True)
    unformated_df = copy.copy(df)

    format_rows(df, large_negative_rows_to_format, large_positive=False)
    format_rows(
        df,
        list(set(df.index.to_list()) - set(large_negative_rows_to_format)),
        large_positive=True,
    )
    return df, unformated_df, number_of_years


def create_valuation_df(
    json_data: dict, valuation_df: pd.DataFrame, current_price: float
) -> (pd.DataFrame, dict):
    # Income Statement
    revenues = valuation_df.loc["totalRevenue"].iloc[-1]
    earnings = valuation_df.loc["netIncome"].iloc[-1]
    try:
        shares_outstanding = valuation_df.loc["commonStockSharesOutstanding"].iloc[-1]
        if shares_outstanding is None or np.isnan(shares_outstanding):
            shares_outstanding = convert_to_numeric_divide_by_one_million(
                json_data["SharesStats"]["SharesOutstanding"]
            )
    except KeyError:
        shares_outstanding = None

    trailing_eps = handle_divide_by_zero(earnings, shares_outstanding)
    try:
        market_cap = shares_outstanding * current_price
    except (ValueError, TypeError):
        market_cap = json_data["Highlights"]["MarketCapitalization"] or 0

    total_cash = valuation_df.loc["cash"].iloc[-1]
    try:
        total_debt = (
            valuation_df.loc["shortLongTermDebtTotal"].iloc[-1]
            or valuation_df.loc["shortTermDebt"].iloc[-1]
            + valuation_df.loc["longTermDebtTotal"].iloc[-1]
        )
    except (ValueError, TypeError):
        total_debt = 0

    try:
        enterprise_value = market_cap + total_debt - total_cash

        if not enterprise_value or np.isnan(enterprise_value):
            if "Valuation" in json_data and "EnterpriseValue" in json_data["Valuation"]:
                enterprise_value = json_data["Valuation"]["EnterpriseValue"]
            else:
                enterprise_value = market_cap

    except (ValueError, TypeError):
        enterprise_value = market_cap

    ebitda = valuation_df.loc["ebitda"].iloc[-1]
    ev_ebitda = handle_divide_by_zero(enterprise_value, ebitda)
    ebit = valuation_df.loc["ebit"].iloc[-1]
    ev_ebit = handle_divide_by_zero(enterprise_value, ebit)

    trailing_price_earnings = handle_divide_by_zero(current_price, trailing_eps)
    forward_eps = json_data["Highlights"]["EPSEstimateNextYear"]
    forward_price_earnings = handle_divide_by_zero(current_price, forward_eps)
    price_sales = handle_divide_by_zero(market_cap, revenues)

    # PEG Ratio is calculated by dividing forward EPS by the average of future period 12 month EPS estimates
    current_date_str = str(datetime.now().date())
    try:
        expected_future_earnings = [
            float(value["earningsEstimateGrowth"])
            for period, value in json_data["Earnings"]["Trend"].items()
            if period >= current_date_str
            and value["earningsEstimateGrowth"] is not None
        ]
        if expected_future_earnings and forward_price_earnings:
            expected_average_future_earnings_growth = np.mean(expected_future_earnings)
            price_earnings_growth_3yr = handle_divide_by_zero(
                forward_price_earnings, (expected_average_future_earnings_growth * 100)
            )
        else:
            price_earnings_growth_3yr = None

    except (ValueError, KeyError):
        price_earnings_growth_3yr = None

    # Balance Sheet
    current_assets = valuation_df.loc["totalCurrentAssets"].iloc[-1]
    total_assets = valuation_df.loc["totalAssets"].iloc[-1]
    current_debt = valuation_df.loc["shortTermDebt"].iloc[-1]
    # current_liabilities = valuation_df.loc['totalCurrentLiabilities'].iloc[-1]
    total_liabilities = valuation_df.loc["totalLiab"].iloc[-1]
    try:
        book_value = total_assets - total_liabilities
    except (ValueError, TypeError):
        book_value = None

    intangible_assets = valuation_df.loc["intangibleAssets"].iloc[-1]
    goodwill = valuation_df.loc["goodWill"].iloc[-1]
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
    preferred_stock_equity = valuation_df.loc["preferredStockTotalEquity"].iloc[-1]
    try:
        net_net = current_assets - (
            total_liabilities
            if total_liabilities is not None
            else 0 + preferred_stock_equity if preferred_stock_equity is not None else 0
        )
    except (ValueError, TypeError):
        net_net = None
    price_net_net = handle_divide_by_zero(market_cap, net_net)
    debt_to_equity = handle_divide_by_zero(
        total_liabilities, valuation_df.loc["totalStockholderEquity"].iloc[-1]
    )

    # Cash Flow
    price_operating_cash_flow = handle_divide_by_zero(
        market_cap, valuation_df.loc["totalCashFromOperatingActivities"].iloc[-1]
    )
    price_free_cash_flow = handle_divide_by_zero(
        market_cap, valuation_df.loc["freeCashFlow"].iloc[-1]
    )
    dividend_per_share = json_data["Highlights"]["DividendShare"]
    dividend_yield = json_data["Highlights"]["DividendYield"] or 0
    try:
        dividend = dividend_per_share * shares_outstanding
    except (ValueError, TypeError):
        dividend = None
    price_dividend = handle_divide_by_zero(market_cap, dividend)
    interest_coverage = handle_divide_by_zero(
        valuation_df.loc["ebit"].iloc[-1], valuation_df.loc["interestExpense"].iloc[-1]
    )
    """
	DSCR =  Net Operating Income / Debt Service
	where:
	
	Net Operating Income = Adj. EBITDA = (Gross Operating Revenue) − (Operating Expenses)
	Debt Service = (Principal Repayment) + (Interest Payments) + (Lease Payments)
	"""
    debt_service_coverage = handle_divide_by_zero(
        valuation_df.loc["operatingIncome"].iloc[-1], current_debt
    )
    try:
        asset_coverage = tangible_assets - current_debt
    except (ValueError, TypeError):
        asset_coverage = None
    asset_coverage_ratio = handle_divide_by_zero(asset_coverage, total_debt)

    df_dict = {
        "Price": current_price,
        "MktCap": market_cap,
        "EV": enterprise_value,
        "Revenue": revenues,
        "Div Yield": dividend_yield,
        "Debt/Equity": debt_to_equity,
        "P/S": price_sales,
        "EV/EBITDA": ev_ebitda,
        "EV/EBIT": ev_ebit,
        "P/B": price_book,
        "P/TB": price_tangible_book,
        "Trailing P/E": trailing_price_earnings,
        "Forward P/E": forward_price_earnings,
        "PEG 3yr": price_earnings_growth_3yr,
        "P/CFO": price_operating_cash_flow,
        "P/FCF": price_free_cash_flow,
        "P/Div": price_dividend,
        "P/Cash": price_cash,
        "P/NCash": price_net_cash,
        "P/NN": price_net_net,
        "Interest Cov": interest_coverage,
        "Service Cov": debt_service_coverage,
        "Asset Cov": asset_coverage_ratio,
    }
    df_dict = {
        key: (round(value, 2) if isinstance(value, (float, int)) else value)
        and (value if isinstance(value, float) and not np.isnan(value) else "")
        for key, value in df_dict.items()
    }
    result_df = pd.DataFrame.from_dict([df_dict])
    try:
        result_df["Div Yield"] = round(result_df["Div Yield"] * 100, 2)
    except (KeyError, ValueError, TypeError):
        result_df["Div Yield"] = 0

    # Copy updated information into valuation tracker to calculate industry mean and std
    exchange = json_data["General"]["Exchange"]
    code = json_data["General"]["Code"]

    try:
        industry = json_data["General"]["GicSector"]
        if not industry or industry == "null":
            industry = json_data["General"]["Sector"]
        industry = industry.replace(" ", "_")
    except (KeyError, AttributeError):
        industry = "None"

    update_dict = {"Code": code}
    ordered_dict = {**update_dict, **df_dict}

    add_company_to_valuation_list(ordered_dict, exchange, code, industry)
    industry_average_valuation_dict = return_mean_std_industry_valuations(
        exchange, industry
    )
    large_positive = ["Revenue", "Div Yield"]

    if industry_average_valuation_dict:
        for col, median in industry_average_valuation_dict["Median"].items():
            if col in large_positive:
                format_cell(
                    result_df,
                    col,
                    median,
                    industry_average_valuation_dict["MAD"][col],
                    red_negative=True,
                )
            else:
                format_cell(
                    result_df,
                    col,
                    median,
                    industry_average_valuation_dict["MAD"][col],
                    large_positive=False,
                    red_negative=True,
                )

    return result_df, ordered_dict


def calculate_industry_average(api_token: str, exchange: str, industry: str) -> None:
    tickers = get_tickers_by_exchange(api_token, exchange)
    computed_industry = "None"
    for ticker in tickers:
        company_code = ticker["Code"]
        company_code = validate_ticker(company_code, exchange)
        json_data = eodhd.get_fundamental_data(api_token, exchange, company_code)
        if not validate_common_stock_tickers(json_data, company_code):
            continue

        computed_industry = json_data["General"]["GicSector"]
        if not computed_industry or computed_industry == "null":
            computed_industry = json_data["General"]["Sector"]

        if industry != computed_industry:
            continue

        company_price = eodhd.get_stock_close_price(api_token, exchange, company_code)
        if company_price is None:
            continue
        summarised_df = create_summarised_df(json_data)
        if summarised_df.empty:
            continue
        _, ordered_dict = create_valuation_df(json_data, summarised_df, company_price)
        add_company_to_valuation_list(
            ordered_dict, exchange, company_code, computed_industry
        )

    return_mean_std_industry_valuations(exchange, computed_industry)


def create_highlights_df(hl_df: pd.DataFrame) -> pd.DataFrame:
    # Avoid divide by 0's
    hl_df.fillna(sys.float_info.epsilon)
    # hl_df.replace(0, sys.float_info.epsilon, inplace=True)
    hl_df.replace(0.0, sys.float_info.epsilon, inplace=True)

    # Revenue metrics
    hl_df.loc["Revenue Increase"] = hl_df.loc["totalRevenue"].pct_change()

    # Calculate rolling percentage increase over the past 3 cells
    hl_df.loc["Revenue Increase 3yr"] = (
        hl_df.loc["totalRevenue"].rolling(window=3, min_periods=1).mean().pct_change()
    )

    hl_df.loc["Turnover Avg3"] = (
        (hl_df.loc["netIncome"] / hl_df.loc["totalRevenue"])
        .rolling(window=3, min_periods=1)
        .mean()
    )

    # Return metrics
    hl_df.loc["ROE Avg3"] = (
        hl_df.loc["netIncome"]
        / hl_df.loc["totalStockholderEquity"].rolling(window=3, min_periods=1).mean()
    )
    net_operating_profit_after_tax = hl_df.loc["ebit"] - hl_df.loc["incomeTaxExpense"]
    non_interest_bearing_current_liabilities = (
        hl_df.loc["totalCurrentLiabilities"] - hl_df.loc["shortTermDebt"]
    )
    invested_capital = hl_df.loc["totalAssets"] - (
        hl_df.loc["cash"] + non_interest_bearing_current_liabilities
    )
    invested_capital_damodaran = (
        hl_df.loc["totalLiab"] + hl_df.loc["totalStockholderEquity"] - hl_df.loc["cash"]
    )
    other_invested_capital = (
        hl_df.loc["netWorkingCapital"] + hl_df.loc["propertyPlantAndEquipmentNet"]
    )
    if (invested_capital_damodaran == 0.0).any():
        hl_df.loc["ROIC Avg3"] = 0
        hl_df.loc["CROIC Avg3"] = 0
    else:
        hl_df.loc["ROIC Avg3"] = (
            (net_operating_profit_after_tax / invested_capital_damodaran)
            .rolling(window=3, min_periods=1)
            .mean()
        )
        hl_df.loc["CROIC Avg3"] = (
            (hl_df.loc["freeCashFlow"] / invested_capital_damodaran)
            .rolling(window=3, min_periods=1)
            .mean()
        )

    # Margins
    hl_df.loc["Gross Margin"] = hl_df.loc["grossProfit"] / hl_df.loc["totalRevenue"]
    hl_df.loc["EBITDA Margin"] = hl_df.loc["ebitda"] / hl_df.loc["totalRevenue"]
    hl_df.loc["Net Inc Margin"] = hl_df.loc["netIncome"] / hl_df.loc["totalRevenue"]
    hl_df.loc["CFO Margin"] = (
        hl_df.loc["totalCashFromOperatingActivities"] / hl_df.loc["totalRevenue"]
    )
    hl_df.loc["FCF Margin"] = hl_df.loc["freeCashFlow"] / hl_df.loc["totalRevenue"]
    hl_df.loc["NCF Margin"] = hl_df.loc["changeInCash"] / hl_df.loc["totalRevenue"]

    # Per share metrics
    hl_df.loc["Common EPS"] = (
        hl_df.loc["netIncomeApplicableToCommonShares"].fillna(hl_df.loc["netIncome"])
        / hl_df.loc["commonStockSharesOutstanding"]
    )
    hl_df.loc["EPS Increase 3yr"] = (
        hl_df.loc["Common EPS"].rolling(window=3, min_periods=1).mean().pct_change()
    )
    hl_df.loc["EBITDA /sh"] = (
        hl_df.loc["ebitda"] / hl_df.loc["commonStockSharesOutstanding"]
    )
    hl_df.loc["CFO /sh"] = (
        hl_df.loc["totalCashFromOperatingActivities"]
        / hl_df.loc["commonStockSharesOutstanding"]
    )
    hl_df.loc["FCF /sh"] = (
        hl_df.loc["freeCashFlow"] / hl_df.loc["commonStockSharesOutstanding"]
    )
    hl_df.loc["RND Margin"] = (
        hl_df.loc["researchDevelopment"] / hl_df.loc["totalRevenue"]
    )
    hl_df.loc["Marketing Margin"] = (
        hl_df.loc["sellingAndMarketingExpenses"] / hl_df.loc["totalRevenue"]
    )
    hl_df.loc["General Margin"] = (
        hl_df.loc["sellingGeneralAdministrative"] / hl_df.loc["totalRevenue"]
    )

    hl_df.loc["Assets /sh"] = (
        hl_df.loc["totalAssets"] / hl_df.loc["commonStockSharesOutstanding"]
    )
    book_value = hl_df.loc["totalAssets"] - hl_df.loc["totalLiab"]
    tangible_book = book_value - hl_df.loc["intangibleAssets"]
    hl_df.loc["Book /sh"] = book_value / hl_df.loc["commonStockSharesOutstanding"]
    hl_df.loc["Tang Book /sh"] = (
        tangible_book / hl_df.loc["commonStockSharesOutstanding"]
    )

    # Calculate 'Debt Overhang' by subtracting 'cashAndShortTermInvestments' from the sum of the other two
    highlight_values = hl_df.loc[
        ["shortTermDebt", "nonCurrentLiabilitiesTotal", "cashAndShortTermInvestments"]
    ]
    highlight_values = highlight_values.applymap(convert_none_to_zero)
    hl_df.loc["Debt Overhang"] = (
        highlight_values.loc["shortTermDebt"]
        + highlight_values.loc["nonCurrentLiabilitiesTotal"]
        - highlight_values.loc["cashAndShortTermInvestments"]
    )

    percent_columns = [
        "Revenue Increase",
        "Revenue Increase 3yr",
        "Turnover Avg3",
        "ROE Avg3",
        "ROIC Avg3",
        "CROIC Avg3",
        "Gross Margin",
        "EBITDA Margin",
        "Net Inc Margin",
        "CFO Margin",
        "FCF Margin",
        "NCF Margin",
        "RND Margin",
        "EPS Increase 3yr",
        "Marketing Margin",
        "General Margin",
    ]

    # Clip percent rows to bounded -1 to 1 (could improve this to be > < a exponential)
    for column in percent_columns:
        hl_df.loc[column] = hl_df.loc[column].clip(lower=-1, upper=1)

    # Multiply selected rows by 100
    hl_df.loc[percent_columns] *= 100

    # Reorder the DataFrame columns
    new_order = [
        "commonStockSharesOutstanding",
        "totalRevenue",
        "Revenue Increase",
        "Revenue Increase 3yr",
        "Turnover Avg3",
        "ROE Avg3",
        "ROIC Avg3",
        "CROIC Avg3",
        "Gross Margin",
        "EBITDA Margin",
        "Net Inc Margin",
        "CFO Margin",
        "FCF Margin",
        "NCF Margin",
        "netIncome",
        "Common EPS",
        "EPS Increase 3yr",
        "EBITDA /sh",
        "CFO /sh",
        "FCF /sh",
        "RND Margin",
        "Marketing Margin",
        "General Margin",
        "Assets /sh",
        "Book /sh",
        "Tang Book /sh",
        "Debt Overhang",
    ]
    hl_df = hl_df.reindex(new_order)

    # Rename the rows
    hl_df.rename(index=financials_row_mapping, inplace=True)
    hl_df = hl_df.fillna("")

    # List of rows to round and format as integers (greater than mean = green)
    large_positive_rows_to_format = [
        "Revenues",
        "Revenue Increase",
        "Revenue Increase 3yr",
        "Gross Margin",
        "Turnover Avg3",
        "ROE Avg3",
        "ROIC Avg3",
        "CROIC Avg3",
        "EBITDA Margin",
        "Net Inc Margin",
        "CFO Margin",
        "FCF Margin",
        "NCF Margin",
        "RND Margin",
        "Common EPS",
        "EPS Increase 3yr",
        "EBITDA /sh",
        "CFO /sh",
        "FCF /sh",
        "Net Income",
        "Assets /sh",
        "Book /sh",
        "Tang Book /sh",
    ]

    hl_df.loc[large_positive_rows_to_format] = hl_df.loc[large_positive_rows_to_format]
    percent_columns_to_format = list(
        set(percent_columns) & set(large_positive_rows_to_format)
    )
    remaining_columns = list(
        set(large_positive_rows_to_format) - set(percent_columns_to_format)
    )

    format_rows(
        hl_df, percent_columns_to_format, large_positive=True, add_percentage=True
    )
    format_rows(hl_df, remaining_columns, large_positive=True)

    # List of rows to round and format as integers (greater than mean = green)
    large_negative_rows_to_format = [
        "Shares Outstanding",
        "Marketing Margin",
        "General Margin",
        "Debt Overhang",
    ]
    hl_df.loc[large_negative_rows_to_format] = hl_df.loc[large_negative_rows_to_format]

    percent_columns_to_format = list(
        set(percent_columns) & set(large_negative_rows_to_format)
    )
    remaining_columns = list(
        set(large_negative_rows_to_format) - set(percent_columns_to_format)
    )

    format_rows(
        hl_df, percent_columns_to_format, large_positive=False, add_percentage=True
    )
    format_rows(hl_df, remaining_columns, large_positive=False)

    return hl_df


def create_balance_sheet_pie_charts(balance_sheet_df: pd.DataFrame) -> str:
    latest_data = balance_sheet_df.iloc[:, -1:]
    asset_components = [
        "Cash",
        "Net Receivables",
        "Inventory",
        "Other Current Assets",
        "Property, Plant, and Equipment",
        "Intangible Assets",
        "Goodwill",
        "Non-Current Assets Other",
    ]
    asset_pie_chart = create_pie_chart(latest_data, asset_components)

    liability_components = [
        "Short-Term Debt",
        "Accounts Payable",
        "Current Deferred Revenue",
        "Other Current Liabilities",
        "Long-Term Debt",
        "Capital Lease Obligations",
        "Deferred Long-Term Liabilities",
    ]
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


def create_earnings_estimates_df(json_data: dict) -> pd.DataFrame:
    current_date = datetime.now().date()
    six_months_earlier = str(current_date - relativedelta(months=6))

    if current_date.month > 6:  # If today is after June 30, we're in the next financial year
        end_of_fy = datetime(current_date.year + 1, 6, 30)
    else:  # If today is before or on June 30, we're in the current financial year
        end_of_fy = datetime(current_date.year, 6, 30)

    earnings_dict = [
        value
        for period, value in json_data["Earnings"]["Trend"].items()
        if period >= six_months_earlier
    ]
    earnings_df = pd.DataFrame.from_records(earnings_dict)

    if not earnings_df.empty:
        earnings_df.set_index("date", inplace=True)
        earnings_df = earnings_df.T.iloc[:, ::-1]

        earnings_df = earnings_df.reindex(earnings_estimates_order)
        earnings_df = earnings_df.dropna(axis=1)
        earnings_df.rename(index=earnings_estimates_row_mappings, inplace=True)

    try:
        earnings_df.loc["Revenue Est Avg"] = earnings_df.loc["Revenue Est Avg"].apply(
            convert_to_numeric_divide_by_one_million
        )
    except KeyError:
        pass
    try:
        earnings_df.loc["EPS Est Growth"] = earnings_df.loc["EPS Est Growth"].apply(
            convert_to_percentage
        )
        earnings_df.loc["Revenue Est Growth"] = earnings_df.loc[
            "Revenue Est Growth"
        ].apply(convert_to_percentage)
    except KeyError:
        pass

    shares_outstanding = json_data['SharesStats']['SharesOutstanding']
    try:
        eps_estimates = earnings_df.loc['EPS Est Avg']
        earnings_df.loc["Net Income Equiv"] = eps_estimates.astype(float) * (shares_outstanding / 1000000)
    except (KeyError, ValueError):
        pass

    desired_row_order = [
        "Revenue Est Avg",
        "Revenue Est Growth",
        "EPS Est Avg",
        "Net Income Equiv",
        "EPS Est Growth",
        "EPS Est Num of Analysts",
        "Revenue Est Number of Analysts",
    ]
    earnings_df = earnings_df.reindex(desired_row_order)

    percent_columns_to_format = ["EPS Est Growth", "Revenue Est Growth"]
    columns_to_format = [
        "EPS Est Avg",
        "Net Income Equiv",
        "EPS Est Num of Analysts",
        "Revenue Est Avg",
        "Revenue Est Number of Analysts",
    ]
    format_rows(earnings_df, percent_columns_to_format, add_percentage=True)
    format_rows(earnings_df, columns_to_format)
    return earnings_df


def create_share_statistics_df(json_data: dict) -> pd.DataFrame:
    share_stats_df = pd.DataFrame([json_data["SharesStats"]])

    if not share_stats_df.empty:
        share_stats_df = share_stats_df.reindex(columns=share_stats_order)
        share_stats_df.rename(columns=share_stats_row_mappings, inplace=True)

    try:
        share_stats_df["Shares Outstanding"] = share_stats_df[
            "Shares Outstanding"
        ].apply(convert_to_numeric_divide_by_one_million)
        share_stats_df["Shares Float"] = share_stats_df["Shares Float"].apply(
            convert_to_numeric_divide_by_one_million
        )
    except KeyError:
        pass

    percent_columns_to_format_mean_std = {
        "Percent Insiders": [5, 3],
        "Percent Institutions": [50, 15],
        "Short Percent Outstanding": [0, 2],
    }

    # Drop columns without values
    share_stats_df = share_stats_df.dropna(axis=1)

    for col in share_stats_df:
        if col in percent_columns_to_format_mean_std:
            format_cell(
                share_stats_df,
                col,
                percent_columns_to_format_mean_std[col][0],
                percent_columns_to_format_mean_std[col][1],
                add_percentage=True,
                dont_round=True,
            )
        else:
            format_cell(share_stats_df, col, None, None)

    return share_stats_df


def create_summarised_df(json_data: dict) -> (pd.DataFrame, None):
    summarised_flattened_data = []

    try:
        for i, (date, details) in enumerate(
            json_data["Financials"]["Income_Statement"]["yearly"].items()
        ):
            summarised_entry = {"date": details["date"]}
            summarised_entry.update(details)

            # Add details from other financial statements for the corresponding date
            for statement_type in ["Income_Statement", "Cash_Flow", "Balance_Sheet"]:
                if date in json_data["Financials"][statement_type]["yearly"]:
                    summarised_entry.update(
                        json_data["Financials"][statement_type]["yearly"][date]
                    )

            summarised_flattened_data.append(summarised_entry)

            # Use previous 20 years
            if i == 19:
                break
    except KeyError:
        print("No financial data available")
        return pd.DataFrame()

    summarised_df = pd.DataFrame(summarised_flattened_data)

    # Set the "date" column as the index
    try:
        summarised_df.set_index("date", inplace=True)
    except KeyError:
        print("Invalid data format for ticker")
        return pd.DataFrame()

    # Transpose and invert the DataFrame
    summarised_df = summarised_df.T.iloc[:, ::-1]

    # Convert strings to numbers and divide by 1 million
    numeric_columns = summarised_df.columns.difference(["date"])
    summarised_df[numeric_columns] = summarised_df[numeric_columns].applymap(
        convert_to_numeric_divide_by_one_million
    )

    return summarised_df


def print_individual_finances(json_data: dict, current_price: float) -> None:
    summarised_df = create_summarised_df(json_data)

    if summarised_df.empty:
        return

    # Create valuation df based off summarised_df
    valuation_df, _ = create_valuation_df(json_data, summarised_df, current_price)

    # Create highlights df based off summarised_df
    hl_df = create_highlights_df(summarised_df)

    # Access the DataFrames for each financial statement
    financial_statements = {
        "Balance_Sheet": balance_sheet_order,
        "Income_Statement": income_statement_order,
        "Cash_Flow": cash_flow_statement_order,
    }

    large_negative_rows_to_format = [
        [
            "Short-Term Debt",
            "Long-Term Debt",
            "Long-Term Debt Total",
            "Capital Lease Obligations",
            "Short-Long Term Debt Total",
            "Deferred Long-Term Liabilities",
            "Non-Current Liabilities Total",
            "Other Current Liabilities",
            "Total Current Liabilities",
            "Accounts Payable",
            "Current Deferred Revenue",
            "Other Liabilities",
            "Total Liabilities",
            "Common Stock Shares Outstanding",
        ],
        [
            "Cost of Revenues",
            "Other Operating Expenses",
            "Research and Development",
            "Selling and Marketing Expenses",
            "Selling, General, and Administrative",
            "Total Operating Expenses",
            "Interest Expense",
            "Tax Provision",
        ],
        [
            "Change to Net Income",
            "Change to Operating Activities",
            "Change to Inventory",
            "Capital Expenditures",
            "Depreciation",
            "Net Borrowings",
            "Stock-Based Compensation",
        ],
    ]

    financial_statement_dataframes = []
    html_pie_charts = ""
    number_of_years = 0
    for i, (key, order) in enumerate(financial_statements.items()):
        df, unformatted_df, number_of_years = create_financial_statement_df(
            json_data, key, order, large_negative_rows_to_format[i]
        )
        financial_statement_dataframes.append(df)

        if key == "Balance_Sheet":
            html_pie_charts = create_balance_sheet_pie_charts(unformatted_df)

    summary_df = create_company_summary(json_data)
    summary_col_widths = {"Description": 900}

    earnings_estimates_df = create_earnings_estimates_df(json_data)
    share_stats_df = create_share_statistics_df(json_data)

    align = ""
    if number_of_years <= 10:
        align = ' style="text-align: center; "'
    company_name = json_data["General"]["Name"]

    # Combine all dataframes into one
    combined_html = (
        summary_df.to_html(col_space=summary_col_widths, index=False, na_rep="N/A")
        + "<br>"
        + f"<h2>{company_name} Valuation</h2>"
        + valuation_df.to_html(
            classes="valuation-table", index=False, escape=False, na_rep="N/A"
        )
        + "<br>"
        + f"<h2{align}>{company_name} Summary</h2>"
        + hl_df.to_html(
            classes="highlight-table time-series", escape=False, na_rep="N/A"
        )
    )

    if not earnings_estimates_df.empty:
        combined_html += (
            f"<h2{align}>Future Earnings Estimates</h2>"
            + earnings_estimates_df.to_html(classes="short-table", escape=False)
        )

    if not share_stats_df.empty:
        combined_html += f"<h2{align}>Share Statistics</h2>" + share_stats_df.to_html(
            index=False, classes="short-table", escape=False
        )

    for df, title in zip(financial_statement_dataframes, financial_statements.keys()):
        classes = title + "-table time-series"
        if title == "Balance_Sheet":
            combined_html += (
                f"<br><h2{align}>{title.replace('_', ' ')}</h2>"
                + df.to_html(classes=classes, escape=False, na_rep="N/A")
                + html_pie_charts
            )
        else:
            combined_html += (
                f"<br><h2{align}>{title.replace('_', ' ')}</h2>"
                + df.to_html(classes=classes, escape=False, na_rep="N/A")
            )

    # Display the DataFrame in a Bokeh Div widget
    div_widget = Div(
        text=individual_company_table_css(number_of_years) + combined_html,
        width=1500,
        height=900,
    )

    # Save the layout containing the Div widget
    ticker_code = summary_df.iloc[0, 0]
    exchange = summary_df.iloc[0, 3]

    # Microsoft MS-DOS had reserved these names for these system device drivers
    if ticker_code == "PRN":
        ticker_code = "PRN_"
    if ticker_code == "CON":
        ticker_code = "CON_"
    if ticker_code == "AUX":
        ticker_code = "AUX_"
    if ticker_code == "NUL":
        ticker_code = "NUL_"
    if ticker_code == "TRAK":
        ticker_code = "TRAK_"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_location = os.path.join(os.path.dirname(script_dir), f"Data_Output/Individual/{str(exchange)}/{str(ticker_code)}.html")
    output_file(file_location)
    try:
        save(column(div_widget))
    except FileNotFoundError:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(os.path.dirname(script_dir), f"Data_Output/Individual/{str(exchange)}")
        os.makedirs(path)

    print(f"Company formatted html has been saved to {file_location}")
