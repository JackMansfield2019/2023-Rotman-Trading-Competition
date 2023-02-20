import signal
import requests
import json
from time import sleep
import sys
import optionprice
from optionprice import Option
import pandas as pd
import matplotlib.pyplot as plt
import os
import re
import math
import py_vollib 
from py_vollib.black_scholes  import black_scholes as bs
from py_vollib.black_scholes.implied_volatility import implied_volatility as iv
from py_vollib.black_scholes.greeks.analytical import delta as delta
import csv
import numpy as np

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
	#print(payload)
	if( payload[0]["news_id"] % 2 == 0):
		raise Exception("ERROR: Most recent news not a volatility annoucement")
	else: 
		low = int(nth_word(payload[0]["body"], 11)[:-1])
		high = int(nth_word(payload[0]["body"], 13)[:-1])
		print("{} parsed. Range: {} ~ {}".format(payload[0]["headline"],low,high))
		last_news_id = payload[0]["news_id"]
		return (last_news_id,low,high)
	
def parse_announcemnt(session : requests.Session):
	print("annoucement")
	sleep(1)
	payload = api_get(session, "news")
	#print(payload)
	if( payload[0]["news_id"] % 2 == 1):
		raise Exception("ERROR: Most recent news not a volatility annoucement")
	else: 
		print("{} parsed. Volatility: {}".format(payload[0]["headline"],int(nth_word(payload[0]["body"], 8)[:-1])))
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

def remove_file(filename):
	if os.path.exists('histograms/'+filename) is True:
		os.remove('histograms/' + filename)

def main():

	vols = []
	vol_ranges = []
	
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

		announcement_ticks = [75, 150, 225]
		estimate_ticks = [37,112, 187, 262]

		# Initialize the previous event type to None
		prev_event_type = None
		anns = 0

		while(True):

			# update time
			current_tick,current_period = update_time(s)
			print(current_tick)
			#volatilities = []
			'''
			1. print to a file, comma sperated list -- done 
			2. empricaly figure out the standard deviation and find a way to print / save it somewhere -- done
			3. print the Max and Min of the volailities -- done
			4. print the average volatility as a number 
			'''
			# parse announcement
			if current_tick in announcement_ticks or (current_tick == 0 and current_period == 2):
				# Announcement event
				if prev_event_type != "announcement":
					# Only parse if not the same as previous event type
					print("announcement")
					anns += 1
					last_news_id,volatility = parse_announcemnt(s)
					vols.append(volatility)
					std_dev = np.std(vols)
					print(f'Max Volatility: {max(vols)}')
					print(f"Min Volatility: {min(vols)}")
					print(f"Avg Volatility: {sum(vols)/len(vols)}")
					print(f'Standard Deviation: {std_dev}')
					prev_event_type = "announcement"
					vol_data = pd.Series(vols)
					filename = "hist_vol.png"
					remove_file(filename)
					plt.figure()
					plt.xlabel('volatilities')
					plt.ylabel('occurences')
					vol_data.hist(bins=[15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30])
					plt.savefig('histograms/hist_vol.png')
					with open('vol_data.csv', 'w', newline='') as file:
						writer = csv.writer(file)
						writer.writerow([volatility])
						file.close()
					with open('standard_deviations.csv','w',newline='') as file:
						writer = csv.writer(file)
						writer.writerow([std_dev])


			# parse estimate
			elif current_tick in estimate_ticks and not (current_tick == 262 and current_period == 2):
				# Estimate event
				if prev_event_type != "estimate":
					# Only parse if not the same as previous event type
					print("estimate")
					last_news_id,low,high = parse_esitmate(s)
					prev_event_type = "estimate"
					vol_range = high - low
					vol_ranges.append(vol_range)
					vol_range_data = pd.Series(vol_ranges)
					filename = "hist_vol_ranges.png"
					remove_file(filename)
					plt.figure()
					plt.xlabel('volatility ranges')
					plt.ylabel('occurences')
					vol_range_data.hist()
					plt.savefig('histograms/hist_vol_ranges.png')

			sleep(1)

'''
plt.legend()
plt.title("Culmative returns vs. time")
plt.ylabel('Culmative returns')
plt.xlabel('Time (5-min intervals)')
plt.figure(2)
plt.hist(rand, bins = max(volatilities) - min(volatilities))
plt.savefig("figure2.pdf")
plt.show()
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
