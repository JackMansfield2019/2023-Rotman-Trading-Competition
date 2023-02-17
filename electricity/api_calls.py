import requests

# this class definition allows us to print error messages and stop the program when needed
class ApiException(Exception):
	pass

API_KEY = {'X-API-key': 'DV2931GT'} # Save your API key for easy access.
BASE_URL = 'http://localhost:9999/v1/'
shutdown = False

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