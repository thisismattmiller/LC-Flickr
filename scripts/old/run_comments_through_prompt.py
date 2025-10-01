import os
import json
import re
import html
from openai import OpenAI
from typing import List, Literal
from pydantic import BaseModel

class Statement(BaseModel):
    subject: str
    verb: str
    object: str
    qualifier: str | None
    subject_uri: str | None
    object_uri: str | None
    source_sentence: str | None

class Statements(BaseModel):
    results: List[Statement]

# client = OpenAI(
#     base_url="https://api.studio.nebius.ai/v1/",
#     api_key=os.environ.get("NEBIUS_API_KEY"),
# )    

data = json.load(open('../data/flickr_photos_with_metadata_comments.json'))
count=0
for photo in data:
	
	photo_id = photo['id']
	if photo_id != '52853498619':
		continue

	count=count+1
	print(count)

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


	print(hdl)

	if 'comments' in photo:
		if 'comments' in photo['comments']:
			if 'comment' in photo['comments']['comments']:
				for comment in photo['comments']['comments']['comment']:

					comment_id = comment['id']

					print(f"../data/statements/{photo_id}-{comment_id}.json")
					if os.path.isfile(f"../data/statements/{photo_id}-{comment_id}.json") == True:
						continue

					print("here")

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

					xxx=x


					completion = client.chat.completions.create(
					    model="meta-llama/Llama-3.3-70B-Instruct-fast",
					    messages=[
					        {
					            "role": "system",
					            "content": """
					            You are a helpful assistant processing the text comments left on photos. Your job is to break down the comments into statements about the subject of the photo. Each statement should be in the form of "Subject Verb Object" in JSON. If there is a qualifier such as a date include that in the statement as "qualifier" if there is a URL that represents the subject include that as "subject_uri" if there is a URL that represents the object include that as "object_uri" Also include the sentence from the comment that created that statement as "source_sentence"
					            """
					        },
					        {
					            "role": "user",
					            "content": text
					        }
					    ],
					    temperature=0,
					    max_tokens=10000,
					    # response_format={
					    #     "type": "json_object"
					    # },
					    extra_body={
					        "guided_json": Statements.model_json_schema()
					    }        
					)

					result = completion.to_dict()
					# result = completion.to_json()
					# result = json.loads(result)
					# print(result)
					try:
						result = json.loads(result['choices'][0]['message']['content'], strict=False)
					except:
						continue
						
					print(result)

					print("-----------------")

					output = {
						"results": result,
						"photo_id":photo_id,
						"comment_id":comment_id,
						"comment": text,
						"title":title,
						"description":description,
						"hdl":hdl
					}

					json.dump(output,open(f"../data/statements/{photo_id}-{comment_id}.json",'w'))


# 					## are they linking to stuff in the comment?
# 					## find out the things they are linking to first
# 					if 'https://' in text or 'http://' in text:

# 						count=count+1
# 						print(count)
# 						print("-----")
# 						print(f"""
# You are a helpful assistant extracting data from comments made on a photograph:

# Title of photograph: {title}

# From the comment text below there are URLs used, extract each url and pair it with the name of the thing it represents, for example person, place, article, photograph, etc. Structure the url and name as an array of JSON objects in the format: [ {{"name": "Person name", "url":"https://…"}}]
# Only use information from the text provided.
# Comment: {text}

# 						""")







# https://www.flickr.com/explore/2021/03/24