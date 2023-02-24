import requests
import json
from time import sleep
import numpy as np
import sys
import signal
import requests
import api_requests as api

#SETTINGS
SPEEDBUMP = 0.5
LAST_MINUTE_THRESHOLD = 60
MAX_ORDER_SIZE = 10000
TICKS_PER_PERIOD = 300
ORDER_BOOK_SIZE = 10000
MAX_SPREAD = 0.2


def ticker_bid(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['price']

def ticker_ask(session, ticker):
    payload = {'ticker': ticker}
    resp = session.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['asks'][0]['price']

# buys/sells a specified quantity of shares of a specified ticker
def submit_order(session, ticker, type_, quantity, action, price):
    print("In Submit Order")
    if type_ == 'MARKET':
        mkt_params = {'ticker': ticker, 'type': type_, 'quantity': quantity, 'action': action}
        resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
        if resp.ok:
            mkt_order = resp.json()
            id = mkt_order['order_id']
            print(f'The market {action} order was submitted and has ID: {id}')
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
            print(f'The limit {action} order was submitted and has ID: {id}')
            return id
        else:
            print('The order was not successfully submitted!')
            return None

def tender_buy(session, held_tenders, tender, tender_offer_prices : list):
    ticker = tender['ticker']
    tick = api.get(session, "case")["tick"]
    price_offered = float(tender['price'])
    quantity_offered = int(tender["quantity"])
    tender_id = int(tender['tender_id'])
    value_of_offer = price_offered * quantity_offered
    net_positions = api.get(session, "limits")[0]['net']
    gross_positions = api.get(session, "limits")[0]['gross']

    if net_positions + quantity_offered < api.get(session, 'limits')[0]['net_limit'] and gross_positions + quantity_offered < api.get(session, 'limits')[0]['gross_limit']:
        potential_profit = 0
        bids = api.get(session, 'securities/book', ticker = 'RITC', limit = ORDER_BOOK_SIZE)['bids']
        shares_accounted_for = 0
        bid_index = 0

        while shares_accounted_for < quantity_offered:
            shares_accounted_for += bids[bid_index]['quantity'] - bids[bid_index]['quantity_filled']
            if(shares_accounted_for > quantity_offered):
                potential_profit += bids[bid_index]['price'] * (quantity_offered - shares_accounted_for + bids[bid_index]['quantity'] - bids[bid_index]['quantity_filled'])
            else:
                potential_profit += bids[bid_index]['price'] * (bids[bid_index]['quantity'] - bids[bid_index]['quantity_filled'])
            bid_index += 1
        if TICKS_PER_PERIOD - tick < LAST_MINUTE_THRESHOLD:   
            if potential_profit > value_of_offer:
                # accept tender offer, then sell to market immediately
                api.post(session, 'tenders/' + str(tender_id))
                #order_id = submit_order(session, 'RITC', 'MARKET', quantity_offered, 'SELL', None)
                #mkt_params = {'ticker': 'RITC', 'type': 'MARKET', 'quantity': quantity_offered, 'action': 'SELL'}
                #resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
                return tender['price']
            else:
                api.delete(session, 'tenders/' + str(tender_id))
        else:
            if potential_profit > value_of_offer:
                api.post(session, 'tenders/' + str(tender_id))

                print("this is the tender offer price: " + str(tender['price']))
                return tender['price']
            else:
                api.delete(session, 'tenders/'+ str(tender_id))
    return 0

def tender_sell(session, held_tenders, tender, tender_offer_prices : list):  
    ticker = tender['ticker']
    tick = api.get(session, 'case')['tick']
    net_positions = api.get(session, "limits")[0]['net']
    gross_positions = api.get(session, "limits")[0]['gross']
    tender_id = tender['tender_id'] 
    quantity_offered = tender['quantity']
    price_offered = tender['price']
    current_position = api.get(session, 'securities', ticker = 'RITC')[0]['position']
    shares_to_be_shorted = 0

    if 0 <= current_position < quantity_offered:
        shares_to_be_shorted = quantity_offered - current_position
    elif current_position < 0:
        shares_to_be_shorted = quantity_offered
    
    shares_to_sell_instantly = quantity_offered - shares_to_be_shorted
    value_of_shorted = shares_to_be_shorted * price_offered
    instant_profit_from_sell = shares_to_sell_instantly * (price_offered - api.get(session, "securities", ticker = 'RITC')[0]['vwap'])
    
    potential_profit = 0
    if (gross_positions - current_position) + abs(current_position - quantity_offered) < api.get(session, 'limits')[0]['gross_limit']:
        if shares_to_be_shorted > 0:
            if TICKS_PER_PERIOD - tick < LAST_MINUTE_THRESHOLD:
                asks = api.get(session, 'securities/book', ticker = 'RITC', limit = ORDER_BOOK_SIZE)['asks']
                shares_accounted_for = 0
                ask_index = 0

                while shares_accounted_for < shares_to_be_shorted:
                    shares_accounted_for += asks[ask_index]['quantity'] - asks[ask_index]['quantity_filled']
                    if shares_accounted_for > quantity_offered:
                        potential_profit += asks[ask_index]['price'] * (quantity_offered - shares_accounted_for + asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"])
                    else:
                        potential_profit += asks[ask_index]["price"] * (asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"])
                    ask_index += 1
                
                potential_profit = value_of_shorted - potential_profit
                if potential_profit + instant_profit_from_sell > 0:
                    # accept tender offer, then buy at market immediately
                    api.post(session, 'tenders/' + str(tender_id))
                    #order_id = submit_order(session, 'RITC', 'MARKET', quantity_offered, 'BUY', None)
                    #mkt_params = {'ticker': 'RITC', 'type': 'MARKET', 'quantity': quantity_offered, 'action': 'BUY'}
                    #resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
                    return tender['price']
                else:
                    api.delete(session, 'tenders/' + str(tender_id))
        elif instant_profit_from_sell > 0:
            api.post(session, 'tenders/' + str(tender_id))
            #order_id = submit_order(session, 'RITC', 'MARKET', quantity_offered, 'SELL', None)
            print("this is the tender price: " + str(tender['price']))
            return tender['price']
        else:
            api.delete(session, 'tenders/' + str(tender_id))
    else:
        api.delete(session, 'tenders/' + str(tender_id))
    return 0
    

def main():
    with api.requests.Session() as session:
        session.headers.update(api.API_KEY)
        status = api.get(session, 'case')['status']
        while(status != 'ACTIVE'):
            status = api.get(session, 'case')['status']
            api.sleep(api.SPEEDBUMP)

        tick = api.get(session, "case")["tick"]
        held_tenders = []
        ticker = 'RITC'
        tender_offer_prices = []

        while status == 'ACTIVE':
            status = api.get(session, 'case')['status']
            tenders = api.get(session, 'tenders')
            for tender in tenders:
                if tender: # must check
                    print("tender received")
                    action = tender['action']
                    if action == 'BUY':
                        offer_price = tender_buy(session, held_tenders, tender, tender_offer_prices)
                        if offer_price > 0:
                            tender_offer_prices.append(offer_price)
                        print(tender_offer_prices)
                    else:
                        offer_price = tender_sell(session, held_tenders, tender, tender_offer_prices)
                        if offer_price > 0:
                            tender_offer_prices.append(offer_price)
                        print(tender_offer_prices)
            spread_ritc = 100*(api.get(session, 'securities', ticker = ticker)[0]['ask']/api.get(session, 'securities', ticker = ticker)[0]['bid'] - 1)
            size = None
            #tender_shares = api.get(session, 'securities', kwargs={'ticker': ticker})[0]['position']
            tender_shares = api.get(session, 'securities', ticker='RITC')[0]['position']
        
            if abs(tender_shares) < MAX_ORDER_SIZE:
                size = abs(tender_shares)
            else:
                size = MAX_ORDER_SIZE
            price_offered = 25
            
            if len(tender_offer_prices) > 0:
                price_offered = tender_offer_prices[-1]

            if tender_shares < 0:
                # need to buy shares
                if 0 < MAX_SPREAD: #or shares_to_sell_instantly >= shares_to_be_shorted: # less volative
                    asks = api.get(session, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                    shares_accounted_for = 0
                    ask_index = 0
                    
                    while shares_accounted_for <= size:
                        shares_accounted_for += asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"]
                        ask_index += 1

                    buy_price = asks[ask_index - 1]["price"]
                    #sell_price_to_offer = asks[ask_index - 1]["price"]
                    #potential_profit = (sell_price_to_offer - buy_price) * shares_to_be_shorted
                    #instant_profit_from_sell = 0

                    #if shares_to_sell_instantly > 0:
                        #instant_profit_from_sell = (sell_price_to_offer - api.get(s, "securities", ticker = ticker)[0]["vwap"]) * shares_to_sell_instantly
                    
                    #if instant_profit_from_sell + potential_profit > 0:
                    #order_id = submit_order(session, ticker, 'MARKET', size, 'BUY', None)
                    if buy_price < price_offered:
                        #mkt_params = {'ticker': ticker, 'type': 'MARKET', 'quantity': size, 'action': 'BUY'}
                        #resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
                        resp = api.post(session, 'orders', ticker=ticker, type='MARKET', quantity=size, action='BUY')
                '''
                    else:
                    price_data = api.get(session, "securities/history", ticker = ticker, limit = 20)
                    asks = api.get(session, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                    shares_accounted_for = 0
                    ask_index = 0
                    
                    while shares_accounted_for <= size:
                        shares_accounted_for += asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"]
                        ask_index += 1

                    buy_price = asks[ask_index - 1]["price"]
                    last_5_ticks = []
                    last_20_ticks = []
                    for i in range(0, 5):
                        last_5_ticks.append(price_data[i]["close"])
                    for i in range(0, 20):
                        last_20_ticks.append(price_data[i]["close"])

                    sma5 = sum(last_5_ticks) / len(last_5_ticks) if len(last_5_ticks) > 0 else 0
                    sma20 = sum(last_20_ticks) / len(last_20_ticks) if len(last_20_ticks) > 0 else 0
                    #if sma20 != 0 and sma5 != 0 and sma5 > sma20:
                        #if buy_price < price_offered:
                            #mkt_params = {'ticker': ticker, 'type': 'MARKET', 'quantity': size, 'action': 'BUY'}
                            #resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
                            #resp = api.post(session, 'orders', ticker=ticker, type='MARKET', quantity=size, action='BUY')'''
            elif tender_shares > 0:
                # need to sell shares
                if 0 < MAX_SPREAD:
                    bids = api.get(session, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                    shares_accounted_for = 0
                    bid_index = 0

                    while shares_accounted_for < MAX_ORDER_SIZE:
                        shares_accounted_for += bids[bid_index]['quantity'] - bids[bid_index]['quantity_filled']
                        bid_index += 1

                    sell_price = bids[bid_index - 1]["price"]
                    if sell_price > price_offered:
                        #mkt_params = {'ticker': ticker, 'type': 'MARKET', 'quantity': size, 'action': 'SELL'}
                        #resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
                        resp = api.post(session, 'orders', ticker=ticker, type='MARKET', quantity=size, action='SELL')
                
                        '''else:
                    if tick >= 20:
                        price_data = api.get(session, 'securities/history', ticker = ticker, limit = 20)
                        bids = api.get(session, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                        shares_accounted_for = 0
                        bid_index = 0

                        while shares_accounted_for < MAX_ORDER_SIZE:
                            shares_accounted_for += bids[bid_index]['quantity'] - bids[bid_index]['quantity_filled']
                            bid_index += 1

                        sell_price = bids[bid_index - 1]["price"]
                        last_5_ticks = []
                        last_20_ticks = []
                        for i in range(0, 5):
                            last_5_ticks.append(price_data[i]["close"])
                        for i in range(0, 20):
                            last_20_ticks.append(price_data[i]["close"])

                        sma5 = sum(last_5_ticks) / len(last_5_ticks) if len(last_5_ticks) > 0 else 0
                        sma20 = sum(last_20_ticks) / len(last_20_ticks) if len(last_20_ticks) > 0 else 0

                        #if sma20 != 0 and sma5 != 0 and sma5 > sma20:
                            #if sell_price > price_offered:
                                #mkt_params = {'ticker': ticker, 'type': 'MARKET', 'quantity': size, 'action': 'SELL'}
                                #resp = session.post('http://localhost:9999/v1/orders', params=mkt_params)
                                #resp = api.post(session, 'orders', ticker=ticker, type='MARKET', quantity=size, action='SELL')'''
            else:
                continue


if __name__ == '__main__':
    api.signal.signal(api.signal.SIGINT, api.signal_handler)
    main()