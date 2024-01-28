INDIVIDUAL_COMPANY_TABLE_STYLE = """
<style>
	table {
		border-collapse: collapse;
		width: 100%;
	}
	th, td {
		text-align: center;
		border-bottom: 1px solid #d9d9d9; # light grey
	}
	td {
		border-right: 1px solid #d9d9d9;
	}
	th {
		background-color: #f2f2f2;
	}
	.highlight-table tr:nth-child(1) td,
	.highlight-table tr:nth-child(4) td,
	.highlight-table tr:nth-child(10) td,
	.highlight-table tr:nth-child(14) td,
	.highlight-table tr:nth-child(23) td {
		border-bottom: 1px solid dimgray;
	}
	.highlight-table tr:nth-child(1) td {
		border-top: 1px solid dimgray;
	}

	.Balance_Sheet-table tr:nth-child(5) td,
	.Balance_Sheet-table tr:nth-child(10) td,
	.Balance_Sheet-table tr:nth-child(12) td,
	.Balance_Sheet-table tr:nth-child(17) td,
	.Balance_Sheet-table tr:nth-child(22) td,
	.Balance_Sheet-table tr:nth-child(24) td,
	.Balance_Sheet-table tr:nth-child(27) td,
	.Balance_Sheet-table tr:nth-child(31) td {
		border-bottom: 2px solid dimgray;
	}
	.Balance_Sheet-table tr:nth-child(4) td,
	.Balance_Sheet-table tr:nth-child(9) td,
	.Balance_Sheet-table tr:nth-child(16) td,
	.Balance_Sheet-table tr:nth-child(21) td {
		border-bottom: 1px solid DimGray;
	}

	.Income_Statement-table tr:nth-child(8) td,
	.Income_Statement-table tr:nth-child(16) td {
		border-bottom: 2px solid dimgray;
	}
	.Income_Statement-table tr:nth-child(7) td,
	.Income_Statement-table tr:nth-child(15) td {
		border-bottom: 1px solid dimgray;
	}

	.Cash_Flow-table tr:nth-child(5) td,
	.Cash_Flow-table tr:nth-child(9) td,
	.Cash_Flow-table tr:nth-child(19) td {
		border-bottom: 2px solid dimgray;
	}
	.Cash_Flow-table tr:nth-child(4) td,
	.Cash_Flow-table tr:nth-child(8) td,
	.Cash_Flow-table tr:nth-child(18) td {
		border-bottom: 1px solid dimgray;
	}

</style>
"""