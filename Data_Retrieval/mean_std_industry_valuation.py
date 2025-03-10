import json
import os

import numpy as np

from Data_Retrieval.shared_functions import calculate_median_absolute_deviation


def add_company_to_valuation_list(
    ordered_dict: dict, exchange: str, company_code: str, industry: str
) -> None:
    file_path = (
        f"F:/Stock Analysis/Data/Fundamentals/Valuation/{exchange}/{industry}.json"
    )

    try:
        market_cap = round(float(ordered_dict["MktCap"]), 2)
        # Don't add if the market cap is under 50M
        if market_cap < 50 or np.isnan(market_cap):
            print(f"Market Cap is too small {market_cap}M, not adding to valuation")
            return
    except ValueError:
        return

    keys_cant_be_negative = [
        "P/S",
        "EV/EBITDA",
        "EV/EBIT",
        "P/TB",
        "P/B",
        "Debt/Equity",
        "Trailing P/E",
        "Forward P/E",
        "P/CFO",
        "P/FCF",
        "P/NCF",
        "P/Div",
        "P/Cash",
        "P/NCash",
    ]
    try:
        with open(file_path, "r") as json_file:
            json_data = json.load(json_file)
            existing_entry = next(
                (
                    entry
                    for entry in json_data["Companies"]
                    if entry["Code"] == company_code
                ),
                None,
            )

            if existing_entry:
                values_to_update = {}
                for key, value in ordered_dict.items():
                    if (
                        value is not None
                        and isinstance(value, (int, float))
                        and not np.isnan(value)
                        and not (key in keys_cant_be_negative and value < 0)
                    ):
                        values_to_update[key] = value
            else:
                values_to_update = update_existing_df(
                    keys_cant_be_negative, ordered_dict
                )

            if values_to_update:
                if existing_entry:
                    existing_entry.update(values_to_update)
                else:
                    json_data["Companies"].append(values_to_update)

        with open(file_path, "w") as json_file:
            json.dump(json_data, json_file, indent=2)

    except FileNotFoundError:
        print(f"File not found: {file_path}, creating a new file.")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(
            os.path.dirname(script_dir), f"Data/Fundamentals/Valuation/{exchange}"
        )
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, "w") as json_file:
            values_to_update = update_existing_df(keys_cant_be_negative, ordered_dict)

            if values_to_update:
                json.dump({"Companies": [values_to_update]}, json_file, indent=2)


def update_existing_df(keys_cant_be_negative: list, ordered_dict: dict):
    values_to_update = {"Code": ordered_dict["Code"]}
    for key, value in ordered_dict.items():
        if (
            value is not None
            and isinstance(value, (int, float))
            and not np.isnan(value)
            and not (key in keys_cant_be_negative and value < 0)
        ):
            values_to_update[key] = value

    return values_to_update


def return_mean_std_industry_valuations(exchange: str, industry: str) -> dict:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(
        os.path.dirname(script_dir),
        f"Data/Fundamentals/Valuation/{exchange}/{industry}.json",
    )
    try:
        with open(file_path, "r") as json_file:
            # Parse the JSON data
            json_data = json.load(json_file)

            # Initialize dictionaries to accumulate values
            keys = [
                "Price",
                "MktCap",
                "EV",
                "Revenue",
                "Div Yield",
                "P/S",
                "EV/EBITDA",
                "EV/EBIT",
                "P/B",
                "P/TB",
                "Debt/Equity",
                "Trailing P/E",
                "Forward P/E",
                "PEG 3yr",
                "P/CFO",
                "P/FCF",
                "P/Div",
                "P/Cash",
                "P/NCash",
                "P/NN",
                "Interest Cov",
                "Service Cov",
                "Asset Cov",
            ]
            numeric_data = {key: [] for key in keys}

            for company in json_data["Companies"]:
                for key, value in company.items():
                    if (
                        isinstance(value, float)
                        and not np.isnan(value)
                        and key in numeric_data
                    ):
                        # Update numeric data for each key
                        numeric_data[key].append(value)

            # Calculate median and Median Absolute Deviation (MAD) based on accumulated values
            filtered_data = {
                key: [
                    item
                    for item in numeric_data[key]
                    if isinstance(item, (int, float)) and not np.isnan(item)
                ]
                for key in numeric_data
                if numeric_data[key]
            }

            median_values = {
                key: round(np.median(filtered_data[key]), 2) for key in filtered_data
            }
            mad_values = {
                key: round(
                    calculate_median_absolute_deviation(np.array(filtered_data[key])), 2
                )
                for key in filtered_data
            }

            # Save median and MAD into another dictionary
            result_dict = {"Median": median_values, "MAD": mad_values}

    except FileNotFoundError:
        return {}

    script_dir = os.path.dirname(os.path.abspath(__file__))
    result_file_path = os.path.join(
        os.path.dirname(script_dir),
        f"Data/Fundamentals/Valuation/{exchange}/{industry}_Average.json",
    )
    with open(result_file_path, "w") as result_file:
        json.dump(result_dict, result_file)

    return result_dict


def print_industry_averages(exchange: str, industry: str) -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(
        os.path.dirname(script_dir),
        f"Data/Fundamentals/Valuation/{exchange}/{industry}_Average.json",
    )

    try:
        with open(file_path, "r") as json_file:
            json_data = json.load(json_file)
            print("Mean")
            print(json.dumps(json_data["Mean"], indent=4))
            print("Std Deviation")
            print(json.dumps(json_data["StdDev"], indent=4))

    except FileNotFoundError:
        print(f"File not found: {file_path}")
