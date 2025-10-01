import requests
import os
import time
import json


api_key = os.environ['FLICKR_API_KEY']




total_pages = 443

url = 'https://www.flickr.com/services/rest/'
photos=[]

for p in range(1,total_pages):


	params = {

		"method":'flickr.people.getPublicPhotos',
		'api_key':api_key,
		'user_id': '8623220@N02',
		'page':p,
		'format':'json',
		'nojsoncallback':1
	}

	req = requests.get(url,params=params)
	print(p,req.status_code)

	data = req.json()
	photos=photos+data['photos']['photo']

	print(len(photos))
	json.dump(photos,open('../data/flickr_photos.json','w'),indent=2)
	time.sleep(0.5)
	
	