import base64
import json
import os
from enum import Enum
from io import BytesIO

import matplotlib
import numpy as np
import pandas as pd
import requests
from bokeh.io import output_file, show
from bokeh.models import TableColumn, ColumnDataSource, DataTable

matplotlib.use("Agg")
from matplotlib import pyplot as plt

ALPHA_SCALE_FACTOR = 3
STD_SCALE_FACTOR = 0.75


class Leverage(Enum):
    highly_levered = "Highly Levered"
    levered = "Levered"
    minimally_levered = "Minimally Levered"
    not_levered = "Not Levered"


class TrafficLightColors(Enum):
    red = "rgba(245, 124, 105, 0.7)"
    yellow = "rgba(247, 234, 134, 0.7)"
    green = "rgba(163, 247, 156, 0.7)"


def create_file_path(relative_path: str):
    current_directory = os.getcwd()
    return os.path.join(current_directory, relative_path)


def return_json_data(relative_path: str):
    file_path = create_file_path(relative_path)

    try:
        # Read the JSON data from the file
        with open(file_path, "r") as json_file:
            print(f'JSON data exists at location: "{relative_path}"')
            json_data = json.load(json_file)
        return json_data

    except FileNotFoundError:
        print(f"File not found: {relative_path}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {relative_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # Return None in case of any error
    return None


def save_response_to_file(url: str, file_path: str):
    if os.path.exists(file_path):
        return return_json_data(file_path)

    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        json_data = response.json()

        # Create directories if they don't exist
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Write the JSON data to the file
        with open(file_path, "w") as json_file:
            json.dump(json_data, json_file)

        print(f'JSON data has been saved to "{file_path}"')
        return json_data
    else:
        print(f"Failed to retrieve data. Status code: {response.status_code}")
        return None


def handle_divide_by_zero(numerator, denominator):
    if denominator == 0 or denominator is None:
        return None
    else:
        if numerator is None:
            return None
        else:
            return numerator / denominator


def handle_divide_by_zero_series(numerator, denominator):
    return np.where(denominator != 0, numerator / denominator, 0)


def convert_none_to_zero(value):
    return 0 if pd.isna(value) else int(value)


def convert_to_numeric_divide_by_one_million(value):
    try:
        if value != "" and pd.notna(value):
            return float(value) / 1000000
        return value
    except (ValueError, TypeError):
        return value


def convert_to_percentage(value):
    try:
        if value != "" and pd.notna(value):
            return float(value) * 100
        return value
    except (ValueError, TypeError):
        return value


def calculate_median_absolute_deviation(data):
    median = np.median(data)
    mad = np.median(np.abs(data - median))
    return mad


def format_bold(value):
    """Formats all values in bold."""
    return f'<div style="font-weight: bold;">{value:.2f}</div>'


def conditionally_format(
    value: float,
    average: [np.ndarray, float, None],
    std_dev: [np.ndarray, float, None],
    large_positive=True,
    add_percentage=False,
    draw_underline=False,
    red_negative=False,
    dont_round=False,
) -> str:
    try:
        # print(f'value: {value}, mean: {average}, std: {std_dev}, z_score: {z_score}, alpha: {alpha}')

        if red_negative and value < 0:
            background_color = "rgba(255, 0, 0, 0.5)"
        else:
            if average is not None and std_dev is not None:
                z_score = (float(value) - average) / std_dev
                alpha = min(1, max(0, abs(z_score) / 2))
                if large_positive:
                    background_color = (
                        f"rgba(0, 230, 0, {alpha / ALPHA_SCALE_FACTOR})"
                        if value > average + STD_SCALE_FACTOR * std_dev
                        else (
                            f"rgba(230, 0, 0, {alpha / ALPHA_SCALE_FACTOR})"
                            if value < average - STD_SCALE_FACTOR * std_dev
                            else "rgba(255, 255, 255, 0)"
                        )
                    )
                else:
                    background_color = (
                        f"rgba(0, 230, 0, {alpha / ALPHA_SCALE_FACTOR})"
                        if value < average - STD_SCALE_FACTOR * std_dev
                        else (
                            f"rgba(230, 0, 0, {alpha / ALPHA_SCALE_FACTOR})"
                            if value > average + STD_SCALE_FACTOR * std_dev
                            else "rgba(255, 255, 255, 0)"
                        )
                    )
            else:
                background_color = "rgba(0, 0, 0, 00)"

    except (TypeError, ValueError):
        background_color = "rgba(255, 255, 255, 0.5)"

    string_percent = "%" if add_percentage else ""
    draw_underline = "border-bottom: 1px solid black;" if draw_underline else ""
    try:
        if add_percentage and not dont_round:
            value = round(float(value))
        else:
            value = round(float(value), 2)
    except (TypeError, ValueError, OverflowError):
        return f'<div style="background: {background_color}; color: black; font-weight: bold; {draw_underline}"></div>'

    return f'<div style="background: {background_color}; color: black; font-weight: bold; {draw_underline}">{value:,}{string_percent}</div>'


def format_leverage(value: float) -> str:
    """
    Applies a traffic light color scale to leverage values.
    - Green: Not Levered
    - Yellow: Minimally/Somewhat Levered
    - Red: Highly Levered
    """
    if isinstance(value, str):
        if value == Leverage.highly_levered.value:
            background_color = TrafficLightColors.red.value
        elif (
            value == Leverage.levered.value or value == Leverage.minimally_levered.value
        ):
            background_color = TrafficLightColors.yellow.value
        else:
            background_color = TrafficLightColors.green.value
        return f'<div style="background: {background_color}; color: black; font-weight: bold;">{value}</div>'
    else:
        if value > 1.5:
            background_color = TrafficLightColors.red.value
        elif value > 0.8:
            background_color = TrafficLightColors.yellow.value
        else:
            background_color = TrafficLightColors.green.value
        return f'<div style="background: {background_color}; color: black; font-weight: bold;">{value:.2f}</div>'


def format_leverage_df(df: pd.DataFrame) -> None:
    """
    Formats the leverage DataFrame with conditional traffic light formatting.
    """
    df["Blended Leverage Score"] = df["Blended Leverage Score"].apply(format_leverage)
    df["Leverage Category"] = df["Leverage Category"].apply(format_leverage)

    for col in df.columns:
        if col not in ["Blended Leverage Score", "Leverage Category"]:
            df[col] = df[col].apply(format_bold)


def format_rows(
    df: pd.DataFrame, rows_to_format, large_positive: bool = True, add_percentage=False
) -> None:
    if not rows_to_format:
        rows_to_format = df.index.to_list()

    for row in rows_to_format:
        values = []
        try:
            for cell_value in df.loc[row]:
                try:
                    if cell_value is not None:
                        values.append(float(cell_value))
                except ValueError:
                    # Float can't be converted
                    continue
        except KeyError:
            # Row has already been removed before we got here, continue
            continue

        if not values:
            continue

        average = np.mean(values)
        std_dev = np.std(values)

        df.loc[row] = df.loc[row].apply(
            lambda value: conditionally_format(
                value,
                average,
                std_dev,
                large_positive=large_positive,
                add_percentage=add_percentage,
            )
        )


def format_cell(
    df: pd.DataFrame,
    column_name,
    average: (float, None),
    std_dev: (float, None),
    large_positive: bool = True,
    add_percentage: bool = False,
    red_negative=False,
    dont_round=False,
) -> None:
    df[column_name] = df[column_name].apply(
        lambda value: conditionally_format(
            value,
            average,
            std_dev,
            large_positive=large_positive,
            add_percentage=add_percentage,
            red_negative=red_negative,
            dont_round=dont_round,
        )
    )


def create_table_column(df: pd.DataFrame):
    # Create TableColumn objects with specific widths
    columns = []
    for i, col in enumerate(df.columns):
        if i == 0:
            # Set a larger width for the first column, plus format
            columns.append(TableColumn(field=col, title=col, width=800))
        else:
            columns.append(TableColumn(field=col, title=col))

    column_data_source = ColumnDataSource(df)
    data_table = DataTable(
        source=column_data_source, columns=columns, width=1900, height=900
    )

    output_file(filename="Output/Individual/AU/CDA.html")
    show(data_table)


def create_pie_chart(df: pd.DataFrame, components: list[str]) -> (str, None):
    component_values = [df.loc[component] for component in components]
    component_values_as_floats = [
        abs(float(value)) if value.any() else 0.0 for value in component_values
    ]
    if all(value == 0.0 for value in component_values_as_floats):
        # All values are 0, a pie chart can't be created
        return None

    total = sum(component_values_as_floats)
    components = [
        (
            component
            if component in df.index
            and df.loc[component].iloc[0] != ""
            and (float(df.loc[component]) / total * 100) > 2.5
            else ""
        )
        for component in components
    ]

    fig, ax = plt.subplots()
    autopct = lambda pct: "{:1.1f}%".format(pct) if pct > 2.5 else ""

    colors = [
        "#c4e6a5",
        "#8099ff",
        "#DD7596",
        "#8EB897",
        "#f5eaab",
        "#f79797",
        "#d499e8",
        "#96e9fa",
    ]
    ax.pie(
        component_values_as_floats,
        labels=components,
        autopct=autopct,
        startangle=90,
        colors=colors,
    )
    ax.axis("equal")
    img_buffer = BytesIO()
    plt.savefig(img_buffer, bbox_inches="tight")
    img_buffer.seek(0)

    # Convert the image to base64
    img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")

    plt.close(fig)
    return img_base64


def validate_ticker(company: str, exchange: str) -> (str, bool):
    code = company["Code"]

    if not code:
        print(f"Couldn't find company code for {code}")
        return False

    if company["Type"] != "Common Stock":
        print(f"{code} is not a common stock")
        return False

    # if company["Exchange"] != exchange:
    #     print(f"{code} is not on exchange {exchange}")
    #     return False

    # eodhd has no data for LGI, GLACR
    if code == "LGI" or code == "GLACR":
        return False

    return True


def calculate_market_cap(company_dict: dict, price: float) -> float:
    try:
        shares_outstanding = company_dict["SharesStats"]["SharesOutstanding"]
        if shares_outstanding is None or shares_outstanding == 0:
            if company_dict["outstandingShares"]["annual"]:
                shares_outstanding = company_dict["outstandingShares"]["annual"]["0"][
                    "shares"
                ]
    except KeyError:
        return 0

    return (shares_outstanding * price) / 1000000


def validate_common_stock_tickers(company_json: dict, ticker: str) -> bool:
    if not company_json:
        print(f"Could not find company data for {ticker}")
        return False

    return True


def clean_and_round_dict(data_dict):
    """
    Cleans and rounds numerical values in a dictionary:
    - Rounds float/int values to 2 decimal places.
    - Replaces NaN values with an empty string.
    - Leaves non-numeric values unchanged.

    Args:
        data_dict (dict): Dictionary with numerical and non-numerical values.

    Returns:
        dict: A new dictionary with cleaned and rounded values.
    """
    return {
        key: (
            ""
            if isinstance(value, float) and np.isnan(value)  # Replace NaN with ""
            else (
                round(value, 2)
                if isinstance(value, (float, int))  # Round numbers
                else value
            )
        )  # Leave non-numeric values unchanged
        for key, value in data_dict.items()
    }
