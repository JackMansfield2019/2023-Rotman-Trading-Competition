import requests # step 1

API_KEY = {'X-API-key': 'DV2931GT'} # step 2

def main():
    with requests.Session() as s: # step 3
        s.headers.update(API_KEY) # step 4
        print("line 8")
        #http://winhost:9999/v1/case?key=DV2931GT
        resp = s.get('http://localhost:9998/v1/case?key=DV2931GT') # step 5
        print("line 10")
        if resp.ok: # step 6
            case = resp.json() # step 7
            tick = case['tick'] # accessing the 'tick' value that was returned
            print('The case is on tick', tick) # step 8
        else:
            print("Error Response is not ok")

if __name__ == '__main__':
    main()