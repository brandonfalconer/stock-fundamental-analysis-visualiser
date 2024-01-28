from bokeh.io import show
from bokeh.models import HTMLTemplateFormatter, TableColumn, DataTable, ColumnDataSource

from Data_Retrieval.web_scraper import get_all_asx_companies

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
