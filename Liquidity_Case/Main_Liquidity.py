import API_Requests as api
from os import system


NET_TRADING_LIMIT = 150000
GROSS_TRADING_LIMIT = 250000
LAST_MINUTE_THRESHOLD = 60
LIQUIDITY_RATIO_THRESHOLD = 0.05

def private_tender_model(s : api.requests.Session, id : int):
    tender : dict = {}

    for t in api.get(s, "tenders"):
        if t["tender_id"] == id:
            tender = t
            break
    
    if tender == {}:
        return "Tender not found by private_tender_model"
    
    tick : int = int(tender["tick"])
    ticker : str = tender["ticker"]
    price_offered : float = float(tender["price"])
    quantity_offered : int = int(tender["quantity"])
    action : str = tender["action"]
    value_of_offer : float = price_offered * quantity_offered

    net_positions : float = api.get(s, "limits")[0]['net']
    gross_positions : float = api.get(s, "limits")[0]['gross']

    if action == "BUY":
        if net_positions + quantity_offered < NET_TRADING_LIMIT and gross_positions + quantity_offered < GROSS_TRADING_LIMIT:
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
                    unload = "LAST MINUTE UNLOAD: SELL ALL FOR MARKET PRICE"
                    return "\n" + decision + "\n" + unload
                else:
                    decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nTIME LOW, NOT PROFITABLE"
                    return "\n" + decision

            else:
                # for risk percentage, how do we calculate total capital?
                # also, how do we calculate the time to unwind the position?
                # these two things are not accounted for in the model thus far

                # calculate liquidity ratio
                liquidity_ratio : float = quantity_offered / api.get(s, "securities", ticker = ticker)[0]["total_volume"]

                if liquidity_ratio < LIQUIDITY_RATIO_THRESHOLD:
                    
                    bids_and_asks = api.get(s, "securities/book", ticker = ticker, limit = 10000)
                    
                    bid_volume : int = 0
                    for bid in bids_and_asks["bids"]:
                        bid_volume += bid["quantity"] - bid["quantity_filled"]
                    
                    ask_volume : int = 0
                    for ask in bids_and_asks["asks"]:
                        ask_volume += ask["quantity"] - ask["quantity_filled"]

                    if bid_volume > ask_volume: # sellers have the upper hand

                        vwap : float = 0

                        for ask in bids_and_asks["asks"]:
                            vwap += ask["price"] * (ask["quantity"] - ask["quantity_filled"])
                        
                        vwap /= ask_volume

                        decision = "ACCEPT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker)
                        unload = "SELL ALL FOR LIMIT PRICE OF " + str(vwap) + " IN 10000 CHUNKS, THEN REMAINDER"
                        return "\n" + decision + "\n" + unload

                    else:
                        decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nBUYERS HAVE THE UPPER HAND"
                        return "\n" + decision
                else:
                    decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIQUIDITY RATIO TOO HIGH"
        else:
            decision = "REJECT THE PRIVATE BUY OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIMITS EXCEEDED"
            return "\n" + decision
    
    elif action == "SELL":
        if gross_positions + quantity_offered < GROSS_TRADING_LIMIT:
            
            current_position : int = api.get(s, "securities", ticker = ticker)[0]["position"]

            shares_to_be_shorted : int = 0

            if 0 <= current_position < quantity_offered:
                shares_to_be_shorted = quantity_offered - current_position
            elif current_position < 0:
                shares_to_be_shorted = quantity_offered

            shares_to_sell_instantly : int = quantity_offered - shares_to_be_shorted
            value_of_shorted : float = shares_to_be_shorted * price_offered

            instant_profit_from_sell : float = shares_to_sell_instantly * (api.get(s, "securities", ticker = ticker)[0]["vwap"] - price_offered)

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
                        unload = "LAST MINUTE UNLOAD: BUY BACK ALL " + str(shares_to_be_shorted) + " SHARES FOR MARKET PRICE"
                        return "\n" + decision + "\n" + unload
                    else:
                        decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + ticker + "\nTIME LOW, NOT PROFITABLE"
                        return "\n" + decision               
                else:
                    liquidity_ratio : float = shares_to_be_shorted / api.get(s, "securities", ticker = ticker)[0]["total_volume"]

                    if liquidity_ratio < LIQUIDITY_RATIO_THRESHOLD:
                        
                        bids_and_asks = api.get(s, "securities/book", ticker = ticker, limit = 10000)
                        
                        bid_volume : int = 0
                        for bid in bids_and_asks["bids"]:
                            bid_volume += bid["quantity"] - bid["quantity_filled"]
                        
                        ask_volume : int = 0
                        for ask in bids_and_asks["asks"]:
                            ask_volume += ask["quantity"] - ask["quantity_filled"]

                        if bid_volume < ask_volume: # buyers have the upper hand

                            vwap : float = 0

                            for bid in bids_and_asks["bids"]:
                                vwap += bid["price"] * (bid["quantity"] - bid["quantity_filled"])
                            
                            vwap /= bid_volume
                            
                            potential_profit = value_of_shorted - shares_to_be_shorted * vwap

                            if instant_profit_from_sell + potential_profit > 0:
                                decision = "ACCEPT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker)
                                unload = "BUY BACK ALL " + str(shares_to_be_shorted) + " SHARES TO BE SHORTED FOR LIMIT PRICE OF " + str(vwap) + " IN 10000 CHUNKS, THEN REMAINDER"
                                return "\n" + decision + "\n" + unload
                            
                            else:
                                decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nINSTANT PROFIT + POTENTIAL LESS THAN 0"
                                return "\n" + decision
                        else:
                            # we may want to accept here: buying back the shorts is disadvantageous because sellers have the upper hand
                            # buy instant profit may outweigh the disadvantage of buying back the shorts
                            decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nSELLERS HAVE THE UPPER HAND"
                            return "\n" + decision

                    else:
                        decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIQUIDITY RATIO TOO HIGH"
                        return "\n" + decision

            elif instant_profit_from_sell > 0:
                decision = "ACCEPT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker)
                unload = "WE OWN ALL OF THE SHARES, SELL ALL FOR OFFER PRICE"
                return "\n" + decision + "\n" + unload
            else:
                decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nINSTANT PROFIT LESS THAN 0"
                return "\n" + decision
        else:
            decision = "REJECT THE PRIVATE SELL OFFER FOR " + str(quantity_offered) + " SHARES OF " + str(ticker) + "\nLIMITS EXCEEDED"
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
        
        tick = api.get(s, "case")["tick"]
        
        old_tenders = api.get(s, "tenders")

        system("cls")

        for tender in old_tenders:
            if tender["is_fixed_bid"]:
                print(private_tender_model(s, tender["tender_id"]))

        while tick < 600:
            tick = api.get(s, "case")["tick"]
            # get the current tender offers
            tenders = api.get(s, "tenders")
            if tenders != old_tenders and len(tenders) > 0:
                old_tenders = tenders
                print(tenders[0]["tender_id"])
                if tenders[0]["is_fixed_bid"]:
                    print(private_tender_model(s, tenders[0]["tender_id"])) # should this be 0 or -1? in the case of multiple tenders, we want the most recent one

if __name__ == '__main__':
    api.signal.signal(api.signal.SIGINT, api.signal_handler)
    main()
