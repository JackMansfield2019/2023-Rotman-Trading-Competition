import signal
import requests
import json
from time import sleep
import sys
import re
import math



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

        #--------------------------------------------------------------------------------------------------

		payload = api_get(s, "news", since = 0)
		
		last_news_id = payload[0]["news_id"]
		#risk_free = int(nth_word(payload[-1]["body"], 7)[:-2])

		while(True):

			# update time
			current_tick,current_period = update_time(s)
			print(current_tick)
			
			# parse news
			sleep(1)

'''
Elec = 0
'''

'''
current day = 1
Producer days 1-4
grab latest news 
if the ticker==1 or 2 
    check for the intial forecast 
    if the headline has sunlight in it
        store range in Solar_Range : list
        Set estimated solar hours by adding upper and lower bound and dividing by two
        caclulate for ELEC-dayX contracts by multiplying the solar hours by 6
if the ticker==89 or 90 
    grab latest news 
    if the headline has sunlight in it
        if the lower bound > solar range[0]
            set lower bound = solar range[0] 
        if the upper bound < solar range[1]
            set upper bound = solar range[1]
        Calculate solar hours by adding solar range[0] and solar range[1] and dividing by 2
        Calculate estimated ELEC_dayx contracts by multiplying the solar hours by 6

if the ticker==149 or 150 
    grab latest news for price volume bulletin 
    grab -1 of that index news for final amount of sunlight 
    use that to calculate the final amount of ELEC-dayX
    Subtract the final amount from the variable ELEC
    Display the NG needed to be purchased by multiplying the ELEC variable by 40. 

if the ticker>=180
    grab latest news for price volume bulletin 
    if latest news had in headline price volume bulletin 2
        set current_tick = 0 while incrementing day by 1

day 5 specific:
if ticker == 149 or 150 
    grab latest news
    if latest news has in it headline price volume bulletin
        (Lower RAE + upper RAE)/2 = Average RAE
        if ARAE + 5 > ELEC-F
            buy as much ELEC-F
        if ARAE > 8+NG
            buy and produce as much NG
        if holding NG 
            use that as well for production
'''

'''
demand = 0
current day =1
Distributor days 1-4
Set lower tn  = 0 and upper tn  = 0, AT = 0 

if tick == 1 or 2 
    buy from the market the amount needed to sell, which is stored in the demand variable
    grab the first range of average temperatures and put this in list called Range_AT 
    variable At = (Range_AT[0] + RangeAT[1])/2
    Calculate demand through plugging AT into the formula 200-15AT + 0.8AT^2 - 0.01AT^3
if tick == 89 or 90 
    grab the second range
    if the lower bound > Range_AT[0]
        set lower bound = Range_AT[0] 
    if the upper bound < Range_AT[1]
        set upper bound = Range_AT[1]
    Calculate demand through plugging AT into the formula 200-15AT + 0.8AT^2 - 0.01AT^3

if tick == 149 or 150 
    calculate consumer demand using the exact AT scraped using 200-15AT + 0.8AT^2 - 0.01AT^3
    Store this in the variable demand
    pass this information to the producer through adding this value to the overall ELEC count

'''

'''
current day =1
debt = 0
owed = 0
Trader
Check if there is a tender each tick
    if selling ELEC-F for > 70 per ELEC-F
        accept the tender
        Add amount of ELEC-F to the ELEC variable
        Add the amount to the debt variable
Check if owed > 0 each tick:
    check if trader bought any contract, if they did subtract from owed amount
    display owed amount if tick%10 == 0

if tick >= 180:
    owed = debt
    debt = 0
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
