import time
import requests
import pandas as pd
from pathlib import Path

BASE_URL = "https://api.worldbank.org/v2"

COUNTRIES = {
    "NGA": "Nigeria",
    "GHA": "Ghana",
    "KEN": "Kenya",
    "ZAF": "South Africa",
}

INDICATORS = {
    "SP.POP.TOTL": "Population",
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "SP.DYN.LE00.IN": "Life expectancy",
    "FP.CPI.TOTL.ZG": "Inflation",
    "IT.NET.USER.ZS": "Internet users",
    "SL.UEM.TOTL.ZS": "Unemployment",
}

def fetch_indicator(country_code, indicator_code, max_retries=3):
    url = f"{BASE_URL}/country/{country_code}/indicator/{indicator_code}"

    params = {
        "format": "json",
        "per_page": 100,
        "date": "1960:2026",
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=60,
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as error:
            print(
                f"Request failed "
                f"(attempt {attempt}/{max_retries}): {error}"
            )

            if attempt < max_retries:
                wait_time = attempt * 2
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

            else:
                print(
                    f"FAILED: {country_code} - {indicator_code}"
                )
                return None

def parse_indicator(country_code, indicator_code):
    data = fetch_indicator(country_code, indicator_code)

    if not data or len(data) < 2 or data[1] is None:
        return []

    rows = []

    for observation in data[1]:
        rows.append({
            "country": COUNTRIES[country_code],
            "country_code": country_code,
            "year": int(observation["date"]),
            "indicator": INDICATORS[indicator_code],
            "indicator_code": indicator_code,
            "value": observation["value"],
        })

    return rows

all_rows = []

for country_code in COUNTRIES:
    for indicator_code in INDICATORS:
        print(
            f"Fetching {COUNTRIES[country_code]} "
            f"- {INDICATORS[indicator_code]}..."
        )

        rows = parse_indicator(country_code, indicator_code)
        all_rows.extend(rows)

df = pd.DataFrame(all_rows)

df = df.sort_values(
    by=["country", "indicator", "year"]
).reset_index(drop=True)

print("\nDataset shape:", df.shape)
print("\nCountries:")
print(df["country"].value_counts())

print("\nIndicators:")
print(df["indicator"].value_counts())

print("\nYear range:")
print(df["year"].min(), "-", df["year"].max())

print("\n--- DATA QUALITY AUDIT ---")

print("\nMissing values by indicator:")
print(
    df.groupby("indicator")["value"]
    .apply(lambda x: x.isna().sum())
    .sort_values(ascending=False)
)

print("\nAvailable observations by indicator:")
print(
    df.groupby("indicator")["value"]
    .count()
    .sort_values(ascending=False)
)

print("\nCoverage by country and indicator:")

coverage = (
    df.dropna(subset=["value"])
    .groupby(["country", "indicator"])
    .agg(
        first_year=("year", "min"),
        latest_year=("year", "max"),
        observations=("value", "count"),
    )
)

print(coverage.to_string())

print("\nDuplicate rows:")
print(
    df.duplicated(
        subset=["country_code", "year", "indicator_code"]
    ).sum()
)

OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_file = OUTPUT_DIR / "world_bank_indicators.csv"

df.to_csv(output_file, index=False)

print(f"\nDataset saved to: {output_file}")
print(f"Rows saved: {len(df):,}")