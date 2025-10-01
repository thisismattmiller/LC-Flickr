
import json

comments = []

data = json.load(open('../data/flickr_photos_with_metadata_comments.json'))

for photo in data:
	if 'comments' in photo:
		if 'comments' in photo['comments']:
			if 'comment' in photo['comments']['comments']:
				for comment in photo['comments']['comments']['comment']:

					comments.append(comment['_content'])



json.dump(comments,open('../data/comments_only.json','w'),indent=2)