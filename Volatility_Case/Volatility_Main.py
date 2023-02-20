import signal
import requests
import json
from time import sleep
import sys
import optionprice
from optionprice import Option
import re
import math
import py_vollib 
from py_vollib.black_scholes  import black_scholes as bs
from py_vollib.black_scholes.implied_volatility import implied_volatility as iv
from py_vollib.black_scholes.greeks.analytical import delta as delta

# this class definition allows us to print error messages and stop the program when needed
class ApiException(Exception):
	pass

#this signal handler allows us for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
	global shutdown
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	shutdown = True


API_KEY = {'X-API-key': 'DV2931GT'} # Save your API key for easy access.
BASE_URL = 'http://localhost:9999/v1/'
shutdown = False


#SETTINGS
# How long to wait after submitting buy or sell orders 
SPEEDBUMP = 0.5
# Maximum number of shares to purchase each order
MAX_VOLUME = 5000
# Maximum number oforder we can sumbit
MAX_ORDERS = 5
# Allowed spread before we sell or buy shares
SPREAD = 0.05

# GLOBALS
global current_tick
global current_period
global ticks_per_period
global total_periods
global trader_id
global first_name
global last_name

# API FUNCTIONS
def api_get(session : requests.Session, endpoint: str, **kwargs : dict) -> dict:
	'''
	Makes a custom GET request to a specified endpoint in the RIT API

		Parameters:
			Session (requests.Session): Current Session Object
			endpoint (String): name of the end point ex "case" or "assets/history" or "orders/{insert your id here}"
			kwargs (Dict): Dictionary that maping each keyword to the value that we pass alongside it
		
		Returns:
			Payload (Dict): Dictonary contining the JSON returned from the endpoint
	
		Example Usage:
			api_get( s, "case")
			api_get( s, "assets/history", ticker = "RTM", period = "14", limit ="100" )
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.get(URL, params=kwargs)
	payload : dict = resp.json()

	if not resp.ok:
		print('API GET FAILED')
		raise ApiException(payload["code"] + ": " + payload["message"])

	return payload

def api_post(session : requests.Session, endpoint: str, **kwargs : dict) -> dict:
	'''
	Makes a custom POST request to a specified endpoint in the RIT API

		Parameters:
			Session (requests.Session): Current Session Object
			endpoint (String): name of the end point ex "case" or "assets/history" or "orders/{insert your id here}"
			kwargs (Dict): Dictionary that maping each keyword to the value that we pass alongside it
		
		Returns:
			Payload (Dict): Dictonary contining the JSON returned from the endpoint
	
		Example Usage:
			api_post( s, "orders", ticker = "RTM", type = "LIMIT", quantity = "100", action = "SELL")
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.post(URL, params=kwargs)
	payload : dict = resp.json()
	
	if resp.ok:
		print('API POST SUCCESSFUL')
	else:
		print('API POST FAILED')
		print(payload["code"] + ": " + payload["message"])
		if(resp.status_code == 429):
			print(payload["code"] + ": " + payload["message"])
			return -1
		else:
			ApiException(payload["code"] + ": " + payload["message"])

	return payload

