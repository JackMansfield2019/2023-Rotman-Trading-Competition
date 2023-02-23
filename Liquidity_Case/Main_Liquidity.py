# pip install tabulate pandas requests

import API_Requests as api
from os import system
import pandas as pd
from tabulate import tabulate
LAST_MINUTE_THRESHOLD = 60
LIQUIDITY_RATIO_THRESHOLD = 100
VOLUME_RATIO_THRESHOLD = 1.0
MAX_SPREAD = .15
TICKS_PER_PERIOD = 600
ORDER_BOOK_SIZE = 10000

def private_tender_model(s : api.requests.Session, tender_id : int):

    tender : dict = {}

    for t in api.get(s, "tenders"):
        if t["tender_id"] == tender_id:
            tender = t
            break
    
    if tender == {}:
        raise Exception("Tender not found")

    # tender_tick : int = int(tender["tick"]) # we need the current tick, not the tick when offer started
    tick : int = api.get(s, "case")["tick"] 
    ticker : str = tender["ticker"]
    price_offered : float = float(tender["price"])
    quantity_offered : int = int(tender["quantity"])
    action : str = tender["action"]
    value_of_offer : float = price_offered * quantity_offered

    net_positions : float = api.get(s, "limits")[0]['net']
    gross_positions : float = api.get(s, "limits")[0]['gross']

    if action == "BUY":
        if net_positions + quantity_offered < api.get(s, "limits")[0]['net_limit'] and gross_positions + quantity_offered < api.get(s, "limits")[0]['gross_limit']:
            if TICKS_PER_PERIOD - tick < LAST_MINUTE_THRESHOLD:

                potential_profit : float = 0
                bids = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                shares_accounted_for : int = 0
                bid_index : int = 0

                while shares_accounted_for < quantity_offered:
                    shares_accounted_for += bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"]
                    if(shares_accounted_for > quantity_offered):
                        potential_profit += bids[bid_index]["price"] * (quantity_offered - shares_accounted_for + bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"])
                    else:
                        potential_profit += bids[bid_index]["price"] * (bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"])
                    bid_index += 1

                if potential_profit > value_of_offer:
                    return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], "MKT")]
                else:
                    return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]

            else:
                # liquidity ratio no longer being used, does not seem to affect investment liquidity

                # we are no longer comparing the volumes of the bids and asks and making a vwap based limit price

                # bids_and_asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)
                
                #bid_volume : int = 0
                #for b in bids_and_asks["bids"]:
                #    bid_volume += b["quantity"] - b["quantity_filled"]
                
                #ask_volume : int = 0
                #for a in bids_and_asks["asks"]:
                #    ask_volume += a["quantity"] - a["quantity_filled"]

                bids = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                shares_accounted_for : int = 0
                bid_index : int = 0

                while shares_accounted_for < quantity_offered:
                    shares_accounted_for += bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"]
                    bid_index += 1
                
                sell_price = bids[bid_index - 1]["price"]

                spread = 100*(api.get(s, "securities", ticker = ticker)[0]["ask"]/api.get(s, "securities", ticker = ticker)[0]["bid"] - 1)

                # print("Spread: " + str(spread))

                if spread < MAX_SPREAD: # less volatile
                    if sell_price > price_offered:
                        return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], round(sell_price, 2))]
                    else:
                        # print("Sell price: " + str(sell_price) + " Offer price: " + str(price_offered))
                        return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]
                else: # volatile, but is it trending up?
                    price_data = api.get(s, "securities/history", ticker = ticker, limit = 20)
                    last_5_ticks = []
                    last_20_ticks = []
                    for i in range(0, 5):
                        last_5_ticks.append(price_data[i]["close"])
                    for i in range(0, 20):
                        last_20_ticks.append(price_data[i]["close"])

                    sma5 = sum(last_5_ticks) / len(last_5_ticks) if len(last_5_ticks) > 0 else 0
                    sma20 = sum(last_20_ticks) / len(last_20_ticks) if len(last_20_ticks) > 0 else 0

                    # print("sma5: " + str(sma5))
                    # print("sma20: " + str(sma20))

                    if sma20 != 0 and sma5 != 0 and sma5 > sma20:
                        if sell_price > price_offered:
                            return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], round(sell_price, 2))]
                        else:
                            # print("Sell price: " + str(sell_price) + " Offer price: " + str(price_offered))
                            return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]
                    else:
                        return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]
        else:
            return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]
    
    elif action == "SELL":            
        current_position : int = api.get(s, "securities", ticker = ticker)[0]["position"]

        shares_to_be_shorted : int = 0

        if 0 <= current_position < quantity_offered:
            shares_to_be_shorted = quantity_offered - current_position
        elif current_position < 0:
            shares_to_be_shorted = quantity_offered

        shares_to_sell_instantly : int = quantity_offered - shares_to_be_shorted
        value_of_shorted : float = shares_to_be_shorted * price_offered

        instant_profit_from_sell : float = shares_to_sell_instantly * (price_offered - api.get(s, "securities", ticker = ticker)[0]["vwap"])

        potential_profit : float = 0
        if (gross_positions - current_position) + abs(current_position - quantity_offered) < api.get(s, "limits")[0]["gross_limit"]:
            if shares_to_be_shorted > 0:
                if TICKS_PER_PERIOD - tick < LAST_MINUTE_THRESHOLD:
                    asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                    shares_accounted_for : int = 0
                    ask_index : int = 0

                    while shares_accounted_for < shares_to_be_shorted:
                        shares_accounted_for += asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"]
                        if(shares_accounted_for > quantity_offered):
                            potential_profit += asks[ask_index]["price"] * (quantity_offered - shares_accounted_for + asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"])
                        else:
                            potential_profit += asks[ask_index]["price"] * (asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"])
                        ask_index += 1

                    potential_profit = value_of_shorted - potential_profit

                    if potential_profit + instant_profit_from_sell > 0:
                        return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], "MKT")]
                    else:
                        return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]          
                else:
                    # liquidity_ratio : float = shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["total_volume"]
                        
                    #bids_and_asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)
                    
                    #bid_volume : int = 0
                    #for b in bids_and_asks["bids"]:
                    #    bid_volume += b["quantity"] - b["quantity_filled"]
                    
                    #ask_volume : int = 0
                    #for a in bids_and_asks["asks"]:
                    #    ask_volume += a["quantity"] - a["quantity_filled"]

                    spread = 100*(api.get(s, "securities", ticker = ticker)[0]["ask"]/api.get(s, "securities", ticker = ticker)[0]["bid"] - 1)

                    # print("Spread: " + str(spread))

                    asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                    shares_accounted_for : int = 0
                    ask_index : int = 0

                    while shares_accounted_for < shares_to_be_shorted:
                        shares_accounted_for += asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"]
                        ask_index += 1
                    
                    buy_price = asks[ask_index - 1]["price"]

                    potential_profit = value_of_shorted - shares_to_be_shorted * buy_price

                    if spread < MAX_SPREAD or shares_to_sell_instantly >= shares_to_be_shorted: # less volatile or there is a decent amount of instant profit

                        if instant_profit_from_sell + potential_profit > 0:
                            return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], round(buy_price, 2))]
                        else:
                            # print("instant profit: " + str(instant_profit_from_sell), "potential profit: " + str(potential_profit))
                            return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]
                    else:

                        price_data = api.get(s, "securities/history", ticker = ticker, limit = 20)
                        last_5_ticks = []
                        last_20_ticks = []
                        for i in range(0, 5):
                            last_5_ticks.append(price_data[i]["close"])
                        for i in range(0, 20):
                            last_20_ticks.append(price_data[i]["close"])

                        sma5 = sum(last_5_ticks) / len(last_5_ticks) if len(last_5_ticks) > 0 else 0
                        sma20 = sum(last_20_ticks) / len(last_20_ticks) if len(last_20_ticks) > 0 else 0

                        # print("sma5: " + str(sma5))
                        # print("sma20: " + str(sma20))

                        if sma20 != 0 and sma5 != 0 and sma5 < sma20:
                            if instant_profit_from_sell + potential_profit > 0:
                                return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], round(buy_price, 2))]
                            else:
                                # print("instant profit: " + str(instant_profit_from_sell), "potential profit: " + str(potential_profit))
                                return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]
                        else:
                            return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]
            elif instant_profit_from_sell > 0:
                return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[32mACCEPT\u001b[37m")]
            else:
                return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]
        else:
            return [("Private", action, ticker, quantity_offered, price_offered, "\u001b[31mREJECT\u001b[37m")]

def competitive_tender_model(s : api.requests.Session, tender_id : int):
    tender : dict = {}

    for t in api.get(s, "tenders"):
        if t["tender_id"] == tender_id:
            tender = t
            break
    
    if tender == {}:
        raise Exception("Tender not found")

    # tender_tick : int = int(tender["tick"])
    tick : int = int(api.get(s, "case")["tick"])
    ticker : str = tender["ticker"]
    quantity_offered : int = int(tender["quantity"])
    action : str = tender["action"]

    net_positions : float = api.get(s, "limits")[0]['net']
    gross_positions : float = api.get(s, "limits")[0]['gross']

    if action == "BUY":
        if quantity_offered + net_positions < api.get(s, "limits")[0]['net_limit'] and quantity_offered + gross_positions < api.get(s, "limits")[0]['gross_limit']:
            if TICKS_PER_PERIOD - tick < LAST_MINUTE_THRESHOLD:
                bid_volume : int = 0
                bids = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                vol_times_price : float = 0
                for b in bids:
                    bid_volume += b["quantity"] - b["quantity_filled"]
                    vol_times_price += (b["quantity"] - b["quantity_filled"]) * b["price"]

                vwap : float = vol_times_price / bid_volume

                value_of_offer = quantity_offered * vwap

                potential_profit : float = 0
                bids = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                shares_accounted_for : int = 0
                bid_index : int = 0

                while shares_accounted_for < quantity_offered:
                    shares_accounted_for += bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"]
                    if(shares_accounted_for > quantity_offered):
                        potential_profit += bids[bid_index]["price"] * (quantity_offered - shares_accounted_for + bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"])
                    else:
                        potential_profit += bids[bid_index]["price"] * (bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"])
                    bid_index += 1

                if potential_profit > value_of_offer:
                    return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], "MKT")]
                else:
                    return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[31mREJECT\u001b[37m")]
            else:
            # liquidity_ratio : float = quantity_offered / api.get(s, "securities", ticker = ticker)[0]["total_volume"]                                        
                #bid_volume : int = 0
                #for b in bids_and_asks["bids"]:
                #    bid_volume += b["quantity"] - b["quantity_filled"]
                
                #ask_volume : int = 0
                #for a in bids_and_asks["asks"]:
                #    ask_volume += a["quantity"] - a["quantity_filled"]

                bids = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                shares_accounted_for : int = 0
                bid_index : int = 0

                while shares_accounted_for < quantity_offered:
                    shares_accounted_for += bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"]
                    bid_index += 1

                buy_offer_price : float = bids[bid_index - 1]["price"]

                sell_price :float = api.get(s, "securities", ticker = ticker)[0]["bid"]

                spread = 100*(api.get(s, "securities", ticker = ticker)[0]["ask"]/api.get(s, "securities", ticker = ticker)[0]["bid"] - 1)

                # print("Spread: " + str(spread))

                if spread < MAX_SPREAD: # less volatile
                    """if get_type_of_tender(tender["caption"]) == "Competitive":
                        bid_volume : int = 0
                        bids = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                        vol_times_price : float = 0
                        for b in bids:
                            bid_volume += b["quantity"] - b["quantity_filled"]
                            vol_times_price += (b["quantity"] - b["quantity_filled"]) * b["price"]

                        vwap : float = vol_times_price / bid_volume

                        bids = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['bids']
                        shares_accounted_for : int = 0
                        bid_index : int = 0

                        while shares_accounted_for < quantity_offered:
                            shares_accounted_for += bids[bid_index]["quantity"] - bids[bid_index]["quantity_filled"]
                            bid_index += 1

                        sell_price : float = bids[bid_index - 1]["price"]

                        return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], sell_price)]
                    else:"""

                    return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, buy_offer_price, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], sell_price)]
                else:
                    price_data = api.get(s, "securities/history", ticker = ticker, limit = 20)
                    last_5_ticks = []
                    last_20_ticks = []
                    for i in range(0, 5):
                        last_5_ticks.append(price_data[i]["close"])
                    for i in range(0, 20):
                        last_20_ticks.append(price_data[i]["close"])

                    sma5 = sum(last_5_ticks) / len(last_5_ticks) if len(last_5_ticks) > 0 else 0
                    sma20 = sum(last_20_ticks) / len(last_20_ticks) if len(last_20_ticks) > 0 else 0

                    # print("sma5: " + str(sma5))
                    # print("sma20: " + str(sma20))

                    if sma5 != 0 and sma20 != 0 and sma5 > sma20:
                        return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(buy_offer_price, 2), "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], sell_price)]
                    else:
                        return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, "N/A", "\u001b[31mREJECT\u001b[37m")]
        else:
            return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, "N/A", "\u001b[31mREJECT\u001b[37m")]
    elif action == "SELL":
        current_position : int = api.get(s, "securities", ticker = ticker)[0]["position"]
        if (gross_positions - current_position) + abs(current_position - quantity_offered) < api.get(s, "limits")[0]['gross_limit']:

            shares_to_be_shorted : int = 0

            if 0 <= current_position < quantity_offered:
                shares_to_be_shorted = quantity_offered - current_position
            elif current_position < 0:
                shares_to_be_shorted = quantity_offered

            shares_to_sell_instantly : int = quantity_offered - shares_to_be_shorted

            if shares_to_be_shorted > 0:
                if TICKS_PER_PERIOD - tick < LAST_MINUTE_THRESHOLD:
                    ask_volume : int = 0
                    asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                    vol_times_price : float = 0
                    for a in asks:
                        ask_volume += a["quantity"] - a["quantity_filled"]
                        vol_times_price += (a["quantity"] - a["quantity_filled"]) * a["price"]

                    vwap : float = vol_times_price / ask_volume

                    value_of_offer = shares_to_be_shorted * vwap

                    potential_profit : float = 0
                    asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                    shares_accounted_for : int = 0
                    ask_index : int = 0

                    while shares_accounted_for < shares_to_be_shorted:
                        shares_accounted_for += asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"]
                        if(shares_accounted_for > shares_to_be_shorted):
                            potential_profit += asks[ask_index]["price"] * (shares_to_be_shorted - shares_accounted_for + asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"])
                        else:
                            potential_profit += asks[ask_index]["price"] * (asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"])
                        ask_index += 1

                    potential_profit = vwap * shares_to_be_shorted - potential_profit

                    instant_profit_from_sell : float = 0

                    if shares_to_sell_instantly > 0:
                        instant_profit_from_sell = (vwap - api.get(s, "securities", ticker = ticker)[0]["vwap"]) * shares_to_sell_instantly

                    if potential_profit + instant_profit_from_sell > 0:
                        return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], "MKT")]
                    else:
                        return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[31mREJECT\u001b[37m")]
                else:
                    #liquidity_ratio : float = shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["total_volume"]
                                        
                    #bid_volume : int = 0
                    #for b in bids_and_asks["bids"]:
                    #    bid_volume += b["quantity"] - b["quantity_filled"]
                    
                    #ask_volume : int = 0
                    #for a in bids_and_asks["asks"]:
                    #    ask_volume += a["quantity"] - a["quantity_filled"]

                    asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                    shares_accounted_for : int = 0
                    ask_index : int = 0

                    while shares_accounted_for < shares_to_be_shorted:
                        shares_accounted_for += asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"]
                        ask_index += 1
                    
                    buy_price : float = asks[0]["price"]

                    sell_price_to_offer : float = asks[ask_index - 1]["price"]

                    potential_profit : float = (sell_price_to_offer - buy_price) * shares_to_be_shorted

                    instant_profit_from_sell : float = 0

                    if shares_to_sell_instantly > 0:
                        instant_profit_from_sell = (sell_price_to_offer - api.get(s, "securities", ticker = ticker)[0]["vwap"]) * shares_to_sell_instantly

                    spread = 100*(api.get(s, "securities", ticker = ticker)[0]["ask"]/api.get(s, "securities", ticker = ticker)[0]["bid"] - 1)

                    if spread < MAX_SPREAD or shares_to_sell_instantly >= shares_to_be_shorted: # less volatile or a decent amount of shares to sell instantly for profit
                        """if get_type_of_tender(tender["caption"]) == "Competitive":
                            ask_volume : int = 0
                            asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                            vol_times_price : float = 0
                            for a in asks:
                                ask_volume += a["quantity"] - a["quantity_filled"]
                                vol_times_price += (a["quantity"] - a["quantity_filled"]) * a["price"]

                            vwap : float = vol_times_price / ask_volume # this is the sell price to offer

                            asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                            shares_accounted_for : int = 0
                            ask_index : int = 0

                            while shares_accounted_for < shares_to_be_shorted:
                                shares_accounted_for += asks[ask_index]["quantity"] - asks[ask_index]["quantity_filled"]
                                ask_index += 1
                            
                            buy_price : float = asks[ask_index - 1]["price"]

                            potential_profit : float = (vwap - buy_price) * shares_to_be_shorted

                            instant_profit_from_sell : float = 0

                            if shares_to_sell_instantly > 0:
                                instant_profit_from_sell = (vwap - api.get(s, "securities", ticker = ticker)[0]["vwap"]) * shares_to_sell_instantly

                            if instant_profit_from_sell + potential_profit > 0:
                                return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], buy_price)]
                            else:
                                return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[31mREJECT\u001b[37m")]
                        else:"""
                        if instant_profit_from_sell + potential_profit > 0:
                            return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, sell_price_to_offer, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], buy_price)]
                        else:
                            # print("instant_profit_from_sell: " + str(instant_profit_from_sell), "potential_profit: " + str(potential_profit))
                            return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, sell_price_to_offer, "\u001b[31mREJECT\u001b[37m")]
                    else:
                        price_data = api.get(s, "securities/history", ticker = ticker, limit = 20)
                        last_5_ticks = []
                        last_20_ticks = []
                        for i in range(0, 5):
                            last_5_ticks.append(price_data[i]["close"])
                        for i in range(0, 20):
                            last_20_ticks.append(price_data[i]["close"])

                        sma5 = sum(last_5_ticks) / len(last_5_ticks) if len(last_5_ticks) > 0 else 0
                        sma20 = sum(last_20_ticks) / len(last_20_ticks) if len(last_20_ticks) > 0 else 0

                        # print("sma5: " + str(sma5))
                        # print("sma20: " + str(sma20))

                        if sma5 != 0 and sma20 != 0 and sma5 < sma20:
                            if instant_profit_from_sell + potential_profit > 0:
                                return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, sell_price_to_offer, "\u001b[32mACCEPT\u001b[37m"), (ticker, "BUY" if action == "SELL" else "SELL", int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], buy_price)]
                            else:
                                # print("instant_profit_from_sell: " + str(instant_profit_from_sell), "potential_profit: " + str(potential_profit))
                                return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, sell_price_to_offer, "\u001b[31mREJECT\u001b[37m")]
                        else:
                            return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, sell_price_to_offer, "\u001b[31mREJECT\u001b[37m")]

            else:
                instant_profit_from_sell : float = 0

                """if get_type_of_tender(tender["caption"]) == "Competitive":
                    ask_volume : int = 0
                    asks = api.get(s, "securities/book", ticker = ticker, limit = ORDER_BOOK_SIZE)['asks']
                    vol_times_price : float = 0
                    for a in asks:
                        ask_volume += a["quantity"] - a["quantity_filled"]
                        vol_times_price += (a["quantity"] - a["quantity_filled"]) * a["price"]

                    vwap : float = vol_times_price / ask_volume # this is the sell price to offer

                    instant_profit_from_sell = (vwap - api.get(s, "securities", ticker = ticker)[0]["vwap"]) * shares_to_sell_instantly

                    if instant_profit_from_sell > 0:
                        return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[32mACCEPT\u001b[37m")]
                    else:
                        return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, round(vwap, 2), "\u001b[31mREJECT\u001b[37m")]
                else:"""
                sell_price_to_offer : float = api.get(s, "securities", ticker = ticker)[0]["ask"]

                instant_profit_from_sell = (sell_price_to_offer - api.get(s, "securities", ticker = ticker)[0]["vwap"]) * shares_to_sell_instantly

                if instant_profit_from_sell > 0:
                    return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, sell_price_to_offer, "\u001b[32mACCEPT\u001b[37m")]
                else:
                    return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, sell_price_to_offer, "\u001b[31mREJECT\u001b[37m")]
        else:
            return [(get_type_of_tender(tender["caption"]), action, ticker, quantity_offered, "N/A", "\u001b[31mREJECT\u001b[37m")]

