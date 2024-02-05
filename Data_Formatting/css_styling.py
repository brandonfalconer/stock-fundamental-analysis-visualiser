def individual_company_table_css(number_years: int) -> str:
	time_series_table_width = 100
	align = ''
	if number_years < 5:
		time_series_table_width = 40
		align = 'margin: 0 auto'
	elif number_years < 10:
		time_series_table_width = 60
		align = 'margin: 0 auto'

	return f"""
		<style>
			table {{
				border-collapse: collapse;
				width: 100%;
			}}
			th, td {{
				text-align: center;
				border-bottom: 1px solid #d9d9d9; # light grey
			}}
			td {{
				border-right: 1px solid #d9d9d9;
			}}
			th {{
				background-color: #f0f4f5;
			}}
		
			tbody > tr > th {{
			  background: #fcfeff;
			}}
			
			tbody > tr > th,
			tbody > tr {{
			  text-align: left !important;
			}}
			thead > tr, th {{
				text-align: center !important;
			}}
			tbody > tr > td:first-child,
			thead > tr > th:first-child {{
			  width: 230px;
			}}
			
			.valuation-table {{
				table {{
				  width: 100%;
				  table-layout: fixed;
				}}
				
				th, td {{
				  width: 4.54%;
				}}
			}}
			
			.time-series {{
				width: {time_series_table_width}% !important;
				{align};
			}}
			
			.earnings-table {{
		 		width: 50%;
				margin: 0 auto;
			}}
			
			.highlight-table {{
				thead > tr > th:first-child {{
				  width: 150px;
				}}
			}}
			.highlight-table tr:nth-child(1) td,
			.highlight-table tr:nth-child(1) th,
			.highlight-table tr:nth-child(4) td,
			.highlight-table tr:nth-child(4) th,
			.highlight-table tr:nth-child(8) td,
			.highlight-table tr:nth-child(8) th,
			.highlight-table tr:nth-child(14) td,
			.highlight-table tr:nth-child(14) th,
			.highlight-table tr:nth-child(15) td,
			.highlight-table tr:nth-child(15) th,
			.highlight-table tr:nth-child(23) td,
			 .highlight-table tr:nth-child(23) th {{
				border-bottom: 2px solid dimgray;
			}}
		
			.highlight-table tr td:last-child,
			.highlight-table tr th:last-child {{
			  border-left: 2px solid dimgray;
			  border-right: 2px solid dimgray;
			}}
		
			.Balance_Sheet-table tr:nth-child(7) td,
			.Balance_Sheet-table tr:nth-child(7) th,
			.Balance_Sheet-table tr:nth-child(15) td,
			.Balance_Sheet-table tr:nth-child(15) th,
			.Balance_Sheet-table tr:nth-child(28) td,
			.Balance_Sheet-table tr:nth-child(28) th,
			.Balance_Sheet-table tr:nth-child(37) td,
			.Balance_Sheet-table tr:nth-child(37) th {{
				border-bottom: 2px solid dimgray;
			}}
			.Balance_Sheet-table tr:nth-child(6) td,
			.Balance_Sheet-table tr:nth-child(6) th,
			.Balance_Sheet-table tr:nth-child(14) td,
			.Balance_Sheet-table tr:nth-child(14) th,
			.Balance_Sheet-table tr:nth-child(27) td,
			.Balance_Sheet-table tr:nth-child(27) th,
			.Balance_Sheet-table tr:nth-child(36) td,
			.Balance_Sheet-table tr:nth-child(36) th {{
				border-bottom: 1px solid dimgray;
			}}
			.Balance_Sheet-table tr td:last-child,
			.Balance_Sheet-table tr th:last-child {{
			  border-left: 2px solid dimgray;
			  border-right: 2px solid dimgray;
			}}
			
			.Income_Statement-table tr:nth-child(1) td,
			.Income_Statement-table tr:nth-child(1) th,
			.Income_Statement-table tr:nth-child(3) td,
			.Income_Statement-table tr:nth-child(3) th,
			.Income_Statement-table tr:nth-child(8) td,
			.Income_Statement-table tr:nth-child(8) th,
			.Income_Statement-table tr:nth-child(16) td,
			.Income_Statement-table tr:nth-child(16) th {{
				border-bottom: 2px solid dimgray;
			}}
			.Income_Statement-table tr:nth-child(7) td,
			.Income_Statement-table tr:nth-child(7) th,
			.Income_Statement-table tr:nth-child(15) td,
			.Income_Statement-table tr:nth-child(15) th {{
				border-bottom: 1px solid dimgray;
			}}
			.Income_Statement-table tr td:last-child,
			.Income_Statement-table tr th:last-child {{
			  border-left: 2px solid dimgray;
			  border-right: 2px solid dimgray;
			}}
		
			.Cash_Flow-table tr:nth-child(7) td,
			.Cash_Flow-table tr:nth-child(7) th,
			.Cash_Flow-table tr:nth-child(11) td,
			.Cash_Flow-table tr:nth-child(11) th,
			.Cash_Flow-table tr:nth-child(12) td,
			.Cash_Flow-table tr:nth-child(12) th,
			.Cash_Flow-table tr:nth-child(25) td,
			.Cash_Flow-table tr:nth-child(25) th,
			.Cash_Flow-table tr:nth-child(27) td,
			.Cash_Flow-table tr:nth-child(27) th {{
				border-bottom: 2px solid dimgray;
			}}
			.Cash_Flow-table tr:nth-child(6) td,
			.Cash_Flow-table tr:nth-child(6) th,
			.Cash_Flow-table tr:nth-child(10) td,
			.Cash_Flow-table tr:nth-child(10) th,
			.Cash_Flow-table tr:nth-child(24) td,
			.Cash_Flow-table tr:nth-child(24) th {{
				border-bottom: 1px solid dimgray;
			}}
			.Cash_Flow-table tr td:last-child,
			.Cash_Flow-table tr th:last-child {{
			  border-left: 2px solid dimgray;
			  border-right: 2px solid dimgray;
			}}
		
		</style>
		"""
