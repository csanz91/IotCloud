import requests
from datetime import datetime, timedelta
from cache import cache_disk, clear_cache


@cache_disk(seconds=300)
def getCurrentPrice():

    response = requests.get("https://api.coindesk.com/v1/bpi/currentprice/EUR.json")
    decodedResponse = response.json()
    price = decodedResponse["bpi"]["EUR"]["rate"]
    return float(price.replace(",", ""))


@cache_disk(seconds=300)
def getHistoricalPrice():
    today = datetime.now()
    weekAgo = today - timedelta(days=6)

    def formatDatetime(dt):
        return dt.strftime("%Y-%m-%d")

    params = {
        "currency": "EUR",
        "start": formatDatetime(weekAgo),
        "end": formatDatetime(today),
    }

    response = requests.get(
        "https://api.coindesk.com/v1/bpi/historical/close.json", params=params
    )
    decodedResponse = response.json()
    try:
    	prices = decodedResponse["bpi"]
    except KeyError:
        prices = {}
    sortedDates = sorted(prices)

    sortedPrices = [prices[date] for date in sortedDates]

    currentPrice = getCurrentPrice()
    sortedPrices.append(currentPrice)

    return sortedPrices