def get_type_of_tender(caption : str):
    if 'institution' in caption:
        return 'private'
    elif 'winner' in caption:
        return 'WTA'
    elif 'reserve' in caption:
        return 'Competitive'

def main():
    with api.requests.Session() as s:
        
        s.headers.update(api.API_KEY)
        
        status = api.get(s, "case")["status"]
        
        while(status != "ACTIVE"):
            status = api.get(s, "case")["status"]
            api.sleep(api.SPEEDBUMP)

        ALL_TENDER_IDS = []

        tender_df = pd.DataFrame(columns = ["Tender Type", "Action", "Ticker", "Quantity", "Price", "Decision"])

        order_df = pd.DataFrame(columns = ["Ticker", "Action", "Quantity", "Price/MKT"])

        system("cls")

        while status == "ACTIVE":
            status = api.get(s, "case")["status"]
            tenders = api.get(s, "tenders")
            for tender in tenders:
                tender_df.drop(tender_df.index, inplace = True)
                order_df.drop(order_df.index, inplace = True)
                if tender["tender_id"] not in ALL_TENDER_IDS and ((not tender["is_fixed_bid"] and tender["expires"] - api.get(s, "case")["tick"] < 15) or (tender["is_fixed_bid"])):
                    ALL_TENDER_IDS.append(tender["tender_id"])
                    if tender["is_fixed_bid"]:
                        info = private_tender_model(s, tender["tender_id"])

                        tender_df.loc[len(tender_df)] = info[0]

                        tender_df.rename(index={0: tender["tender_id"]}, inplace = True)

                        formatted_tender_df = tabulate(tender_df, headers = "keys", tablefmt = "fancy_grid")

                        print(formatted_tender_df)

                        if len(info) > 1:
                            
                            offload_info = info[1]

                            for i in range(offload_info[2]):
                                order_df.loc[len(order_df)] = (offload_info[0], offload_info[1], offload_info[3], offload_info[5])

                            if offload_info[4] > 0:
                                order_df.loc[len(order_df)] = (offload_info[0], offload_info[1], offload_info[4], offload_info[5])

                            formatted_order_df = tabulate(order_df, headers = "keys", tablefmt = "fancy_grid")

                            print(formatted_order_df)
                    else:
                        info = competitive_tender_model(s, tender["tender_id"])

                        tender_df.loc[len(tender_df)] = info[0]

                        tender_df.rename(index={0: tender["tender_id"]}, inplace = True)

                        formatted_tender_df = tabulate(tender_df, headers = "keys", tablefmt = "fancy_grid")

                        print(formatted_tender_df)

                        if len(info) > 1:
                            
                            offload_info = info[1]

                            for i in range(offload_info[2]):
                                order_df.loc[len(order_df)] = (offload_info[0], offload_info[1], offload_info[3], offload_info[5])

                            if offload_info[4] > 0:
                                order_df.loc[len(order_df)] = (offload_info[0], offload_info[1], offload_info[4], offload_info[5])

                            formatted_order_df = tabulate(order_df, headers = "keys", tablefmt = "fancy_grid")

                            print(formatted_order_df)

            api.sleep(api.SPEEDBUMP)


if __name__ == '__main__':
    api.signal.signal(api.signal.SIGINT, api.signal_handler)
    main()
