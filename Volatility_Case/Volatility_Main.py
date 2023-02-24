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
from scipy.stats import norm


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
# self tuned risk threshold
RISK_THRESH = 0.6
# average weekly volatility measured empirically
AVG_VOL = 25.0
# Stadard deviation measured empirically
STD_DEV = 3.779838657739062
# Risk Free
RISK_FREE = 0.0


# GLOBALS
global current_tick
global current_period
global current_volatility
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

# OBJECTS
class Arb_Opp:
	def __init__(self, value : float, delta : float , fee : int, opt_gross_cost : float, opt_net_cost : float, ETF_gross_cost : float, ETF_net_cost : float,
	min_quantity : int, max_quantity : int ):
		self.value : float = value
		self.delta : float = delta
		self.fee : float = fee 
		self.opt_gross_cost : int = opt_gross_cost
		self.opt_net_cost : int = opt_net_cost 
		self.ETF_gross_cost : int = ETF_gross_cost
		self.ETF_net_cost : int = ETF_net_cost 
		self.min_quantity : int = min_quantity
		self.max_quantity : int = max_quantity

class Position:
	def __init__(self, session : requests.Session, delta, ticker, price, quantity, og_price, og_volatility, gross_cost, net_cost,ticks_til_expiration):
		self.s : requests.Session = session
		self.ticker : str = ticker
		if(self.ticker != "RTM"):
			if(self.ticker[4] == 'C'):
				self.type = 'C'
			else:
				self.type = 'P'
		else:
			self.type = 'S'
		self.price : float = price
		self.delta : float = delta
		self.quantity : float = quantity
		self.og_price : float = og_price
		self.og_volatility : float = og_volatility
		self.gross_cost : float = gross_cost
		self.net_cost : float = net_cost
		self.ticks_til_expiration : int = ticks_til_expiration
		self.update()

	def update(self) -> None:
		security = api_get(self.s, "securities",ticker = self.ticker)
		self.price = (security["bid"] + security["ask"])/2.0
		self.quantity = security["position"]
		case = api_get(self.s,"case")
		self.ticks_til_expiration = (int(security["stop_period"]) * 300) - (case["period"] -1)*300 + case["tick"]
		return

	def get_price(self) -> float:
		self.update()
		return self.price
		
	def get_quantity(self) -> int:
		self.update()
		return self.quantity
	
	def get_ticks_til_expiration(self) -> int:
		self.update()
		return self.ticks_til_expiration


# OTHER FUNCITONS
def parse_esitmate(session : requests.Session):
	print("estimate")
	sleep(1)
	payload = api_get(session, "news")
	if( payload[0]["news_id"] % 2 == 0):
		raise Exception("ERROR: Most recent news not a volatility annoucement")
	else: 
		low = int(nth_word(payload[0]["body"], 11)[:-1])
		if low < 15:
			low = 15
		high = int(nth_word(payload[0]["body"], 13)[:-1])
		if high > 29:
			high = 29

		print("{} parsed. Range: {} ~ {}",payload[0]["headline"],low,high)
		last_news_id = payload[0]["news_id"]
		return (last_news_id,low,high)
	
def parse_announcemnt(session : requests.Session):
	print("annoucement")
	sleep(1)
	payload = api_get(session, "news")
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

def Price_option(security : dict, stock_price : float, volatility : float) -> float:
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
	T = (((int(security["stop_period"]) * 300) - (current_period -1)*300 + current_tick)/15)/365.24
	R = 0.0
	sigma = volatility/100
	print()
	print("FLAG:      ", flag)
	print("SPOT:      ", S)
	print("STRIKE:    ", K)
	print("TIME:      ", T)
	print("RISK-FREE: ", R)
	print("Volitlity: ", sigma)
	p_hat = bs(flag, S, K, T, R, sigma)
	return p_hat

def calc_delta(security : dict,stock_price : float,volatility : float ) -> float:
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
	T = (((int(security["stop_period"]) * 300) - (current_period -1)*300 + current_tick)/15)/365.24
	R = 0.0
	sigma = volatility/100

	return delta('c', S, K, T, R, sigma)

