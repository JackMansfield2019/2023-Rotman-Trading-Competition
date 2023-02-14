#from Starter_code import api_get, api_delete, api_post
import requests
import json
from time import sleep
import numpy as np
import sys
import signal
import requests

class ApiException(Exception):
    pass

# handles shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    shutdown = True

# set API key to authenticate to the RIT client
API_KEY = {'X-API-key': '0HKYGOCC'}
shutdown = False

# SETTINGS
SPEEDBUMP = 0.5
MAX_VOLUME = 5000
MAX_ORDERS = 5
SPREAD = 0.5

# returns the current 'tick' of the running case
def get_tick(session):
    resp = session.get('https://flserver.rotman.utoronto.ca:16615/v1/case')
    case = resp.json()
    return case['tick']
    raise ApiException('Authorization error Please check API key.')

# returns bid and ask first row for a given sec
def ticker_bid_ask(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('https://flserver.rotman.utoronto.ca:16615/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price'], book['asks'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

def ticker_bid(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('https://flserver.rotman.utoronto.ca:16615/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

def ticker_ask(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('https://flserver.rotman.utoronto.ca:16615/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['asks'][0]['price']
    raise ApiException('Authorization error Please Check API Key')

def unwinding_algo_simulation(number_of_shares, time_to_sell):
    k = number_of_shares
    T = time_to_sell
    pass

def almgren_chriss_optimal_execution(number_of_shares, time_to_sell_by, intervals):
    X = number_of_shares
    T = time_to_sell_by
    N = intervals
    t_ = T/N 
    k = [i for i in range(0,N)]
    t = [k[i]*t_ for i in range(0,N)]
    # number of unites to hold at time t_k; x_0 = X, x_N = 0
    x = np.zeros(N)
    x[0] = X
    x[-1] = 0
    #x = [X, 0] # number of unites to hold at time t_k; x_0 = X, x_N = 0
    S = None # security price

# returns info about all open sell orders
def open_sells(session):
    resp = session.get('https://flserver.rotman.utoronto.ca:16615/v1/orders?status=OPEN')
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
    resp = session.get('https://flserver.rotman.utoronto.ca:16615/v1/orders?status=OPEN')
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
        session.post('https://flserver.rotman.utoronto.ca:16615/v1/orders', params = {'ticker':'BULL','type': 'LIMIT', 'quantity': MAX_VOLUME, 'price': sell_price, 'action': 'SELL'})
        session.post('https://flserver.rotman.utoronto.ca:16615/v1/orders', params = {'ticker': 'BULL','type': 'LIMIT', 'quantity': MAX_VOLUME, 'price': buy_price, 'action': 'BUY'})

# buys/sells a specified quantity of shares of a specified ticker
def submit_order(session, ticker, type_, quantity, action, price):
    if type_ == 'MARKET':
        mkt_params = {'ticker': ticker, 'type': type_, 'quantity': quantity, 'action': action}
        resp = session.post('https://flserver.rotman.utoronto.ca:16615/v1/orders', params=mkt_params)
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
        resp = session.post('https://flserver.rotman.utoronto.ca:16615/v1/orders', params=mkt_params)
        if resp.ok:
            mkt_order = resp.json()
            id = mkt_order['order_id']
            print('The limit ' + action + ' order was submitted and has ID: ' + str(id))
            return id
        else:
            print('The order was not successfully submitted!')
            return None

def delete_order(session, order_id):
    resp = session.delete('https://flserver.rotman.utoronto.ca:16615/v1/orders/{}'.format(order_id))
    if resp.ok:
        status = resp.json()
        success = status['success']
        print('The order was successfully cancelled: ' + str(success))
    else:
        print('The order was unsuxxessfully cancelled.')

# method re-orders all open buys or sells
def re_order(session, number_of_orders, ids, volumes_filled, volumes, price, action):
    for i in range(number_of_orders):
        id = ids[i]
        volume = volumes[i]
        volume_filled = volumes_filled[i]
        #if order is partially filled
        if volume_filled != 0:
            volume = MAX_VOLUME - volume_filled
        
        # delete then re-purchase
        deleted = session.delete('https://flserver.rotman.utoronto.ca:16615/v1/orders/{}'.format(id))
        if deleted.ok:
            session.post('https://flserver.rotman.utoronto.ca:16615/v1/orders', params = {'ticker':'BULL', 'type': 'LIMIT', 'quantity': volume, 'price': price, 'action': action})

def main():
    # instantiate variables about all the open buy orders
    buy_ids = []                # order ids
    buy_prices = []             # order prices
    buy_volumes = []            # order volumes
    volume_filled_buys = []     # amount of volume filled for each order
    open_buys_volume = 0        # combined volume from all open buy orders

    # instantiate variables about all the open sell orders
    sell_ids = []
    sell_prices = []
    sell_volumes = []
    volume_filled_sells = []
    open_sells_volume = 0

    # instantiated variables when just one side of the book has been completely filled
    single_side_filled = False
    single_side_transaction_time = 0

    # creates a session to manage connections and requests to the RIT Client
    with requests.Session() as s:
        s.headers.update(API_KEY)
        tick = get_tick(s)

        # while the time is between 5 and 295, do the following
        while tick > 5 and tick < 295 and not shutdown:
            # update information about the case
            volume_filled_sells, open_sells_volumne, sell_ids, sell_prices, sell_volumes = open_sells(s)
            volume_filled_buys, open_buys_volume, buy_ids, buy_prices, buy_volumes = open_buys(s)
            bid_price, ask_price = ticker_bid_ask(s, 'BULL') # NEED TO CHANGE TICKER
            """
            # checks for tender offer
            endpoint = "tenders"
            args = None
            tender = api_get(session, endpoint, args)
            if tender:
                endpoint = "orders?"
                args = "status=OPEN"
                open_orders = api_get(session, endpoint, args)
                long_pos = sum(open_orders["action"] == "BUY")
                short_pos = sum(open_orders["action"] == "SELL")
                if sum(long_pos + short_pos) <= gross_limit and sum(long_pos - short_pos) <= net_limit:
                    profit_np = unwinding_algo_simulation()
                    profit_cp = unwinding_algo_simulation()
                    if profit_np > profit_cp:
                        endpoint = flserver.rotman.utoronto.ca + "tenders"
                        args = tender["tender_id"]
                        tender_accept_res = api_post(session, endpoint, args)
                    else:
                        endpoint = flserver.rotman.utoronto.ca + "tenders"
                        args = tender["tender_id"]
                        tender_decline_res = api_delete(session, endpoint, args)
            """
            # check if you have 0 open orders
            if open_sells_volume == 0 and open_buys_volume == 0:
                # both sides are filled now
                single_side_filled = False

                # calculate the spread between the bid and ask prices
                bid_ask_spread = ask_price - bid_price

                # set the prices
                sell_price = ask_price
                buy_price = bid_price

                # the calculated spread is greater or equal to our set spread
                if bid_ask_spread >= SPREAD:
                    # buy and sell the maximum number of shares
                    buy_sell(s, sell_price, buy_price)
                    sleep(SPEEDBUMP)
            
            # there are outstanding open orders
            else:
                # one side of the book has no open orders
                if not single_side_filled and (open_buys_volume == 0 or open_sells_volume == 0):
                    single_side_filled = True
                    single_side_transaction_time = tick
                
                # ask side has been completely filled
                if open_sells_volume == 0:
                    # current buy orders are at the top of the book
                    if buy_price == bid_price:
                        continue # next iteration of loop
                    
                    # its been more than 3 seconds since a single side has been completely filled
                    elif tick - single_side_transaction_time >= 3:
                        # calculate the potential profits you can make
                        next_buy_price = bid_price + 0.01
                        potential_profit = sell_price - next_buy_price - 0.02

                        # potential profit is greater than or equal to a cent or its been more than 6 seconds
                        if potential_profit >= 0.01 or tick - single_side_transaction_time >= 6:
                            action = 'BUY'
                            number_of_orders = len(buy_ids) # NEED TO CHANGE
                            buy_price = bid_price + 0.01
                            price = buy_price
                            ids = buy_ids
                            volumes = buy_volumes
                            volumes_filled = volume_filled_buys
                        
                            # delete buys and re-buy
                            re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action)
                            sleep(SPEEDBUMP)
                        
                # bid side has been completely filled
                elif open_buys_volume == 0:
                    # current sell orders are at the top of the book
                    if sell_price == ask_price:
                        continue # next iteration of loop
                    
                    # its been more than 3 seconds since a single side has been completely filled
                    elif tick - single_side_transaction_time >= 3:
                        # calculate the potential profit you can make
                        next_sell_price = ask_price - 0.01
                        potential_profit = next_sell_price - buy_price - 0.02

                        # potential profit is greater than or equal to a cent or its been more than 6 seconds
                        if potential_profit >= 0.01 or tick - single_side_transaction_time >= 6:
                            action = 'SELL'
                            number_of_orders = len(sell_ids) # NEED TO CHANGE
                            sell_price = ask_price - 0.01
                            price = sell_price
                            ids = sell_ids
                            volumes = sell_volumes
                            volumes_filled = volume_filled_sells
                        
                        # delete sells then re-sell
                        re_order(s, number_of_orders, ids, volumes_filled, volumes, price, action)
                        sleep(SPEEDBUMP)
            
            # refresh the case time
            tick = get_tick(s)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()