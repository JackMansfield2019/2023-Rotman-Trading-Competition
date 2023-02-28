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
from py_vollib.black_scholes.greeks.analytical import theta as theta

from scipy.stats import norm
from py_lets_be_rational.exceptions import BelowIntrinsicException
from py_lets_be_rational.exceptions import AboveMaximumException



#========================================SETTINGS========================================

API_KEY = {'X-API-key': 'DV2931GT'} # Save your API key for easy access.
BASE_URL = 'http://localhost:9999/v1/'
shutdown = False

# How long to wait after submitting buy or sell orders 
SPEEDBUMP = 0.5
# Maximum number of shares to purchase each order
MAX_VOLUME = 5000
# Maximum number oforder we can sumbit
MAX_ORDERS = 5
# Allowed spread before we sell or buy shares
SPREAD = 0.15
# self tuned risk threshold
RISK_THRESH = 0.6
# average weekly volatility measured empirically
AVG_VOL = 23.514112903225808
# Stadard deviation measured empirically
STD_DEV = 3.874893968921868

OPT_GROSS_LIMIT = 2500
OPT_NET_LIMIT   = 1000 
ETF_GROSS_LIMIT = 50000
ETF_NET_LIMIT   = 50000 

TICKS_PER_PERIOD = 300
TOTAL_PERIODS    = 2

RISK_FREE = 0.0


#========================================GLOBALS========================================

# Trader info
global trader_id
global first_name
global last_name
global current_nlv

#limits info
global opt_gross_limit 
global opt_net_limit 
global ETF_gross_limit
global ETF_net_limit
global total_current_delta

# time info
global current_tick
global current_period

# news info
global current_volatility
global current_low
global current_high

#======================================== API FUNCTIONS ========================================
# this class definition allows us to print error messages and stop the program when needed
class ApiException(Exception):
	pass

#this signal handler allows us for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
	global shutdown
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	shutdown = True

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

#======================================== OBJECTS ========================================

