from datetime import datetime, timedelta
from io import BytesIO
import logging
import logging.config
import zipfile
from zoneinfo import ZoneInfo

import pandas as pd
import requests


logger = logging.getLogger(__name__)

tz = ZoneInfo("Europe/Madrid")

def get_indexed_tariffs_cost(past_days) -> pd.DataFrame:

    # Get the current date
    current_date = datetime.now(tz=tz)
    start_date = current_date - timedelta(days=past_days)
    end_date = current_date + timedelta(days=2)

    # Replace {date} in the URL with the current date
    url = f"https://api.esios.ree.es/archives/71/download?date_type=publicacion&end_date={end_date.strftime('%Y-%m-%d')}&locale=es&start_date={start_date.strftime('%Y-%m-%d')}"
    response = requests.get(url)
    zip_content = BytesIO(response.content)

    with zipfile.ZipFile(zip_content, "r") as zip_ref:
        # Initialize an empty DataFrame to hold all data
        all_data = pd.DataFrame()

        # Read each .xls file directly from the zip
        for file_name in zip_ref.namelist():
            if not file_name.endswith(".xls"):
                continue

            with zip_ref.open(file_name) as file:
                # Read the .xls file into a DataFrame
                df = pd.read_excel(
                    file, sheet_name="Tabla de Datos PCB", engine="xlrd", skiprows=4
                )

                # Extract the relevant columns based on the provided ranges
                NUM_HOURS = 24
                date = df.iloc[:NUM_HOURS, 0].reset_index(drop=True)  # Column A
                hour = df.iloc[:NUM_HOURS, 1].reset_index(drop=True)  # Column B
                omiep = df.iloc[:NUM_HOURS, 26].reset_index(drop=True)  # Column AA
                cmp = df.iloc[:NUM_HOURS, 20].reset_index(drop=True)  # Column U
                rcp = df.iloc[:NUM_HOURS, 10].reset_index(drop=True)  # Column K
                atr = df.iloc[:NUM_HOURS, 5].reset_index(drop=True)  # Column F
                pvpc = df.iloc[:NUM_HOURS, 4].reset_index(drop=True)  # Column E

                # Combine the extracted columns into a new DataFrame
                data = pd.DataFrame(
                    {
                    'Date': date.dt.tz_localize(tz=tz) + pd.to_timedelta(hour-1, unit='h'),
                        "OMIEp": omiep,
                        "CMp": cmp,
                        "RCp": rcp,
                        "ATR": atr,
                        "PVPC": pvpc,
                    }
                )
                all_data = pd.concat([all_data, data], ignore_index=True)

    all_data.set_index("Date", inplace=True)

    PRedp = 0.0521
    COSTE_GESTION = 0.005 * 1000.0  # €/MWh
    M = 0.000255

    all_data["Flexi"] = (
        all_data["OMIEp"]
        + all_data["CMp"]
        + all_data["RCp"]
        + all_data["ATR"]
        + PRedp
        + COSTE_GESTION
        + M
    ) / 1000.0
    all_data["PVPC"] = all_data["PVPC"] / 1000.0

    def calc_solar(row):
        price = row["Flexi"] - COSTE_GESTION / 1000.0
        if 10 <= row.name.hour < 16:
            price /= 2.0
        return price

    all_data["Solar"] = all_data.apply(calc_solar, axis=1)

    return all_data[["Flexi", "Solar", "PVPC"]]


def get_data():
    LAST_DAYS = 2
    tariffs_cost = get_indexed_tariffs_cost(LAST_DAYS)

    return tariffs_cost.to_dict(orient="index")