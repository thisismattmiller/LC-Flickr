import json
import re
import html
data = json.load(open('../data/flickr_photos_with_metadata_comments.json'))
count=0
for photo in data:
	

	try:
		title = photo['metadata']['photo']['title']['_content']
	except:
		continue


	try:
		description = photo['metadata']['photo']['description']['_content'] 
	except:
		description =''

	description = description.replace('http://','https://')
	hdl = None
	for tag in photo['metadata']['photo']['tags']['tag']:
		# print(tag)
		if 'hdl.loc.gov' in tag['raw']:
			hdl = tag['raw'].replace('dc:identifier=','')


	# hdl = re.findall(r"http://hdl\.loc\.gov/.*",description)

	# print("*********")
	if hdl == None:
		# look for it in the desc

		hdl = re.findall(r"https://hdl\.loc\.gov/[/.a-z0-9]+",description)
		if len(hdl) == 0:
			hdl = re.findall(r"https://chroniclingamerica.loc.gov/[/.\-a-z0-9]+",description)

			if len(hdl) == 0:
				hdl = re.findall(r"hdl\.loc\.gov/[/.a-z0-9]+",description)
				if len(hdl) == 0:
					hdl = re.findall(r"www\.loc\.gov/item[/.a-z0-9]+",description)

					if len(hdl) == 0:
						continue
						print(photo['id'])

		hdl_touse = ''
		for h in hdl:
			if len(h) > len(hdl_touse):
				hdl_touse=h

		hdl = hdl_touse


	# print(hdl)

	if 'comments' in photo:
		if 'comments' in photo['comments']:
			if 'comment' in photo['comments']['comments']:
				for comment in photo['comments']['comments']['comment']:

					text = comment['_content']

					text = html.unescape(text)

					# drop anything talking about flickr meta stuff, 
					if 'www.flickr.com/groups/' in text or 'flickr.com/explore' in text:
						continue

					# short comments
					if len(text.split(" ")) <=5:
						continue

					if 'feature this photo' in text:
						continue
					if 'permission to use' in text:
						continue

					if re.search(r"www\.flickr\.com/photos/.*/galleries/", text):
						continue

					## are they linking to stuff in the comment?
					## find out the things they are linking to first
					if 'https://' in text or 'http://' in text:

						count=count+1
						print(count)
						print("-----")
						print(f"""
You are a helpful assistant extracting data from comments made on a photograph:

Title of photograph: {title}

From the comment text below there are URLs used, extract each url and pair it with the name of the thing it represents, for example person, place, article, photograph, etc. Structure the url and name as an array of JSON objects in the format: [ {{"name": "Person name", "url":"https://…"}}]
Only use information from the text provided.
Comment: {text}

						""")







# https://www.flickr.com/explore/2021/03/24