class Arb_Opp:
	def __init__(self, s : requests.Session, og_expected_vol: float, og_implied_vol: float, og_price: float, og_p_hat: float, 
				og_delta: float, og_theta: float, fee: float, opt_gross_cost: int, opt_net_cost: int, 
				 ETF_gross_cost: int, ETF_net_cost: int, ticks_til_expiration: int, prob_of_profit: float, portfolio: dict[str, int]):
		# Session
		self.s = s

		# Volatility variables
		self.og_expected_vol: float = og_expected_vol
		self.current_expected_vol: float = og_expected_vol
		self.og_implied_vol: float = og_implied_vol
		self.current_implied_vol: float = og_implied_vol
		self.og_vol_diff: float = og_expected_vol - og_implied_vol
		self.current_vol_diff: float = self.current_expected_vol - self.current_implied_vol

		# Price variables
		self.og_price: float = og_price
		self.current_price: float = og_price
		self.og_p_hat: float = og_p_hat
		self.current_p_hat: float = og_p_hat
		self.og_arb_value: float = og_p_hat - og_price
		self.current_arb_value: float = self.current_p_hat - self.current_price

		# Quantity variables
		self.quantity: int = 0
		self.min_quantity: int = math.ceil(fee / abs(self.current_arb_value)) + 1
		self.max_quantity: int = 100

		# Relevant Greeks
		self.og_delta: float = og_delta
		self.current_delta: float = og_delta
		self.og_theta: float = og_theta
		self.current_theta: float = og_theta

		#Limit Variables
		self.opt_gross_cost: int = opt_gross_cost
		self.opt_net_cost: int = opt_net_cost
		self.ETF_gross_cost: int = ETF_gross_cost
		self.ETF_net_cost: int = ETF_net_cost
		
		# Time variables
		self.ticks_til_expiration: int = ticks_til_expiration
		self.weeks_til_expiration: int = math.floor(ticks_til_expiration / 75)

		# Other variables
		self.fee: float = fee
		self.prob_of_profit: float = prob_of_profit
		self.portfolio: dict[str, int] = portfolio
	
	def update(self):
		rtm = api_get(self.s,"securities", ticker = "RTM")

		# grab current underlying stock price 
		stock_price = (rtm["bid"] + rtm["ask"])/2.0

		# Calulate current_expected_vol 
		self.current_expected_vol  = (current_volatility*(1/self.weeks_til_expiration) + (1-(1/self.weeks_til_expiration))*AVG_VOL)/100

		# Calulate the Current Implied volatility
		try:
			self.current_implied_vol = calc_iv(api_get(self.s,"securities", ticker = list(self.portfolio.keys())[0]) ,stock_price)
		except BelowIntrinsicException as e:
			self.current_implied_vol = 0.001

		# Calc differnce in current volatility estimates 
		self.current_vol_diff = self.current_expected_vol - self.current_implied_vol

		self.ticks_til_expiration = -9999

		# iterate through all securities in the portfolio
		for key, value in self.portfolio.items():
			# retieve the current info about the current security 
			security = api_get(self.s,"securities", ticker = value)

			#Calculate the market value of each option in the portfolio using the current market price and the number of contracts held.
			self.current_price += value * (security["bid"] + security["ask"])/2.0

			# Reprice the option with respect to the current expected volatility
			self.current_p_hat += value * Price_option(security, stock_price,self.current_expected_vol)

			# Calulate the delta of the entire portfolio
			self.current_delta += (value * calc_delta(security, stock_price,self.current_expected_vol) ) * 100

			# Calulate the Theta(time decay) of the entire portfolio
			self.current_theta += (value * calc_theta(security, stock_price, self.current_expected_vol))

			# Set the ticks til experiation to be equal to the ticks til experiation of the longest positon in the portfolio
			if ((int(security["stop_period"]) * 300) - (current_period - 1)*300 + current_tick) > self.ticks_til_expiration:
				self.ticks_til_expiration = ((int(security["stop_period"]) * 300) - (current_period - 1)*300 + current_tick)

		# Calc the value one instance of this arbitrage portfolio can construct
		self.current_arb_value = self.current_p_hat - self.current_price

		# Calc Weeks_til_experiation
		self.weeks_til_expiration = math.floor(self.ticks_til_expiration / 75)

		self.prob_of_profit = 1.0
		'''
		self.prob_of_profit = prob_of_profit =  prob_hitting_p_hat(
								security = security,
								p_hat = self.current_p_hat,
								ticks_til_expiration = self.ticks_til_expiration,
								stock_price = stock_price,
							)
		'''
		
	def add_to_holdings(self):
		self.update()
		self.max_quanity = self.quantity
		pass
	def buy(q):
		
		return
		

#======================================== HELPER FUNCTIONS ========================================
def nth_word(string : str, n: int):
	res = re.findall(r'\S+', string)
	return res[n-1]

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

	S : float = stock_price
	K : int   = int(security["ticker"][5:])
	T : float = ( ((int(security["stop_period"]) * 300) - (current_period - 1)*300 + current_tick) /15.0)/365.24
	R : float = RISK_FREE
	sigma : float = volatility
	
	print()
	print("    ",security["ticker"])
	print("FLAG:      ", flag)
	print("SPOT:      ", S)
	print("STRIKE:    ", K)
	print("TIME:      ", T)
	print("RISK-FREE: ", R)
	print("Volitlity: ", sigma)
	
	p_hat = bs(flag, S, K, T, R, sigma)
	return p_hat

def calc_iv(security : dict, stock_price : float) -> float:
	global current_tick
	global current_period
	
	if(security["ticker"][4] == 'C'):
		flag = 'c'
	else:
		flag = 'p'

	P : float = (security['bid'] + security['ask'])/2.0
	S : float = stock_price
	K : int   = int(security["ticker"][5:])
	T : float = ( ((int(security["stop_period"]) * 300) - (current_period - 1)*300 + current_tick) /15.0)/365.24
	R : float = RISK_FREE

	print()
	print("     ",security["ticker"])
	print("PRICE:     ", P)
	print("SPOT:      ", S)
	print("STRIKE:    ", K)
	print("TIME:      ", T)
	print("RISK-FREE: ", R)
	print("FLAG:      ", flag)
	return iv(P,S,K,T,R,'c')

def calc_delta(security : dict, stock_price : float, volatility : float ) -> float:
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

