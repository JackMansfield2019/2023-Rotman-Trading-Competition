import requests
API_KEY = {'X-API-key': ''}
# returns bid and ask first row for a given sec
def ticker_bid_ask(sessions, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price'], book['asks'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

def ticker_bid(sessions, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

def ticker_ask(sessions, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['asks'][0]['price']
    raise ApiException('Authorization error Please Check API Key')