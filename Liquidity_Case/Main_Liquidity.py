# pip install tabulate pandas requests

import API_Requests as api
from os import system
import pandas as pd
from tabulate import tabulate
LAST_MINUTE_THRESHOLD = 60
LIQUIDITY_RATIO_THRESHOLD = 100
VOLUME_RATIO_THRESHOLD = 1.0
MAX_SPREAD = .15

def private_tender_model(s : api.requests.Session, tender_id : int):

    tender : dict = {}

    for t in api.get(s, "tenders"):
        if t["tender_id"] == tender_id:
            tender = t
            break
    
    if tender == {}:
        return "Tender not found by private_tender_model"
    
    bid = api.get(s, "securities", ticker = tender["ticker"])[0]["bid"]
    ask = api.get(s, "securities", ticker = tender["ticker"])[0]["ask"]

    spread = 100*(ask/bid - 1)

    tick : int = int(tender["tick"])
    ticker : str = tender["ticker"]
    price_offered : float = float(tender["price"])
    quantity_offered : int = int(tender["quantity"])
    action : str = tender["action"]
    value_of_offer : float = price_offered * quantity_offered

    net_positions : float = api.get(s, "limits")[0]['net']
    gross_positions : float = api.get(s, "limits")[0]['gross']

    if action == "BUY":
        if net_positions + quantity_offered < api.get(s, "limits")[0]['net_limit'] and gross_positions + quantity_offered < api.get(s, "limits")[0]['gross_limit']:
            if 600 - tick < LAST_MINUTE_THRESHOLD:

                potential_profit : float = 0
                bids = api.get(s, "securities/book", ticker = ticker, limit = 10000)['bids']
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
                    decision = "ACCEPT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker)
                    unload = "LAST MINUTE UNLOAD: SELL ALL FOR MARKET PRICE: " + str(int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"])) + " SHARES OF " + str(api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + ", THEN " + str(quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " SHARES"
                    return [("Private", action, ticker, quantity_offered, price_offered, ask, spread, "\u001b[32mACCEPT\u001b[37m", "PROFITABLE LAST MINUTE"), (ticker, action, int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], "MKT")]
                else:
                    decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nTIME LOW, NOT PROFITABLE"
                    return [("Private", action, ticker, quantity_offered, price_offered, ask, spread, "\u001b[31mREJECT\u001b[37m", "NOT PROFITABLE LAST MINUTE")]

            else:
                # for risk percentage, how do we calculate total capital?
                # also, how do we calculate the time to unwind the position?
                # these two things are not accounted for in the model thus far

                # calculate liquidity ratio
                liquidity_ratio : float = quantity_offered / api.get(s, "securities", ticker = ticker)[0]["total_volume"]

                if liquidity_ratio < LIQUIDITY_RATIO_THRESHOLD:
                    
                    bids_and_asks = api.get(s, "securities/book", ticker = ticker, limit = 10000)
                    
                    bid_volume : int = 0
                    for b in bids_and_asks["bids"]:
                        bid_volume += b["quantity"] - b["quantity_filled"]
                    
                    ask_volume : int = 0
                    for a in bids_and_asks["asks"]:
                        ask_volume += a["quantity"] - a["quantity_filled"]

                    print("bid_volume: " + str(bid_volume))
                    print("ask_volume: " + str(ask_volume))

                    spread = 100*(api.get(s, "securities", ticker = ticker)[0]["ask"]/api.get(s, "securities", ticker = ticker)[0]["bid"] - 1)

                    print("spread: " + str(spread))

                    if spread < MAX_SPREAD: # sellers have the upper hand

                        vwap : float = 0

                        for a in bids_and_asks["asks"]:
                            vwap += a["price"] * (a["quantity"] - a["quantity_filled"])
                        
                        vwap /= ask_volume

                        sell_price = ((vwap + bids_and_asks["asks"][0]["price"]) / 2 + bids_and_asks["asks"][0]["price"]) / 2 

                        if sell_price > price_offered:
                            decision = "ACCEPT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker)
                            unload = "MAKE " + str(int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"])) + " LIMIT SELL ORDERS OF " + str(api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " FOR " + str(round(sell_price, 2)) + " EACH, THEN " + str(quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " SHARES"
                            return [("Private", action, ticker, quantity_offered, price_offered, ask, spread, "\u001b[32mACCEPT\u001b[37m", "PROFITABLE"), (ticker, action, int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], round(sell_price, 2))]
                        else:
                            decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIMIT SELL PRICE NOT PROFITABLE"
                            return [("Private", action, ticker, quantity_offered, price_offered, ask, spread, "\u001b[31mREJECT\u001b[37m", "NOT PROFITABLE")]
                    else:
                        decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nSPREAD TOO HIGH"
                        return [("Private", action, ticker, quantity_offered, price_offered, ask, spread, "\u001b[31mREJECT\u001b[37m", "SPREAD TOO HIGH")]
                else:
                    decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIQUIDITY RATIO TOO HIGH"
                    return [("Private", action, ticker, quantity_offered, price_offered, ask, spread, "\u001b[31mREJECT\u001b[37m", "LIQUIDITY RATIO")]
        else:
            decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIMITS EXCEEDED"
            return [("Private", action, ticker, quantity_offered, price_offered, ask, spread, "\u001b[31mREJECT\u001b[37m", "LIMITS EXCEEDED")]
    
    elif action == "SELL":
        if gross_positions + quantity_offered < api.get(s, "limits")[0]['gross_limit']:
            
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

            if shares_to_be_shorted > 0:
                if 600 - tick < LAST_MINUTE_THRESHOLD:
                    asks = api.get(s, "securities/book", ticker = ticker, limit = 10000)['asks']
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
                        decision = "ACCEPT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker)
                        unload = "LAST MINUTE UNLOAD: BUY BACK ALL " + str(shares_to_be_shorted) + " SHARES FOR MARKET PRICE: " + str(int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"])) + " SHARES OF " + str(api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + ", THEN " + str(shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " SHARES"
                        return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[32mACCEPT\u001b[37m", "PROFITABLE LAST MINUTE"), (ticker, action, int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], "MKT")]
                    else:
                        decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + ticker + "\nTIME LOW, NOT PROFITABLE"
                        return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[31mREJECT\u001b[37m", "NOT PROFITABLE LAST MINUTE")]          
                else:
                    liquidity_ratio : float = shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["total_volume"]

                    if liquidity_ratio < LIQUIDITY_RATIO_THRESHOLD:
                        
                        bids_and_asks = api.get(s, "securities/book", ticker = ticker, limit = 10000)
                        
                        bid_volume : int = 0
                        for b in bids_and_asks["bids"]:
                            bid_volume += b["quantity"] - b["quantity_filled"]
                        
                        ask_volume : int = 0
                        for a in bids_and_asks["asks"]:
                            ask_volume += a["quantity"] - a["quantity_filled"]

                        print("bid volume: " + str(bid_volume))
                        print("ask volume: " + str(ask_volume))

                        spread = 100*(api.get(s, "securities", ticker = ticker)[0]["ask"]/api.get(s, "securities", ticker = ticker)[0]["bid"] - 1)

                        print("spread: " + str(spread))

                        if spread < MAX_SPREAD: # buyers have the upper hand

                            vwap : float = 0

                            for b in bids_and_asks["bids"]:
                                vwap += b["price"] * (b["quantity"] - b["quantity_filled"])
                            
                            vwap /= bid_volume

                            buy_price = ((vwap + bids_and_asks["bids"][0]["price"]) / 2 + bids_and_asks["bids"][0]["price"]) / 2
                            
                            potential_profit = value_of_shorted - shares_to_be_shorted * buy_price

                            if instant_profit_from_sell + potential_profit > 0:
                                decision = "ACCEPT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker)
                                unload = "MAKE " + str(int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"])) + " LIMIT BUY ORDERS OF " + str(api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " FOR " + str(round(buy_price, 2)) + " EACH, THEN " + str(shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " SHARES"
                                return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[32mACCEPT\u001b[37m", "PROFITABLE"), (ticker, action, int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]), api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"], round(buy_price, 2))]
                            
                            else:
                                decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nINSTANT PROFIT + POTENTIAL LESS THAN 0"
                                return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[31mREJECT\u001b[37m", "NOT PROFITABLE")]
                        else:
                            # we may want to accept here: buying back the shorts is disadvantageous because sellers have the upper hand
                            # but instant profit may outweigh the disadvantage of buying back the shorts
                            decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nSPREAD TOO HIGH"
                            return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[31mREJECT\u001b[37m", "SPREAD TOO HIGH")]

                    else:
                        decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIQUIDITY RATIO TOO HIGH"
                        return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[31mREJECT\u001b[37m", "LIQUIDITY RATIO TOO HIGH")]

            elif instant_profit_from_sell > 0:
                decision = "ACCEPT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker)
                unload = "WE OWN ALL OF THE SHARES, SELL ALL FOR OFFER PRICE"
                return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[32mACCEPT\u001b[37m", "INSTANT PROFIT")]
            else:
                decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nINSTANT PROFIT LESS THAN 0"
                return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[31mREJECT\u001b[37m", "NOT PROFITABLE INSTANTLY")]
        else:
            decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIMITS EXCEEDED"
            return [("Private", action, ticker, quantity_offered, price_offered, bid, spread, "\u001b[31mREJECT\u001b[37m", "LIMITS EXCEEDED")]

def competitive_tender_model(s : api.requests.Session, tender_id : int):
    tender : dict = {}

    for t in api.get(s, "tenders"):
        if t["tender_id"] == tender_id:
            tender = t
            break
    
    if tender == {}:
        return "Tender not found by private_tender_model"
    
    # print current market price for the security
    print("current ask for this security: " + str(api.get(s, "securities", ticker = tender["ticker"])[0]["ask"]))
    print("current bid for this security: " + str(api.get(s, "securities", ticker = tender["ticker"])[0]["bid"]))


    # print("\nWaiting on competitive tender " + str(tender_id) + " to get close to expiring")

    # wait until 10 seconds before the tender ends
    # while api.get(s, "case")["tick"] < tender["expires"] - 10:
      #  api.sleep(api.SPEEDBUMP)

    tick : int = int(tender["tick"])
    ticker : str = tender["ticker"]
    quantity_offered : int = int(tender["quantity"])
    action : str = tender["action"]

    net_positions : float = api.get(s, "limits")[0]['net']
    gross_positions : float = api.get(s, "limits")[0]['gross']

    bids_and_asks : dict = api.get(s, "securities/book", ticker = ticker, limit = 10000)

    buy_price_to_offer : float = bids_and_asks["asks"][0]["price"]
    sell_price_to_offer : float = bids_and_asks["bids"][0]["price"]

    if action == "BUY":
        if quantity_offered + net_positions < api.get(s, "limits")[0]['net_limit'] and quantity_offered + gross_positions < api.get(s, "limits")[0]['gross_limit']:
            if 600 - tick < LAST_MINUTE_THRESHOLD:
                # we may want to accept a last minute competitive buy offer, but how do we calculate a price to offer?
                # if we were to sell all at market price, we wouldnt be able to set our offer price at the lowest ask - we would still be at a loss

                decision = "REJECT THE COMPETITIVE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLAST MINUTE"
                return "\n" + decision
            else:
                liquidity_ratio : float = quantity_offered / api.get(s, "securities", ticker = ticker)[0]["total_volume"]

                if liquidity_ratio < LIQUIDITY_RATIO_THRESHOLD:
                                        
                    bid_volume : int = 0
                    for b in bids_and_asks["bids"]:
                        bid_volume += b["quantity"] - b["quantity_filled"]
                    
                    ask_volume : int = 0
                    for a in bids_and_asks["asks"]:
                        ask_volume += a["quantity"] - a["quantity_filled"]

                    print("bid_volume: " + str(bid_volume))
                    print("ask_volume: " + str(ask_volume))

                    spread = 100*(api.get(s, "securities", ticker = ticker)[0]["ask"]/api.get(s, "securities", ticker = ticker)[0]["bid"] - 1)

                    print("spread: " + str(spread))

                    if spread < MAX_SPREAD: # sellers have the upper hand

                        vwap : float = 0

                        for a in bids_and_asks["asks"]:
                            vwap += a["price"] * (a["quantity"] - a["quantity_filled"])
                        
                        vwap /= ask_volume

                        sell_price = ((vwap + bids_and_asks["asks"][0]["price"]) / 2 + bids_and_asks["asks"][0]["price"]) / 2

                        if sell_price > buy_price_to_offer:
                            decision = "ACCEPT THE COMPETITIVE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + " AT PRICE: " + str(round(buy_price_to_offer, 2))
                            unload = "MAKE " + str(int(quantity_offered / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"])) + " LIMIT SELL ORDERS OF " + str(api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " FOR " + str(round(sell_price, 2)) + " EACH, THEN " + str(quantity_offered % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " SHARES"
                            return "\n" + decision + "\n" + unload
                        else:
                            decision = "REJECT THE COMPETITIVE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIMIT SELL PRICE TOO LOW"
                            return "\n" + decision

                    else:
                        decision = "REJECT THE COMPETITIVE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nSPREAD TOO HIGH"
                        return "\n" + decision
                else:
                    decision = "REJECT THE COMPETITIVE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIQUIDITY RATIO TOO HIGH"
                    return "\n" + decision
        else:
            decision = "REJECT THE COMPETITIVE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIMITS EXCEEDED"
            return "\n" + decision
    
    elif action == "SELL":
        if quantity_offered + gross_positions < api.get(s, "limits")[0]['gross_limit']:
            current_position : int = api.get(s, "securities", ticker = ticker)[0]["position"]

            shares_to_be_shorted : int = 0

            if 0 <= current_position < quantity_offered:
                shares_to_be_shorted = quantity_offered - current_position
            elif current_position < 0:
                shares_to_be_shorted = quantity_offered

            shares_to_sell_instantly : int = quantity_offered - shares_to_be_shorted
            value_of_shorted : float = shares_to_be_shorted * sell_price_to_offer

            instant_profit_from_sell : float = shares_to_sell_instantly * (sell_price_to_offer - api.get(s, "securities", ticker = ticker)[0]["vwap"])

            potential_profit : float = 0

            if shares_to_be_shorted > 0:
                if 600 - tick < LAST_MINUTE_THRESHOLD:
                    # we may want to accept a last minute competitive buy offer, but how do we calculate a price to offer?
                    # if we were to sell all at market price, we wouldnt be able to set our offer price at the lowest ask - we would still be at a loss

                    decision = "REJECT THE COMPETITIVE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLAST MINUTE"
                    return "\n" + decision

                else:
                    liquidity_ratio : float = shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["total_volume"]

                    if liquidity_ratio < LIQUIDITY_RATIO_THRESHOLD:
                                            
                        bid_volume : int = 0
                        for b in bids_and_asks["bids"]:
                            bid_volume += b["quantity"] - b["quantity_filled"]
                        
                        ask_volume : int = 0
                        for a in bids_and_asks["asks"]:
                            ask_volume += a["quantity"] - a["quantity_filled"]

                        print("bid volume: " + str(bid_volume))
                        print("ask volume: " + str(ask_volume))

                        spread = 100*(api.get(s, "securities", ticker = ticker)[0]["ask"]/api.get(s, "securities", ticker = ticker)[0]["bid"] - 1)

                        print("spread: " + str(spread))

                        if spread < MAX_SPREAD: # buyers have the upper hand

                            vwap : float = 0

                            for b in bids_and_asks["bids"]:
                                vwap += b["price"] * (b["quantity"] - b["quantity_filled"])
                            
                            vwap /= bid_volume
                            
                            buy_price = ((vwap + bids_and_asks["bids"][0]["price"]) / 2 + bids_and_asks["bids"][0]["price"]) / 2

                            potential_profit = value_of_shorted - shares_to_be_shorted * buy_price

                            if instant_profit_from_sell + potential_profit > 0:
                                decision = "ACCEPT THE COMPETITIVE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + " AT PRICE: " + str(sell_price_to_offer)
                                unload = "MAKE " + str(int(shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["max_trade_size"])) + " LIMIT BUY ORDERS OF " + str(api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " FOR " + str(round(buy_price, 2)) + " EACH, THEN " + str(shares_to_be_shorted % api.get(s, "securities", ticker = ticker)[0]["max_trade_size"]) + " SHARES"
                                return "\n" + decision + "\n" + unload
                            
                            else:
                                decision = "REJECT THE COMPETITIVE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nINSTANT PROFIT + POTENTIAL LESS THAN 0"
                                return "\n" + decision
                        else:
                            # we may want to accept here: buying back the shorts is disadvantageous because sellers have the upper hand
                            # but instant profit may outweigh the disadvantage of buying back the shorts
                            decision = "REJECT THE COMPETITIVE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nSPREAD TOO HIGH"
                            return "\n" + decision

                    else:
                        decision = "REJECT THE COMPETITIVE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIQUIDITY RATIO TOO HIGH"
                        return "\n" + decision

            elif instant_profit_from_sell > 0:
                decision = "ACCEPT THE COMPETITIVE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + " AT PRICE: " + str(sell_price_to_offer)
                unload = "WE OWN ALL OF THE SHARES, SELL ALL FOR OFFER PRICE"
                return "\n" + decision + "\n" + unload
            else:
                decision = "REJECT THE COMPETITIVE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nINSTANT PROFIT LESS THAN 0"
                return "\n" + decision
        else:
            decision = "REJECT THE COMPETITIVE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIMITS EXCEEDED"
            return "\n" + decision



# may be useful if we decide to differentiate between competitive and WTA tenders
def get_type_of_tender(caption : str):
    if 'institution' in caption:
        return 'private'
    elif 'winner' in caption:
        return 'WTA'
    elif 'reserve' in caption:
        return 'competitive'

def main():
    with api.requests.Session() as s:
        
        s.headers.update(api.API_KEY)
        
        status = api.get(s, "case")["status"]
        
        while(status != "ACTIVE"):
            status = api.get(s, "case")["status"]
            api.sleep(api.SPEEDBUMP)

        ALL_TENDER_IDS = []

        tender_df = pd.DataFrame(columns = ["Tender Type", "Action", "Ticker", "Quantity", "Price", "Bid/Ask", "Spread", "Decision", "Reason"])

        order_df = pd.DataFrame(columns = ["Ticker", "Action", "Quantity", "Price/MKT"])

        system("cls")

        while status == "ACTIVE":
            status = api.get(s, "case")["status"]
            tenders = api.get(s, "tenders")
            tender_df.drop(tender_df.index, inplace = True)
            order_df.drop(order_df.index, inplace = True)
            for tender in tenders:
                if tender["tender_id"] not in ALL_TENDER_IDS:
                    ALL_TENDER_IDS.append(tender["tender_id"])
                    if tender["is_fixed_bid"]:
                        info = private_tender_model(s, tender["tender_id"])

                        tender_df.loc[len(tender_df)] = info[0]

                        tender_df.rename(index={0: tender["tender_id"]}, inplace = True)

                        formatted_tender_df = tabulate(tender_df, headers = "keys", tablefmt = "fancy_grid")

                        print(formatted_tender_df)

                        if len(info) > 1:
                            
                            print(info[1])

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