def calc_theta(security : dict, stock_price : float, volatility : float) -> float:
	global current_tick
	global current_period
	global trader_id
	global first_name
	global last_name
	
	if(security["ticker"][4] == 'C'):
		flag = 'c'
	else:
		flag = 'p'

	S : float = stock_price
	K : int   = int(security["ticker"][5:])
	T : float = ( ((int(security["stop_period"]) * 300) - (current_period - 1)*300 + current_tick) /15.0)/365.24
	R : float = RISK_FREE
	sigma : float = volatility/100.0
	#annual_theta_calc = theta(flag, S, K, T, R, sigma) * 365
	return theta(flag, S, K, T, R, sigma)

 
def calc_break_even_prob(current_volatility, lower_bound, weeks_til_expeiration, avg_weekly_vol, std_dev) -> float:

	total_surplus :float =  math.floor((current_volatility - lower_bound)/2.0 ) # the amount of surplus volitlity we will need to get back to breakeven

	weekly_surplus : float = total_surplus / weeks_til_expeiration # average addtional volaitlity we need per week in order to sell for a profit at week n

	desired_weekly_volatility :float = weekly_surplus + avg_weekly_vol # average volaitlity we need per week in order to sell for a profit at week n

	prob_of_getting_weekly_surplus : float = 1.0 - norm.cdf((desired_weekly_volatility), avg_weekly_vol, std_dev) # the probaility of getting the nesscary 
																										# amount of additonal volatility in a given week
	breakeven_probaility : float = weeks_til_expeiration * prob_of_getting_weekly_surplus

	return breakeven_probaility

# calulates the probaility that the future news annoucments will be large enough to over come theta and hit a price p_hat at the time of some future news annocument
def prob_hitting_p_hat(security : dict, p_hat : float, ticks_til_expiration : int, stock_price : float, vol_range : tuple = None):
	'''
	security : the option in question
	p_hat : the price we want the option to hit
	weeks_til expeiration : the amount of future news annoucments we have to hit it
	stock_price : current price of the underlying
	theta : time decay of the option per day
	'''
	weeks_til_expiration : int = math.floor(ticks_til_expiration / 75)

	if(security["ticker"][4] == 'C'):
		flag = 'c'
	else:
		flag = 'p'

	prev_probabilities = []

	for i in range(weeks_til_expiration):
		try:
			
			vol_needed_to_hit_phat = iv(
										price = p_hat,
										S = stock_price, # Assumes stock price stays constant b/c they told us it has mean of 0
										K = int(security["ticker"][5:]),
										t = ( (ticks_til_expiration - (75 * (weeks_til_expiration - i))) /15.0)/365.24,
										r = RISK_FREE,
										flag = flag,
									)
			'''
			print()
			print("     ",security["ticker"])
			print("PRICE:     ", p_hat)
			print("SPOT:      ", stock_price)
			print("STRIKE:    ", int(security["ticker"][5:]))
			print("TIME:      ", ( (ticks_til_expiration - (75 * (weeks_til_expiration - i))) /15.0)/365.24)
			print("RISK-FREE: ", RISK_FREE)
			print("FLAG:      ", flag)
			'''
		except BelowIntrinsicException as e:
			prev_probabilities.append(1.0)
			continue
		except AboveMaximumException as e:
			prev_probabilities.append(0.0)
			continue
		
		if vol_needed_to_hit_phat == 0.0:
			prev_probabilities.append(0.0)
			continue

		# if there is a specfic probaility for the 1st week that the user wants us to consider 
		if i == 0 and vol_range != None:
			# if vol for first week is gaurenteed
			if vol_range[0] == vol_range[1]:
				if vol_range[0] >= vol_needed_to_hit_phat:
					prob_up = 1.0
				else:
					prob_up = 0.0
			# If we have a range of what the first weeks vol could be
			else:
				# if the range is equal to or greater than my volatility estimate  
				if(vol_needed_to_hit_phat <= vol_range[0]):
					prob_up = 1.0
					prob_down = 0.0
				# if the range is stictly less than my volatility estimate  
				elif(vol_needed_to_hit_phat > vol_range[1]):
					prob_up = 0.0
					prob_down = 1.0
				else:
					prob_down = (vol_needed_to_hit_phat - vol_range[0]) / 6
					prob_up = 1.0 - prob_down

			#print("Prob up: ",prob_up)
			prev_probabilities.append(prob_up)
			continue

		weekly_vol_needed_to_hit_phat : float = vol_needed_to_hit_phat * math.sqrt(1/52.1429)

		prob_of_getting_weekly_vol_needed_to_hit_phat_on_a_given_week : float = 1.0 - norm.cdf(weekly_vol_needed_to_hit_phat, AVG_VOL, STD_DEV)
		
		prob_of_getting_weekly_vol_needed_to_hit_phat_each_week : float =  math.pow(prob_of_getting_weekly_vol_needed_to_hit_phat_on_a_given_week,(weeks_til_expiration - i))
		
		#add to list of previous probabilities
		prev_probabilities.append(prob_of_getting_weekly_vol_needed_to_hit_phat_each_week)

	return sum(prev_probabilities) / len(prev_probabilities)

