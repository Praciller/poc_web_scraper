import pandas as pd
from logger import logger

def save_summaries_to_files(df, base_filename):
    """
    Saves the summary data to two files:
      1) base_filename.csv
      2) base_filename.xlsx
    Example: base_filename="output/summarized_data" =>
      "output/summarized_data.csv" + ".xlsx"
    """
    csv_file = f"{base_filename}.csv"
    xlsx_file = f"{base_filename}.xlsx"

    df.to_csv(csv_file, index=False, encoding="utf-8")
    logger.info(f"[console.log] Data saved to CSV: {csv_file}")

    df.to_excel(xlsx_file, index=False)
    logger.info(f"[console.log] Data saved to Excel: {xlsx_file}")
