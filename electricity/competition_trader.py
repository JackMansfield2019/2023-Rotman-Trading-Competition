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
		
		#global variables for each day
		elec = 0
	
		while(True):
			#updates the first solar range
			
			temp_elec = 0
			temp_elec += int(input("How many futures did you sell: "))
			temp_elec*=5
			elec+=temp_elec
			print("You currently have to tell the producer to produce this much more elec contracts: ", elec)
			if(current_tick == 150):
				print("STOP AND TELL THE PRODUCER TO PROUDCE THIS MUCH MORE ELEC CONTRACTS: ", elec)
		
			# update time
			current_tick,current_period = update_time(s)
			#print(current_tick)
			
			# parse news
			sleep(1)

if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	main()
	"""
		NOTE:	RIT Client must be running to access this API
		NOTE:	Responses are always JSON objects.
		NOTE:	Successful requests always return with HTTP code 200
		NOTE:	Unsuccessful responses have HTTP error codes between 400 and 500
	"""