# if Trying to find probability  that we make addtional profit use: current_volatility + 1 
# if trying to find probability that we break even a week before experiration use: weeks_til_expeiration - 1 
def calc_break_even_prob(current_volatility, lower_bound, weeks_til_expeiration, avg_weekly_vol, std_dev) -> float:

	total_surplus =  math.floor((current_volatility - lower_bound)/2.0 ) # the amount of surplus volitlity we will need to get back to breakeven

	weekly_surplus = total_surplus / weeks_til_expeiration # average addtional volaitlity we need per week in order to sell for a profit at week n

	desired_weekly_volatility = weekly_surplus + avg_weekly_vol # average volaitlity we need per week in order to sell for a profit at week n

	prob_of_getting_weekly_surplus = 1 - norm.cdf((desired_weekly_volatility), avg_weekly_vol, std_dev) # the probaility of getting the nesscary 
																										# amount of additonal volatility in a given week

	breakeven_probaility = weeks_til_expeiration * prob_of_getting_weekly_surplus

	return breakeven_probaility


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

		if current_tick != 0 and current_period == 1 :
			payload = api_get(s, "news", since = 0)
			
			last_news_id = payload[0]["news_id"]
			risk_free = int(nth_word(payload[-1]["body"], 7)[:-2])
			volatility = int(nth_word(payload[-1]["body"], 29)[:-2])
			days_per_heat = int(nth_word(payload[-1]["body"], 34))

			delta_limit = int(re.sub(",", "", nth_word(payload[-2]["body"], 8).strip(',')))
			penalty_percentage = int(nth_word(payload[-2]["body"], 14)[:-1])

		next_estimate = 37
		next_annoucement = 75
		
		new_estimate = False
		new_annoucement = False

		arb_opps = []
		positions = []

						
		# set limits
		opt_gross_limit : int = 2500
		opt_net_limit : int = 1000 
		ETF_gross_limit : int = 50000
		ETF_net_limit : int = 50000 

		last_period = 1

		while(True):
			# update time
			current_tick,current_period = update_time(s)
			print(current_tick)


			# set limits
			opt_gross_limit : int = 2500
			opt_net_limit : int = 1000 
			ETF_gross_limit : int = 50000
			ETF_net_limit : int = 50000 

			#==============================PARSE NEWS==============================
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

			#===============================================================================

			#==============================PORTFOLIO MANAGEMENT==============================
			#Get list of securites 
			securities = api_get(s,"securities")

			#Set Trade Counter
			trade_counter = 0
			
			# iterate through Securities 
			for i, security in enumerate(securities):

				if security["position"] != 0:
					if security["ticker"] == "RTM":
						ETF_gross_limit -= abs(security["position"])
						ETF_net_limit -= security["position"]
					else:
						opt_gross_limit -= abs(security["position"])
						opt_net_limit -= security["position"] 
					
				weeks_til_expiration = ((int(security["stop_period"]) * 300) - (current_period -1)*300 + current_tick)/75.0

				if(new_estimate):
				
					if(volatility - low < 0.0 ):
						prob_up = 1.0
						prob_down = 0.0
					elif((volatility - high) > 1.0 ):
						prob_up = 0.0
						prob_down = 1.0
					else:
						prob_up = (volatility - low) / low
						prob_down = 1 - prob_up

					print("Prob up: ",prob_up)
					print("prob down: ", prob_down)


					if security["unrealized"] >= 0.0:
						prob_break_even = calc_break_even_prob(volatility, low+1, weeks_til_expiration, AVG_VOL, STD_DEV)
						print("prob_break_even: ",prob_break_even)
						print("total_prob: ", (prob_down * prob_break_even) + prob_up )
						if (prob_down * prob_break_even) + prob_up >= RISK_THRESH:
							print("HOLD Position ",i)
						else:
							api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = security["position"], action = "SELL" )
							print("SELL Position ",i)
					else:
						prob_break_even = calc_break_even_prob(volatility, low, weeks_til_expiration, AVG_VOL, STD_DEV)
						print("prob_break_even: ",prob_break_even)
						print("total_prob: ", (prob_down * prob_break_even) + prob_up )
						if (prob_down * prob_break_even) + prob_up >= RISK_THRESH:
							print("HOLD Position ",i)
						else:
							api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = security["position"], action = "SELL" )
							print("SELL Position ",i)

				elif(new_annoucement):
					prob_down = norm.cdf(volatility, AVG_VOL, STD_DEV)
					prob_up = 1.0 - prob_down

					print("Prob up: ",prob_up)
					print("prob down: ", prob_down)

					if security["unrealized"]  >= 0.0:
						prob_break_even = calc_break_even_prob(volatility, -1*(volatility + 2), weeks_til_expiration, AVG_VOL, STD_DEV)
						print("prob_break_even: ",prob_break_even)
						print("total_prob: ", (prob_down * prob_break_even) + prob_up )
						if (prob_down * prob_break_even) + prob_up >= RISK_THRESH:
							#buy
							print("HOLD Position ",i)
						else:
							api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = security["position"], action = "SELL" )
							print("SELL Position ",i)
					else:
						prob_break_even = calc_break_even_prob(volatility,  -1*volatility, weeks_til_expiration, AVG_VOL, STD_DEV)
						print("prob_break_even: ",prob_break_even)
						print("total_prob: ", (prob_down * prob_break_even) + prob_up )
						if (prob_down * prob_break_even) + prob_up >= RISK_THRESH:
							print("HOLD Position ",i)
						else:
							api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = security["position"], action = "SELL" )
							print("SELL Position ",i)
			
			#===============================================================================



			#==============================ARBITRAGE DETECTION==============================

			#Get list of securites 
			securities = api_get(s,"securities")

			#Set Trade Counter
			trade_counter = 0

			# iterate through Securities 
			for i, security in enumerate(securities):

				weeks_til_expiration = round((security["stop_period"] * 300) / 75.0)
				
				#ignore expired options
				if( security['stop_period'] < current_period):
					continue

				#ignore non-option securities
				if(security["ticker"] == "RTM"):
					stock_price = (security["bid"] + security["ask"])/2
					continue
				
				#--------------------------------VOLATILITY ARBITRAGE--------------------------------
				if(new_annoucement and current_tick > 220 and current_tick < 230):
					# calc Volatility 
					#volatility =  ( volatility * (1/weeks_til_expiration) ) + (AVG_VOL * (1.0-(1/weeks_til_expiration)))

					# price the option
					p_hat = Price_option(security,stock_price,volatility)
					print("-------------------------------")
					print("MRK PRICE: ", (security["bid"] + security["ask"])/2)
					print("P_HAT:     ",p_hat)
					print()

					# If underpriced 
					if(p_hat < ((security["bid"] + security["ask"])/2) - 0.05):
						
						#calc delta
						arb_delta = (100 * calc_delta(security,stock_price,volatility)) - 100

						# construct arbitrage object
						arb_opp = Arb_Opp(
							value =  p_hat - (security["bid"] + security["ask"])/2,
							delta = (100 * calc_delta(security,stock_price,volatility)) - 100,
							fee = 4.00,
							opt_gross_cost = 1,
							opt_net_cost = 1,
							ETF_gross_cost = 100,
							ETF_net_cost = -100,
							min_quantity = math.ceil( 4.00 / ( p_hat - (security["bid"] + security["ask"])/2 ) ) + 1,
							max_quantity = 100,
						)

						# add to list of arb objects
						arb_opps.append(arb_opp)
						if q*100 <= ETF_gross_limit and q <= opt_gross_limit:
							ETF_gross_limit -= q * 100
							opt_gross_limit -= q

							# Calc quantity needed to overcome Trading fee
							q = math.ceil( 4.00 / ( p_hat - (security["bid"] + security["ask"])/2 ) )

							# long the call option
							api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = q, action = "BUY" )

							# short the underlying to hedge
							api_post(s,"orders", ticker = "RTM", type = "MARKET", quantity = q*100, action = "SELL" )

							trade_counter += 2
						
					# If over priced 
					elif ( p_hat > ((security["bid"] + security["ask"])/2) + 0.05):
						
						#calc delta
						arb_delta = (100 * calc_delta(security,stock_price,volatility)) + 100

						# construct arbitrage object
						arb_opp = Arb_Opp(
							value =  p_hat - (security["bid"] + security["ask"])/2,
							delta = arb_delta if arb_delta != 0 else 0.001,
							fee = 4.00,
							opt_gross_cost = 1,
							opt_net_cost = -1,
							ETF_gross_cost = 100,
							ETF_net_cost = 100,
							min_quantity = math.ceil( 4.00 / ( p_hat - (security["bid"] + security["ask"])/2 ) ) + 1,
							max_quantity = 100,
						)

						# add to list of arb objects
						arb_opps.append(arb_opp)

						#Calc quantity needed to overcome Trading fee
						q = math.ceil( 4.00 / ( p_hat - ((security["bid"] + security["ask"])/2) ) )
						if q*100 <= ETF_gross_limit and q <= opt_gross_limit:
							ETF_gross_limit -= q * 100
							opt_gross_limit -= q
							# short the call option
							api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = q, action = "SELL" )

							# long the underlying asset to hedge
							api_post(s,"orders", ticker = "RTM", type = "MARKET", quantity = q*100, action = "BUY" )

							trade_counter += 2

				#-----------------------------------------------------------------------------------------------

				#================================================MAKE TRADES================================================
				'''
				# sort arbitrage oppertunities by the most appleaing to the least
				arb_opps.sort(key=lambda x: x.value / math.abs(x.delta), reverse=True)
				
				# set limits
				opt_gross_limit : int = 2500
				opt_net_limit : int = 1000 
				ETF_gross_limit : int = 50000
				ETF_net_limit : int = 50000 

				for i, arb_opp in enumerate(arb_opps):
					# if we decide to take the arb_opp
					# decide on quanity to take 
					# create a position
					# make trades
					continue
				'''
				#===========================================================================================================
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