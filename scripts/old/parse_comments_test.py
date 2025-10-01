import json


data = 	json.load(open('../data/flickr_photos_with_metadata_comments.json','r'))



for photo in data:

	if 'comments' in photo:


		if 'comments' in photo['comments']:

			print(photo['comments']['comments'])

			if 'comment' in photo['comments']['comments']:



				print(photo['comments']['comments']['comment'])