#======================================== CASE FUNCTIONS ========================================

def update_time(session : requests.Session):
	global current_tick
	global current_period
	payload = api_get(session, "case")
	current_tick = int(payload["tick"])
	current_period = int(payload["period"])
	return current_tick,current_period

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

		print("{} parsed. Range: {} ~ {}".format(payload[0]["headline"],low,high))
		last_news_id = payload[0]["news_id"]
		return (last_news_id,low,high)
	
def parse_announcemnt(session : requests.Session):
	print("annoucement")
	sleep(1)
	payload = api_get(session, "news")
	if( payload[0]["news_id"] % 2 == 1):
		raise Exception("ERROR: Most recent news not a volatility annoucement")
	else: 
		print("{} parsed. Volatility: {}".format(payload[0]["headline"],int(nth_word(payload[0]["body"], 8)[:-1])))
		last_news_id = payload[0]["news_id"]
		return (last_news_id,float(nth_word(payload[0]["body"], 8)[:-1]))

#========================================== MAIN ==========================================

def main():
	# Bring in Globals

	# Trader info
	global trader_id
	global first_name
	global last_name
	global current_nlv

	# Limits info
	global opt_gross_limit 
	global opt_net_limit 
	global ETF_gross_limit
	global ETF_net_limit
	global total_current_delta

	# Time info
	global current_tick
	global current_period
	

	# News info
	global last_news_id
	global days_per_heat
	global delta_limit
	global penalty_percentage

	global current_volatility
	global current_low
	global current_high
 

	with requests.Session() as s: # Create a Session object to manage connections and requests to the RIT client.
		
		s.headers.update(API_KEY) # Add the API key to the Session to authenticate with every request

		# SET TRADER VARIABLES
		payload = api_get(s, "trader")
		trader_id = payload["trader_id"]
		first_name = payload["first_name"]
		last_name = payload["last_name"]
		current_nlv = payload["nlv"]

		#INITIALIZE LIMIT VARIABLES
		opt_gross_limit = OPT_GROSS_LIMIT
		opt_net_limit   = OPT_NET_LIMIT
		ETF_gross_limit = ETF_GROSS_LIMIT
		ETF_net_limit   = ETF_NET_LIMIT

		# INITIALIZE TIME VARIABLES
		payload = api_get(s, "case")
		current_tick = int(payload["tick"])
		current_period = int(payload["period"])
		
		# INITIALIZE LOCAL VARIABLES

		# Keep track of the tick of the next estimate & annoucemnt
		next_estimate = 37
		next_annoucement = 75
		
		#Flags Informing us of a new estimate
		new_estimate = False
		new_annoucement = False

		last_period = 1
		prev_tick = current_tick

		# Flag recoding wethre or not we parsed the inital news
		parsed_first_news = False

		# Initlaize my portfolio of Arb_Opps
		holdings : list[Arb_Opp]= []
		

		# MAIN LOOP
		while(True):
			total_current_delta = 0
			# update time
			current_tick,current_period = update_time(s)
			if current_tick == prev_tick:
				sleep(SPEEDBUMP)
				continue
			else:
				prev_tick = current_tick
				print(current_tick, " ", current_period)

			#========================================== PARSE NEWS ==========================================
			last_news_id       = 0
			# INITIALIZE NEWS VARIABLES
			
			if current_tick > 0 and not parsed_first_news:
					payload = api_get(s, "news", since = 0)	
					

					delta_limit        = int(re.sub(",", "", nth_word(payload[-2]["body"], 8).strip(',')))
					penalty_percentage = int(nth_word(payload[-2]["body"], 14)[:-1])

					current_volatility = float(nth_word(payload[-1]["body"], 29)[:-2])
					
					# set the flag
					parsed_first_news = True
			
			if(current_tick > 262):
				next_estimate = 37
				next_annoucement = 0
 
			if (current_tick % 75 >= 37 and current_tick >= next_estimate and current_tick < 263):
				if(current_period == 5 and current_tick > 261):
					continue 
				print(last_news_id)
				last_news_id,low,high = parse_esitmate(s)
				next_estimate = math.floor( (last_news_id - ((current_period - 1) *9))/2 * 75)
				new_estimate = True
			elif( current_tick % 75 < 37 and current_tick >= next_annoucement and current_tick < 251):
				print(last_news_id)
				last_news_id,current_volatility = parse_announcemnt(s)
				next_annoucement = (last_news_id - ((current_period -1)*9))/2 * 75
				new_annoucement = True

			#========================================== ARBITRAGE DETECTION ==========================================
			
			# Retrieve list of securites 
			securities = api_get(s,"securities")
			
			pos_arb_counter = 0
			neg_arb_counter = 0

			new_arb_opps = []
			pos_delta_arb_opps : list[Arb_Opp]= []
			neg_delta_arb_opps : list[Arb_Opp]= []

			trade_counter = 0
			# Iterate through each Securities 
			for i, security in enumerate(securities):

				# update time to ensure we are on the right tick
				current_tick,current_period = update_time(s)
				
				# Calulate the options weeks til expiration
				ticks_til_expiration : int = (security["stop_period"] * 300) - ((current_period -1 ) * 300) + current_tick

				# Calulate the options weeks til expiration
				weeks_til_expiration : int = math.floor(((security["stop_period"] * 300) - ((current_period -1 ) * 300) + current_tick ) / 75.0)

				# Ignore expired options
				if( security['stop_period'] < current_period):
					continue

				# Ignore non-option securities
				if(security["ticker"] == "RTM"):
					stock_price = (security["bid"] + security["ask"])/2
					continue

				# Parse the type of the option
				if(security["ticker"][4] == 'C'):
					option_type = 'c'
				else:
					option_type = 'p'

				# Calulate Market_Price for the current option
				market_price : float = (security["bid"] + security["ask"])/2.0

				# Parse the Strike price
				strike_price : int = int(security["ticker"][5:])
				
				# Detect Call Exercise Arbitrage
				if option_type == 'c' and current_tick > 1:
					if market_price < stock_price - strike_price:
						if (stock_price - strike_price) - market_price > 0.01:
							print()
							print("-------------------------------")
							print("CALL EXERCISE ARBITRAGE!")
							print("ARB VALUE :", (stock_price - strike_price) - market_price)
							print("-------------------------------")

							# Buy the call option
							api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = 1, action = "BUY" )

							# short the underlying asset to hedge
							api_post(s,"orders", ticker = "RTM", type = "MARKET", quantity = 100, action = "SELL" )
							continue

				# Detect Put Exercise Arbitrage
				if option_type == 'p' and current_tick > 1:
					if market_price < strike_price - stock_price:
						if (strike_price - stock_price) - market_price > 0.01:
							print()
							print("-------------------------------")
							print("PUT EXERCISE ARBITRAGE!")
							print("ARB VALUE : ", (strike_price - stock_price) - market_price)
							print("-------------------------------")
							
							# Buy the put option
							api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = 1, action = "BUY" )

							# long the underlying asset to hedge
							api_post(s,"orders", ticker = "RTM", type = "MARKET", quantity = 100, action = "BUY" )
							continue
				
				# Calulate our volatiity estimate
				if(new_annoucement):
					estimated_volatility : float =  ( (current_volatility * (75.0/ticks_til_expiration)) + (1.0 - (75.0/ticks_til_expiration)) * AVG_VOL )/100.0
				elif(new_estimate):
					estimated_volatility : float = ( ((low + high)/2.0) * (75.0/ticks_til_expiration) + (1.0 - (75.0/ticks_til_expiration)) * AVG_VOL )/100.0
					

				if(new_annoucement or new_estimate and current_tick > 76):

					'''
					print()
					print("weeks til expiration: ", weeks_til_expiration)
					print("current_volatility:   ", current_volatility)
					print("current vol factor:   ", current_volatility*(1/weeks_til_expiration))
					print("AVG_VOL Factor:       ", (1-(1/weeks_til_expiration))*AVG_VOL)
					print("Estimated volatility: ", estimated_volatility)
					'''

					# Calulate the securities implied volatility
					try:
						implied_volatility = calc_iv(security,stock_price)
					except BelowIntrinsicException as e:
						print('The volatility is below the intrinsic value.')
						if str(e) != 'The volatility is below the intrinsic value.':
							raise
						if option_type == 'c':
							if market_price < stock_price - strike_price:
								print("Call Exercise Arbitrage!")
						if option_type == 'p':
							if market_price < strike_price - stock_price:
								print("Put Exercise Arbitrage!")
						implied_volatility = 0.00001
					except AboveMaximumException as e:
						if option_type == 'c':
							if market_price < stock_price - strike_price:
								print("Call Exercise Arbitrage!")
						if option_type == 'p':
							if market_price < strike_price - stock_price:
								print("Put Exercise Arbitrage!")
						implied_volatility = 999999

					implied_volatility = max (0.001,implied_volatility)

					print("-------------------------------")
					print("Implied Vol:    ", implied_volatility)
					print("Estimated Vol:  ", estimated_volatility)
					if (estimated_volatility - implied_volatility >= 0):
						print("VOL_VALUE:      +{}".format( estimated_volatility - implied_volatility))
					else:
						print("VOL_VALUE:       {}".format( estimated_volatility - implied_volatility))

					p_hat = Price_option(security,stock_price,estimated_volatility)
					print("-------------------------------")
					print("MRK PRICE: ", market_price)
					print("P_HAT:     ", p_hat)
					if (p_hat - market_price >= 0):
						print("ARB_VALUE: +{}".format( p_hat - market_price))
					else:
						print("ARB_VALUE: {}".format( p_hat - market_price))

					print()

					#----------------------------CONSTRUCT ARBITRAGE----------------------------

					# If under priced
					if implied_volatility < estimated_volatility - .015 and p_hat - market_price >= SPREAD:
						# Increment number of negative arbitrage elements
						neg_arb_counter += 1

						# construct arbitrage object
						arb_opp = Arb_Opp(
							s = s,
							og_expected_vol = estimated_volatility,
							og_implied_vol = implied_volatility, 
							og_price = market_price, 
							og_p_hat = p_hat, 
							og_delta = calc_delta(security,stock_price,estimated_volatility), 
							og_theta = calc_theta(security,stock_price,estimated_volatility), 
							fee = 2.00, 
							opt_gross_cost = 1, 
							opt_net_cost = 1, 
							ETF_gross_cost = 0, 
							ETF_net_cost = 0, 
							ticks_til_expiration = ticks_til_expiration, 
							prob_of_profit =  1.0, 
							portfolio = {
								security["ticker"] : 1
							},
						)					
						# Calc quantity needed to overcome Trading fee and add 3
						q = math.ceil( 2.00 / ( p_hat - (security["bid"] + security["ask"])/2 ) ) + 3
						arb_opp.quantity =  q

						# long the call option
						api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = q, action = "BUY" )
						
						# short the underlying to hedge
						api_post(s,"orders", ticker = "RTM", type = "MARKET", quantity = q*100, action = "SELL" )

						total_current_delta += arb_opp.current_delta * q * 100
						holdings.append(arb_opp)

						trade_counter += 2

					#if over priced 
					elif implied_volatility > estimated_volatility + .015 and p_hat - market_price <= -SPREAD:
						pos_arb_counter += 1

						# construct arbitrage object
						arb_opp = Arb_Opp(
							s = s,
							og_expected_vol = estimated_volatility,
							og_implied_vol = implied_volatility, 
							og_price = market_price, 
							og_p_hat = p_hat, 
							og_delta = -1 * calc_delta(security,stock_price,estimated_volatility), 
							og_theta = -1 * calc_theta(security,stock_price,estimated_volatility), 
							fee = 2.00, 
							opt_gross_cost = 1, 
							opt_net_cost = -1, 
							ETF_gross_cost = 0, 
							ETF_net_cost = 0, 
							ticks_til_expiration = ticks_til_expiration, 
							prob_of_profit = 1.0, 
							portfolio = {
								security["ticker"] : -1
							}
						)
						holdings.append(arb_opp)

						#Calc quantity needed to overcome Trading fee
						q = math.ceil( 2.00 / ( p_hat - ((security["bid"] + security["ask"])/2) ) ) + 3
						arb_opp.quantity = q
						api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = q, action = "SELL" )

						# long the underlying asset to hedge
						api_post(s,"orders", ticker = "RTM", type = "MARKET", quantity = q*100, action = "BUY" )

						total_current_delta += arb_opp.current_delta * q * 100

						trade_counter += 2

				if(trade_counter > 8 and i != len(securities)-1 ):
					sleep(1)
					trade_counter = 0



			if(new_annoucement or new_estimate):
				print("total securities: ", len(securities))
				print("arb_counter:      ", pos_arb_counter + neg_arb_counter)
				print("pos_arb_counter:  ", pos_arb_counter)
				print("neg_arb_counter:  ", neg_arb_counter)

				print()
				print()
			#========================================== PREPROCESS FILTERING ==========================================

			#========================================== OPTIMIZATION PROBLEM ==========================================

			#========================================== PORTFOLIO MANAGEMENT ==========================================
			# update time to ensure we are on the right tick
			current_tick,current_period = update_time(s)
			
			# Calulate the options weeks til expiration
			ticks_til_expiration : int = (security["stop_period"] * 300) - ((current_period -1 ) * 300) + current_tick

			# Calulate the options weeks til expiration
			weeks_til_expiration : int = math.floor(((security["stop_period"] * 300) - ((current_period -1 ) * 300) + current_tick ) / 75.0)

			# Ignore non-option securities
			'''
			rtm = api_get(s,"securities", ticker = "RTM")

			# grab current underlying stock price 
			stock_price = (rtm["bid"] + rtm["ask"])/2.0

			for i , arb_op in enumerate(holdings):
				obj = api_get(s,"securities", ticker = arb_opp.portfolio[0])
				current_price = (obj["bid"] + obj["ask"])/2
				if current_price >= arb_op.current_p_hat:
					if(arb_opp.opt_net_cost > 1):
						api_post(s,"orders", ticker = arb_opp.portfolio[0], type = "MARKET", quantity =  arb_opp.quantity, action = "SELL" )
					else:
						api_post(s,"orders", ticker = arb_opp.portfolio[0], type = "MARKET", quantity =  arb_opp.quantity, action = "BUY" )
			'''


			'''
			for i, security in enumerate(securities):
				if(new_estimate):
					# if the range is equal to or greater than my volatility estimate  
					if(estimated_volatility <= low):
						prob_up = 1.0
						prob_down = 0.0
					# if the range is stictly less than my volatility estimate  
					elif(estimated_volatility > high):
						prob_up = 0.0
						prob_down = 1.0
					else:
						prob_down = (estimated_volatility - low) / 6
						prob_up = 1.0 - prob_down
				
					if prob_down >= RISK_THRESH and security["position"] > 0:
						api_post(s,"orders", ticker = security["ticker"], type = "MARKET", quantity = math.floor(prob_down * security["position"]), action = "SELL" )
			'''

			
			#========================================== PLACE TRADES ==========================================
			
			new_estimate = False
			new_annoucement = False

if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	main()
	"""
		NOTE:	RIT Client must be running to access this API
		NOTE:	Responses are always JSON objects.
		NOTE:	Successful requests always return with HTTP code 200
		NOTE:	Unsuccessful responses have HTTP error codes between 400 and 500
	"""
