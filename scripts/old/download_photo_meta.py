import requests
import os
import time
import json


data = 	json.load(open('../data/flickr_photos_with_metadata.json','r'))
api_key = os.environ['FLICKR_API_KEY']


url = 'https://www.flickr.com/services/rest/'

count = 0
for photo in data:

	if 'metadata' in photo:
		continue

	count=count+1


	params = {

		"method":'flickr.photos.getInfo',
		'api_key':api_key,
		'photo_id': photo['id'],
		'format':'json',
		'nojsoncallback':1
	}

	req = requests.get(url,params=params)
	print(f'#{count}',photo['id'],req.status_code)

	if req.status_code != 200:
		print("Got bad status code")
		break

	metadata=req.json()

	photo['metadata'] = metadata

	if count % 25 == 0:
		json.dump(data,open('../data/flickr_photos_with_metadata.json','w'),indent=2)


	time.sleep(1.1)

	

json.dump(data,open('../data/flickr_photos_with_metadata.json','w'),indent=2)

# photos=[]

# for p in range(1,total_pages):






# 	data = req.json()
# 	photos=photos+data['photos']['photo']

# 	print(len(photos))
# 	json.dump(photos,open('../data/flickr_photos.json','w'),indent=2)
# 	time.sleep(0.5)
	
# 	