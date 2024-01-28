import base64
import os
import sys
from io import BytesIO

import requests
import json

import numpy as np
import pandas as pd
from bokeh.io import output_file, show
from bokeh.models import TableColumn, ColumnDataSource, DataTable
import matplotlib

matplotlib.use('Agg')
from matplotlib import pyplot as plt

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
			print(directory)

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
		if value != '' and pd.notna(value):
			return float(value) / 1000000
		return value
	except (ValueError, TypeError):
		return value


def conditionally_format(value: float, average: [np.ndarray, float], std_dev: [np.ndarray, float], large_positive=True,
						 add_percentage=False, draw_underline=False) -> str:
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

	except (TypeError, ValueError):
		background_color = "rgba(255, 255, 255, 0.5)"

	string_percent = '%' if add_percentage else ''
	draw_underline = 'border-bottom: 1px solid black;' if draw_underline else ''
	try:
		if add_percentage:
			value = round(float(value))
		else:
			value = round(float(value), 2)
	except (TypeError, ValueError):
		pass
	except OverflowError:
		pass
	return f'<div style="background: {background_color}; color: black; font-weight: bold; {draw_underline}">{value}{string_percent}</div>'


def format_rows(df: pd.DataFrame, rows_to_format, large_positive: bool = True, add_percentage: bool = False) -> None:
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

		df.loc[row] = df.loc[row].apply(lambda value: conditionally_format(value, average, std_dev, large_positive,
																		   add_percentage))


def format_cell(df: pd.DataFrame, column_name, average: float, std_dev: float, large_positive: bool = True,
				add_percentage: bool = False) -> None:
	df[column_name] = df[column_name].apply(lambda value: conditionally_format(value, average, std_dev, large_positive,
																			   add_percentage))


def add_company_to_valuation_list(ordered_dict: dict, exchange: str, company_code: str, industry: str) -> None:
	file_path = f"Data/Fundamentals/Valuation/{exchange}/{industry}.json"

	try:
		print(ordered_dict)
		market_cap = float(ordered_dict['MktCap'])
		# Don't add if the market cap is under 50M
		if market_cap < 50:
			print(f'Market Cap is too small {market_cap}M, not adding to valuation')
			return
	except ValueError:
		return

	try:
		with open(file_path, 'r') as json_file:
			json_data = json.load(json_file)
			existing_entry = next((entry for entry in json_data['Companies'] if entry['Code'] == company_code), None)
			if existing_entry:
				# Update the existing entry
				existing_entry.update(ordered_dict)
			else:
				# Append the new entry
				json_data['Companies'].append(ordered_dict)

		with open(file_path, 'w') as json_file:
			json.dump(json_data, json_file, indent=2)

	except FileNotFoundError:
		print(f"File not found: {file_path}, creating a new file.")
		with open(file_path, 'w') as json_file:
			json.dump({'Companies': [ordered_dict]}, json_file, indent=2)


def return_mean_std_industry_valuations(exchange: str, industry: str) -> dict:
	file_path = f"Data/Fundamentals/Valuation/{exchange}/{industry}.json"
	try:
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
						try:
							company['Dividend Yield'] = numeric_value
							numeric_data_sum[key] = numeric_data_sum.get(key, 0) + numeric_value
							numeric_data_count[key] = numeric_data_count.get(key, 0) + 1
						except ValueError:
							continue
					if isinstance(value, float) and not np.isnan(value):
						# Update sum and count for each numeric key
						numeric_data_sum[key] = numeric_data_sum.get(key, 0) + value
						numeric_data_count[key] = numeric_data_count.get(key, 0) + 1

			# Calculate mean and standard deviation based on accumulated values
			mean_values = {key: numeric_data_sum[key] / numeric_data_count[key] for key in numeric_data_sum}
			std_dev_values = {
				key: np.std([company[key] for company in json_data['Companies']
							 if company[key] is not None and not np.isnan(company[key])]) for key in numeric_data_sum}

			# Save mean and standard deviation into another dictionary
			result_dict = {'Mean': mean_values, 'StdDev': std_dev_values}

	except FileNotFoundError:
		return {}

	result_file_path = f"Data/Fundamentals/Valuation/{exchange}/{industry}_Average.json"
	with open(result_file_path, 'w') as result_file:
		json.dump(result_dict, result_file)

	return result_dict


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
	data_table = DataTable(source=column_data_source, columns=columns, width=1900, height=900)

	output_file(filename='Output/Individual/AU/CDA.html')
	show(data_table)


def create_pie_chart(df: pd.DataFrame, components: list[str]) -> (str, None):
	components = [component for component in components if component in df.index]
	component_values = [df.loc[component] for component in components]

	component_values_as_floats = [abs(float(value)) if value.any() else 0.0 for value in component_values]
	if all(value == 0.0 for value in component_values_as_floats):
		# All values are 0, a pie chart can't be created
		return None

	fig, ax = plt.subplots()
	autopct = lambda pct: '{:1.1f}%'.format(pct) if pct > 2.5 else ''
	colors = ['#c4e6a5', '#8099ff', '#DD7596', '#8EB897', '#f5eaab', '#f79797', '#d499e8']
	ax.pie(component_values_as_floats, labels=components, autopct=autopct, startangle=90, colors=colors)
	ax.axis('equal')
	img_buffer = BytesIO()
	plt.savefig(img_buffer, bbox_inches='tight')
	img_buffer.seek(0)

	# Convert the image to base64
	img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
	return img_base64


def validate_ticker(ticker_code: str) -> (str, None):
	# Microsoft MS-DOS had reserved these names for these system device drivers.
	# PRN : System list device, usually a parallel port
	if ticker_code == 'PRN':
		ticker_code = 'PRN_'

	# eodhd has no data for LGI
	if ticker_code == 'LGI':
		return None

	return ticker_code