def api_delete(session : requests.Session, endpoint: str, **kwargs : dict) -> dict:
	'''
	Makes a custom DELETE request to a specified endpoint in the RIT API

		Parameters:
			Session (requests.Session): Current Session Object
			endpoint (String): name of the end point ex "case" or "assets/history" or "orders/{insert your id here}"
			kwargs (Dict): Dictionary that mapping each keyword to the value that we pass alongside it
		
		Returns:
			Payload (Dict): Dictionary continuing the JSON returned from the endpoint
	
		Example Usage:
			api_delete( s, "/tenders/{id}")
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.post(URL, params=kwargs)
	payload : dict = resp.json()

	if resp.ok:
		print('API DELETE SUCCESSFUL')
	else:
		print('API DELETE FAILED')
		raise ApiException(payload["code"] + ": " + payload["message"])
	return payload
	
# OTHER FUNCITONS
def parse_esitmate(session : requests.Session):
	print("estimate")
	sleep(1)
	payload = api_get(session, "news")
	print(payload)
	if( payload[0]["news_id"] % 2 == 0):
		raise Exception("ERROR: Most recent news not a volatility annoucement")
	else: 
		low = int(nth_word(payload[0]["body"], 11)[:-1])
		high = int(nth_word(payload[0]["body"], 13)[:-1])
		print("{} parsed. Range: {} ~ {}",payload[0]["headline"],low,high)
		last_news_id = payload[0]["news_id"]
		return (last_news_id,low,high)
	
def parse_announcemnt(session : requests.Session):
	print("annoucement")
	sleep(1)
	payload = api_get(session, "news")
	print(payload)
	if( payload[0]["news_id"] % 2 == 1):
		raise Exception("ERROR: Most recent news not a volatility annoucement")
	else: 
		print("{} parsed. Volatility: {}",payload[0]["headline"],int(nth_word(payload[0]["body"], 8)[:-1]))
		last_news_id = payload[0]["news_id"]
		return (last_news_id,int(nth_word(payload[0]["body"], 8)[:-1]))

def nth_word(string : str, n: int):
	res = re.findall(r'\S+', string)
	return res[n-1]

def update_time(session : requests.Session):
	global current_tick
	global current_period
	payload = api_get(session, "case")
	current_tick = int(payload["tick"])
	current_period = int(payload["period"])
	return current_tick,current_period


def Price_option(security : dict, stock_price : float, volatility : float):
	global current_tick
	global current_period
	global ticks_per_period
	global total_periods
	global trader_id
	global first_name
	global last_name
	
	if(security["ticker"][4] == 'C'):
		flag = 'c'
	else:
		flag = 'p'

	S = stock_price
	K = int(security["ticker"][5:])
	t = 0.0191781
	#(((int(security["stop_period"]) * 300) - (current_period -1)*300 + current_tick)/15)/365.24
	r = 0.0
	sigma = volatility/100
	print()
	print("FLAG:      ", flag)
	print("SPOT:      ", S)
	print("STRIKE:    ", K)
	print("TIME:      ", t)
	print("RISK-FREE: ", r)
	print("Volitlity: ", sigma)
	p_hat = bs(flag, S, K, t, r, sigma)
	return p_hat

'''
def Price_option(security : dict, volatility : float):

	if(security["ticker"][4] == 'C'):
		kind = 'call'
	else:
		kind = 'put'

	some_option = Option(european=True,
						kind=kind,
						s0=(security["bid"] + security["ask"])/2,
						k = int(security["ticker"][5:]),
						sigma= volatility,
						r=0.00,
						t = int(((int(security["stop_period"]) * 300) - (current_period -1)*300 + current_tick)/15),				
						dv=0)
	return some_option.getPrice()
