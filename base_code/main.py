import signal
import json
from time import sleep
import sys

#this signal handler allows us for a graceful shutdown when CTRL+C is pressed
def signal_handler(signum, frame):
	global shutdown
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	shutdown = True

#SETTINGS
# How long to wait after submitting buy or sell orders 
SPEEDBUMP = 0.5
# Maximum number of shares to purchase each order
MAX_VOLUME = 5000
# Maximum number oforder we can sumbit
MAX_ORDERS = 5
# Allowed spread before we sell or buy shares
SPREAD = 0.05

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