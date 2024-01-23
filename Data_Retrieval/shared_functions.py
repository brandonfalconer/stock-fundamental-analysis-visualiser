import os
import requests
import json

import numpy as np
import pandas as pd
from bokeh.io import output_file, show
from bokeh.models import TableColumn, ColumnDataSource, DataTable

ALPHA_SCALE_FACTOR = 4
STD_SCALE_FACTOR = 0.75


def create_file_path(relative_path: str):
	current_directory = os.getcwd()
	return os.path.join(current_directory, relative_path)


def return_json_data(relative_path: str):
	file_path = create_file_path(relative_path)

	try:
		# Read the JSON data from the file
		with open(file_path, "r") as json_file:
			print(f'JSON data exists at location: "{file_path}"')
			json_data = json.load(json_file)
		return json_data

	except FileNotFoundError:
		print(f"File not found: {file_path}")
	except json.JSONDecodeError as e:
		print(f"Error decoding JSON in {file_path}: {e}")
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
    return 0 if denominator == 0 else numerator / denominator


def convert_none_to_zero(value):
	return 0 if pd.isna(value) else int(value)


def convert_to_numeric_divide_by_one_million(value):
	try:
		if value != '' and pd.notna(value):
			return float(value) / 1000000
		return value
	except (ValueError, TypeError):
		return value


def conditionally_format(value: float, average: [np.ndarray, float], std_dev: [np.ndarray, float], large_positive=True,
						 add_percentage=False, draw_underline=False):
	try:
		z_score = (float(value) - average) / std_dev
		alpha = min(1, max(0, abs(z_score) / 2))
		# print(f'value: {value}, mean: {average}, std: {std_dev}, z_score: {z_score}, alpha: {alpha}')

		if large_positive:
			background_color = (
				f"rgba(0, 230, 0, {alpha / ALPHA_SCALE_FACTOR})" if value > average + STD_SCALE_FACTOR * std_dev
				else f"rgba(230, 0, 0, {alpha / ALPHA_SCALE_FACTOR})" if value < average - STD_SCALE_FACTOR * std_dev
				else "rgba(255, 255, 255, 0)"
			)
		else:
			background_color = (
				f"rgba(0, 230, 0, {alpha / ALPHA_SCALE_FACTOR})" if value < average - STD_SCALE_FACTOR * std_dev
				else f"rgba(230, 0, 0, {alpha / ALPHA_SCALE_FACTOR})" if value > average + STD_SCALE_FACTOR * std_dev
				else "rgba(255, 255, 255, 0)"
			)

	except ValueError:
		background_color = "rgba(255, 255, 255, 0.5)"

	string_percent = '%' if add_percentage else ''
	draw_underline = 'border-bottom: 1px solid black;' if draw_underline else ''
	try:
		if add_percentage:
			value = round(float(value))
		else:
			value = round(float(value), 2)
	except ValueError:
		pass
	return f'<div style="background: {background_color}; color: black; font-weight: bold; {draw_underline}">{value}{string_percent}</div>'


def format_rows(df: pd.DataFrame, rows_to_format, large_positive: bool = True, add_percentage: bool = False):
	if not rows_to_format:
		rows_to_format = df.index.to_list()

	for row in rows_to_format:
		values = []
		for cell_value in df.loc[row]:
			try:
				values.append(float(cell_value))
			except ValueError:
				continue

		average = np.mean(values)
		std_dev = np.std(values)

		df.loc[row] = df.loc[row].apply(lambda value: conditionally_format(value, average, std_dev, large_positive,
																		   add_percentage))


def format_cell(df: pd.DataFrame, column_name, average: float, std_dev: float, large_positive: bool = True,
				add_percentage: bool = False):
	df[column_name] = df[column_name].apply(lambda value: conditionally_format(value, average, std_dev, large_positive,
																			   add_percentage))


def return_mean_std_industry_valuations(exchange: str, industry: str):
	file_path = f"Data/Fundamentals/Valuation/{exchange}/{industry}.json"
	with open(file_path, "r") as json_file:
		# Parse the JSON data
		json_data = json.load(json_file)

		# Initialize dictionaries to accumulate values
		numeric_data_sum = {}
		numeric_data_count = {}

		# Iterate over each company and accumulate numeric values
		for company in json_data['Companies']:
			for key, value in company.items():
				if key == 'Dividend Yield':
					numeric_value = float(value.rstrip('%'))
					company['Dividend Yield'] = numeric_value
					numeric_data_sum[key] = numeric_data_sum.get(key, 0) + numeric_value
					numeric_data_count[key] = numeric_data_count.get(key, 0) + 1
				if isinstance(value, (int, float)):
					# Update sum and count for each numeric key
					numeric_data_sum[key] = numeric_data_sum.get(key, 0) + value
					numeric_data_count[key] = numeric_data_count.get(key, 0) + 1

		# Calculate mean and standard deviation based on accumulated values
		mean_values = {key: numeric_data_sum[key] / numeric_data_count[key] for key in numeric_data_sum}
		std_dev_values = {key: np.std([company[key] for company in json_data['Companies']]) for key in numeric_data_sum}

		# Save mean and standard deviation into another dictionary
		result_dict = {'Mean': mean_values, 'StdDev': std_dev_values}

	result_file_path = f"Data/Fundamentals/Valuation/{exchange}/{industry}_Average.json"
	with open(result_file_path, 'w') as result_file:
		json.dump(result_dict, result_file)

	return result_dict


def create_table_column(df):
	# Create TableColumn objects with specific widths
	columns = []
	for i, col in enumerate(df.columns):
		if i == 0:
			# Set a larger width for the first column, plus format
			columns.append(TableColumn(field=col, title=col, width=800))
		else:
			columns.append(TableColumn(field=col, title=col))

	column_data_source = ColumnDataSource(df)
	data_table = DataTable(source=column_data_source, columns=columns, width=1900, height=900)

	output_file(filename='Output/Individual/AU/CDA.html')
	show(data_table)
