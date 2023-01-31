
# returns bid and ask first row for a given sec
def ticker_bid_ask(sessions, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price'], book['asks'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

# returns info about all open sell orders
def open_sells(session):
    resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
    if resp.ok:
        open_sells_volume = 0
        ids = []
        prices = []
        order_volumes = []
        volume_filled = []

        open_orders = resp.json()
        for order in open_orders:
            if order['action'] == 'SELL':
                volume_filled.append(order['quantity_filled'])
                order_volumes.append(order['quantity'])
                open_sells_volume = open_sells_volume + order['quantity']
                prices.append(order['price'])
                ids.append(order['order_id'])
    return volume_filled, open_sells_volume, ids, prices, order_volumes

# returns info about all open buy orders
def open_buys(session):
    resp = session.get('http://localhost:9999/v1/orders?status=OPEN')
    if resp.ok:
        open_buys_volume = 0
        ids = []
        prices = []
        order_volumes = []
        volume_filled = []

        open_orders = resp.json()
        for order in open_orders:
            if order['action'] == 'BUY':
                volume_filled.append(order['quantity_filled'])
                order_volumes.append(order['quantity'])
                open_buys_volume = open_buys_volume + order['quantity']
                prices.append(order['price'])
                ids.append(order['order_id'])
    return volume_filled, open_buys_volume, ids, prices, order_volumes

# buys and sells maximum number of shares
def buy_sell(session, sell_price, buy_price):
    for i in range(MAX_ORDERS):
        session.post('http://localhost:9999/v1/orders', params = {'ticker':'ALGO',
        'type': 'LIMIT', 'quantity': MAX_VOLUME 'price': sell_price, 'action': 'SELL'})
        session.post('http://localhost:9999/v1/orders', params = {'ticker': 'ALGO',
        'type': 'LIMIT', 'quantity': MAX_VOLUME, 'price': buy_price, 'action': 'BUY'})
