import signal
import requests
import json
from time import sleep
import sys


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
#SPEEDBUMP = 0.5
# Maximum number of shares to purchase each order
#MAX_VOLUME = 5000
# Maximum number oforder we can sumbit
#MAX_ORDERS = 5
# Allowed spread before we sell or buy shares
#SPREAD = 0.05



def get(session : requests.Session, endpoint: str, **kwargs : dict) -> dict:
	'''
	Makes a custom GET request to a specified endpoint in the RIT API

		Parameters:
			Session (requests.Session): Current Session Object
			endpoint (String): name of the end point ex "case" or "assets/history" or "orders/{insert your id here}"
			kwargs (Dict): Dictionary that maping each keyword to the value that we pass alongside it
		
		Returns:
			Payload (Dict): Dictonary contining the JSON returned from the endpoint
	
		Example Usage:
			get( s, "case")
			get( s, "assets/history", ticker = "RTM", period = "14", limit ="100" )
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.get(URL, params=kwargs)

	if resp.ok:
		payload : dict = resp.json()
		# print('API GET SUCCESSFUL')

	else:
		print('API GET FAILED')
		if(resp.status_code == 401):
			raise ApiException("Unauthorized")
		elif(resp.status_code == 429):
			raise ApiException("Rate Limit Exceeded")
		elif(resp.status_code == 500):
			raise ApiException("Unexpected error 500 (internal server error) parameters may be wrong")
		elif(resp.status_code == 400):
			raise ApiException("Bad Request, parameters may be wrong")
		else:
			raise ApiException("other error code in orders: ", resp.status_code)
		
	return payload

def post(session : requests.Session, endpoint: str, **kwargs : dict) -> dict:
	'''
	Makes a custom POST request to a specified endpoint in the RIT API

		Parameters:
			Session (requests.Session): Current Session Object
			endpoint (String): name of the end point ex "case" or "assets/history" or "orders/{insert your id here}"
			kwargs (Dict): Dictionary that maping each keyword to the value that we pass alongside it
		
		Returns:
			Payload (Dict): Dictonary contining the JSON returned from the endpoint
	
		Example Usage:
			post( s, "orders", ticker = "RTM", type = "LIMIT", quantity = "100", action = "SELL")
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.post(URL, params=kwargs)

	if resp.ok:
		payload : dict = resp.json()
		# print('API POST SUCCESSFUL')
	else:
		print('API POST FAILED')
		if(resp.status_code == 401):
			raise ApiException("Unauthorized")
		elif(resp.status_code == 429):
			raise ApiException("Rate Limit Exceeded")
		elif(resp.status_code == 500):
			raise ApiException("Unexpected error 500, possible error could include limit order without price specified")
		elif(resp.status_code == 400):
			raise ApiException("Bad Request")
		else:
			raise ApiException("other error code in orders: ", resp.status_code)

	return payload

def delete(session : requests.Session, endpoint: str, **kwargs : dict) -> dict:
	'''
	Makes a custom DELETE request to a specified endpoint in the RIT API

		Parameters:
			Session (requests.Session): Current Session Object
			endpoint (String): name of the end point ex "case" or "assets/history" or "orders/{insert your id here}"
			kwargs (Dict): Dictionary that mapping each keyword to the value that we pass alongside it
		
		Returns:
			Payload (Dict): Dictionary continuing the JSON returned from the endpoint
	
		Example Usage:
			delete( s, "/tenders/{id}")
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.post(URL, params=kwargs)

	if resp.ok:
		payload : dict = resp.json()
		# print('API DELETE SUCCESSFUL')

	else:
		print('API DELETE FAILED')
		if(resp.status_code == 401):
			raise ApiException("Unauthorized")
		elif(resp.status_code == 429):
			raise ApiException("Rate Limit Exceeded")
		elif(resp.status_code == 500):
			raise ApiException("Unexpected error 500 (internal server error)")
		elif(resp.status_code == 400):
			raise ApiException("Bad Request, parameters may be wrong")
		else:
			raise ApiException("other error code in orders: ", resp.status_code)

	return payload
