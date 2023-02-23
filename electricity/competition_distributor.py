import signal
import requests
import json
from time import sleep
import sys
import re
import math
import config_electricity

# this class definition allows us to print error messages and stop the program when needed
class ApiException(Exception):
	pass

#this signal handler allows us for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
	global shutdown
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	shutdown = True


API_KEY = {'X-API-key': '8CVIPIDF'} # Save your API key for easy access.
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
		ELEC = 0
		day = 1
		old_day = -1
		AT_Range = []

		
		Second_AT_Check = False
		AT = -1

		
		while(True):
			#grabs most recent news release
			news = api_get(s, "news", since = 0)
			last_news_id = int(news[0]["news_id"])
			day = int(news[0]["period"])
			
			#updates the first Averate temperature range
			if(current_tick >= 1 and AT_Range ==[] and day!=old_day):
				for id in range( 0, last_news_id):
					if "TEMPERATURE" in news[id]["headline"] and int(news[id]["tick"]) < 8:
						temp_solar = news[id]["body"].split()
						for word in temp_solar:
							if word.isnumeric():
								AT_Range.append(int(word))
								if len(AT_Range) > 1:
									AT = (AT_Range[0]+AT_Range[1])/2
									print("First estimated ELEC-DayX needed from consumers: ", (200-15*AT + 0.8*AT*AT - 0.01*AT*AT*AT))
									print("First forecast of maximum futures you can hold: ", (200-15*AT_Range[1] + 0.8*AT_Range[1]*AT_Range[1] - 0.01*AT_Range[1]*AT_Range[1]*AT_Range[1])/5)
									break
						break

			if(current_tick >= 90 and AT_Range !=[] and not Second_AT_Check):	
				for id in range(0, last_news_id):
					if "TEMPERATURE" in news[id]["headline"] and int(news[id]["tick"]) < 100:
						temp_solar = news[id]["body"].split()
						for word in temp_solar:
							if word.isnumeric():
								if(Second_AT_Check):
									if AT_Range[1] > int(word):
										AT_Range[1] = int(word)
										AT = (AT_Range[0]+AT_Range[1])/2
										print("Second estimated ELEC-DayX needed from consumers: ", ((200-15*AT + 0.8*AT*AT - 0.01*AT*AT*AT)))
										print("Second forecast of maximum futures you can hold: ", (200-15*AT_Range[1] + 0.8*AT_Range[1]*AT_Range[1] - 0.01*AT_Range[1]*AT_Range[1]*AT_Range[1])/5)
									break
								else:
									if AT_Range[0] < int(word):
										AT_Range.append(int(word))
									Second_AT_Check = True
						break
						
			
			if(current_tick >= 148 and Second_AT_Check):
				if "TEMPERATURE" in news[id]["headline"] and int(news[id]["tick"]) < 153:
					Temp = news[id-1]["body"].split()
					for word in Temp:
						if word.isnumeric():
							AT = int(word)
							Second_AT_Check = False
							AT_Range = []
							old_day = day
							print("Exact ELEC-DayX needed from consumers and maximum futures you can hold: ", (200-15*AT + 0.8*AT*AT - 0.01*AT*AT*AT))
							config_electricity.ELEC +=200-15*AT + 0.8*AT*AT - 0.01*AT*AT*AT
							break
				
									
			# update time
			current_tick,current_period = update_time(s)
			print(current_tick)
			
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