'''

def main():
	
	with requests.Session() as s: # Create a Session object to manage connections and requests to the RIT client.

		s.headers.update(API_KEY) # Add the API key to the Session to authenticate with every request
		
		#VARIABLES:
		payload = api_get(s, "case")
		current_tick = int(payload["tick"])
		current_period = int(payload["period"])
		ticks_per_period = int(payload["ticks_per_period"])
		total_periods = int(payload["total_periods"])
		

		payload = api_get(s, "trader")

		trader_id = payload["trader_id"]
		first_name = payload["first_name"]
		last_name = payload["last_name"]
		current_nlv = payload["nlv"]


		payload = api_get(s, "news", since = 0)
		
		last_news_id = payload[0]["news_id"]
		risk_free = int(nth_word(payload[-1]["body"], 7)[:-2])
		volailtiy = int(nth_word(payload[-1]["body"], 29)[:-2])
		days_per_heat = int(nth_word(payload[-1]["body"], 34))

		delta_limit = int(re.sub(",", "", nth_word(payload[-2]["body"], 8).strip(',')))
		penalty_percentage = int(nth_word(payload[-2]["body"], 14)[:-1])

		next_estimate = 37
		next_annoucement = 75
		
		new_estimate = False
		new_annoucement = False

		while(True):

			# update time
			current_tick,current_period = update_time(s)
			print(current_tick)
			
			# parse news
			if(current_tick > 262):
				next_estimate = 37
				next_annoucement = 0

			if (current_tick % 75 >= 37 and current_tick >= next_estimate and current_tick < 263):
				if(current_period == 2 and current_tick > 261):
					continue 
				print(last_news_id)
				last_news_id,low,high = parse_esitmate(s)
				next_estimate = math.floor( (last_news_id - ((current_period - 1) *9))/2 * 75)
				new_estimate = True
			elif( current_tick % 75 < 37 and current_tick >= next_annoucement and current_tick < 251):
				print(last_news_id)
				last_news_id,volatility = parse_announcemnt(s)
				next_annoucement = (last_news_id - ((current_period -1)*9))/2 * 75
				new_annoucement = True

			#Get list of securites 
			securities = api_get(s,"securities")

			#Set Trade Counter
			trade_counter = 0

			# iterate through Securities 
			for i, security in enumerate(securities):
				
				#ignore expired options
				if( security['stop_period'] < current_period):
					continue

				#ignore non-option securities
				if(security["ticker"] == "RTM"):
					stock_price = (security["bid"] + security["ask"])/2
					continue
				
				#VOLATILITY ARBITRAGE
				if(new_annoucement):
					# price the option
					p_hat = Price_option(security,stock_price,volatility)
					print("-------------------------------")
					print("MRK PRICE: ", (security["bid"] + security["ask"])/2)
					print("P_HAT:     ",p_hat)
					print()

					# If underpriced 
					if(p_hat < ((security["bid"] + security["ask"])/2) - 0.05):
						# Calc quantity needed to overcome Trading fee
						q = math.ceil( 4.00 / ( p_hat - (security["bid"] + security["ask"])/2 ) )

						# long the call option
						api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = q, action = "BUY" )

						# short the underlying to hedge
						api_post(s,"orders", ticker = "RTM", type = "MARKET", quantity = q*100, action = "SELL" )

						trade_counter += 2

					# If over priced 
					elif ( p_hat > ((security["bid"] + security["ask"])/2) + 0.05):
						#Calc quantity needed to overcome Trading fee
						q = math.ceil( 4.00 / ( p_hat - ((security["bid"] + security["ask"])/2) ) )

						# short the call option
						api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = q, action = "SELL" )

						# long the underlying asset to hedge
						api_post(s,"orders", ticker = "RTM", type = "MARKET", quantity = q*100, action = "BUY" )

						trade_counter += 2

				#elif(new_estimate):
					'''
					p_hat_low = Price_option(i,stock_price,low)
					p_hat_high = Price_option(i,stock_price,high)

					if(p_hat_low != None):
						pass
					if(p_hat_high != None):
						pass
					'''
					# price with lower bound
					# price with higher bound
					# iterate through all securities
					# if market_price > higher bound
						# bring it back to higher bound
					# if market_price < Lower_Bound
						# bring it up to Lower_Bound
				if(trade_counter > 8 and i != len(securities)-1 ):
					sleep(1)
					trade_counter = 0
			new_estimate = False
			new_annoucement = False
			sleep(1)

			'''
			RANGE:

			check if the option was price with a volitility outsode of the range. 

			price with lowest 
			price with highest
			if market price is outside of these prices:
				arb oppertunity
			else:
				no arb oppertunity 

			ANNUCEMENT:
			Issue only have 1 week of volatility 
			dont know full volatility until the end of the contract 
			we can sell the contract before expiry though 
			do i assume that volitlity will hold for the whole time????
			'''
				



if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	main()
	"""
		NOTE:	RIT Client must be running to access this API
		NOTE:	Responses are always JSON objects.
		NOTE:	Successful requests always return with HTTP code 200
		NOTE:	Unsuccessful responses have HTTP error codes between 400 and 500
	"""



'''
TODO:
3. fix the too many requests issue : its messing up my hedging
4. switch to py_vollib
5. is 46 the actual price or an error?
	emprical: only exersize arb oppertunities where price is signifiganlty off, see if it makes money
	could this be because of exersize arbitrage or something
	does black scholes account for exersize arbitrage?
6. Track riskless profits from arbitrage oppertunities
7. download LLVM + LLVM lite + NUMBA
8. combine all RTM hedgeing into one trade 

skipped 0
hit 75
missed estimate @ 112
missed annoucement @ 150
missed estimate @ 187
missed annoucement @ 225

'''