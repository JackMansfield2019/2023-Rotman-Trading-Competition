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

# buys/sells a specified quantity of shares of a specified ticker
def submit_order(session, ticker, type_, quantity, action, price):
    if type_ == 'MARKET':
        mkt_params = {'ticker': ticker, 'type': type_, 'quantity': quantity, 'action': action}
        resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
        if resp.ok:
            mkt_order = resp.json()
            id = mkt_order['order_id']
            print('The market ' + action + ' order was submitted and has ID: ' + str(id))
            return id
        else:
            print('The order was not successfully submitted!')
            return None
    elif type_ == 'LIMIT':
        mkt_params = {'ticker': ticker, 'type': type_, 'quantity': quantity, 'price': price, 'action': action}
        resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
        if resp.ok:
            mkt_order = resp.json()
            id = mkt_order['order_id']
            print('The limit ' + action + ' order was submitted and has ID: ' + str(id))
            return id
        else:
            print('The order was not successfully submitted!')
            return None

def delete_order(session, order_id):
    resp = session.delete('http://localhost:9999/v1/orders/{}'.format(order_id))
    if resp.ok:
        status = resp.json()
        success = status['success']
        print('The order was successfully cancelled: ' + str(success))
    else:
        print('The order was unsuxxessfully cancelled.')
