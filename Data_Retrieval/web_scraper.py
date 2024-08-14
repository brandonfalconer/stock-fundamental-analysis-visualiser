import datetime
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os.path


def get_all_asx_companies(sort_column="market_cap"):
    """
    Return a DF of all AU listed companies, sorted by sector.
    :param sort_column:
    :return:
    """

    selected_information = [
        "title",
        "code",
        "sector_id",
        "last",
        "change_percent",
        "month_percent_change",
        "1yr_percent_change",
        "52w_low",
        "52w_high",
        "volume",
        "market_cap",
    ]

    # Check if an up to date excel file exists
    excel_file_name = (
        "Data/All_Stocks/" + datetime.today().strftime("%Y-%m-%d") + "_all_stocks.xlsx"
    )
    if os.path.isfile(excel_file_name):
        print("All stocks file exist.")
        all_stock_df = pd.read_excel(excel_file_name)
        return selected_information, all_stock_df

    print("All stocks file does not exist, attempting to create the file.")

    # Using marketindex.com.au for stock market information
    url = "https://www.marketindex.com.au/asx-listed-companies"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html_page = urlopen(req)

    # Get HTML content
    soup = BeautifulSoup(html_page, "html.parser")

    # Find specific data
    asx_table = soup.find("asx-listed-companies-table")
    asx_table_str = (
        str(asx_table)
        .replace("&quot;", "")
        .replace("&amp;", "&")
        .replace('<asx-listed-companies-table :companies="[', "")
        .replace(']"></asx-listed-companies-table>', "")
        .split(",{")
    )

    industry_dict = {
        "12": "Financials",
        "13": "Materials",
        "14": "Health Care",
        "15": "Industrials",
        "16": "Consumer Discretionary",
        "17": "Real Estate",
        "18": "Energy",
        "19": "Consumer Staples",
        "20": "Information Technology",
        "21": "Communication Services",
        "22": "Utilities",
        "null": "Other",
    }

    data_list = []
    temp_list = []
    for line in range(len(asx_table_str)):
        value = asx_table_str[line].split(",")

        for info in selected_information:
            for item in value:
                item = item.split(":")
                if item[0] == info:
                    if info == "sector_id":
                        temp_list.append(industry_dict[item[1]])
                    elif info in ["market_cap", "volume"]:
                        temp_list.append(int(item[1]))
                    elif info in [
                        "last",
                        "change",
                        "month_percent_change",
                        "1yr_percent_change",
                        "52w_low",
                        "52w_high",
                    ]:
                        temp_list.append(float(item[1]))
                    else:
                        temp_list.append(item[1])
                    break

        data_list.append(temp_list)
        temp_list = []

    # Create dataframe
    all_stock_df = pd.DataFrame(data_list, columns=selected_information)
    all_stock_df = all_stock_df.sort_values(
        ["sector_id", "market_cap"], ascending=[True, False]
    )
    all_stock_df.to_excel(excel_file_name)

    return selected_information, all_stock_df
