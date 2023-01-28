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

	TODO:
		tell user when they are missing parameters for a certain endpoint
			parse endpoint
			check if required arguments are in dictonary
			return list of arguments required 
		tell user why a request failed(ex rate limit)
			parse error message from api
			handle exception
			print corresponding error message
		handle what happens if user provides an argument that the end point does not take.
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.get(URL, params=kwargs)

	if resp.ok:
		payload : dict = json.loads(resp.json())
		print('API GET SUCCESSFUL')

	else:
		print('API GET FAILED')
		raise ApiException('Authorization error Please Check API Key.')
		
	return payload

def api_put(session : requests.Session, endpoint: str, **kwargs : dict) -> dict:
	'''
	Makes a custom PUT request to a specified endpoint in the RIT API

		Parameters:
			Session (requests.Session): Current Session Object
			endpoint (String): name of the end point ex "case" or "assets/history" or "orders/{insert your id here}"
			kwargs (Dict): Dictionary that maping each keyword to the value that we pass alongside it
		
		Returns:
			Payload (Dict): Dictonary contining the JSON returned from the endpoint
	
		Example Usage:
			api_put( s, "orders", ticker = "RTM", type = "LIMIT", quantity = "100", action = "SELL")
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.put(URL, params=kwargs)

	if resp.ok:
		payload : dict = json.loads(resp.json())
		print('API PUT SUCCESSFUL')

	else:
		print('API PUT FAILED')
		raise ApiException('Authorization error Please Check API Key.')

	return payload

def api_delete(session : requests.Session, endpoint: str, **kwargs : dict) -> dict:
	'''
	Makes a custom DELETE request to a specified endpoint in the RIT API

		Parameters:
			Session (requests.Session): Current Session Object
			endpoint (String): name of the end point ex "case" or "assets/history" or "orders/{insert your id here}"
			kwargs (Dict): Dictionary that maping each keyword to the value that we pass alongside it
		
		Returns:
			Payload (Dict): Dictonary contining the JSON returned from the endpoint
	
		Example Usage:
			api_delete( s, "/tenders/{id}")
	'''
	URL : str  = BASE_URL + endpoint

	resp = session.put(URL, params=kwargs)

	if resp.ok:
		payload : dict = json.loads(resp.json())
		print('API DELETE SUCCESSFUL')

	else:
		print('API DELETE FAILED')
		raise ApiException('Authorization error Please Check API Key.')

	return payload

def main():
	
	with requests.Session() as s: # Create a Session object to manage connections and requests to the RIT client.
	
		s.headers.update(API_KEY) # Add the API key to the Session to authenticate with every request
		
		payload = api_get(s, "case")

		tick = payload["tick"]

		#while the time is between 5 and 295, do the following
		while tick > 5 and tick < 295 and not shutdown:

			#refresh the case time. THIS IS IMPORTANT FOR THE WHILE LOOP
			tick = api_get(s, "case")["tick"]

			print('The case is on tick', tick) # Do something with the parsed data.

if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	main()
	"""
		NOTE:	RIT Client must be running to access this API
		NOTE:	Responses are always JSON objects.
		NOTE:	Successful requests always return with HTTP code 200
		NOTE:	Unsuccessful responses have HTTP error codes between 400 and 500
	"""
