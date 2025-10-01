import os
import json
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


# class URLItem(BaseModel):
#     name: str
#     url: str


# class URLList(BaseModel):
#   result: List[URLItem]
#   # year: int
#   # director: str
#   # cast: 
#   # genre: Literal[
#   #     "drama", "thriller", "sci-fi",
#   #     "comedy", "horror", "fantasy"
#   # ]



client = OpenAI(
    base_url="https://api.studio.nebius.ai/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
)

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
            "content": """
see also
<a href="http://www.flickr.com/photos/library_of_congress/2163002857/"><img src="http://farm3.staticflickr.com/2118/2163002857_d7a4e0f569_m.jpg" width="240" height="173" alt="Tripoli - Guns on " /></a>

More on the Pisa and Italian Pisa class armored battle cruisers:<a href="http://www.cityofart.net/bship/rn_garibaldi.html" rel="nofollow">www.cityofart.net/bship/rn_garibaldi.html</a>  (scroll down)

Pisa served in WWI, then was reclassified as a coastal battleship in 1921 and  used as a training ship until being scrapped in 1937.

 <a href="http://en.wikipedia.org/wiki/Pisa_class_armored_cruiser" rel="nofollow">en.wikipedia.org/wiki/Pisa_class_armored_cruiser</a>
Her sister ship, sold to Greece as the Georgios Averof, is the only remaining armored battle cruiser of this era and is a museum ship, at Faliro, Greece, near Athens.
<a href="http://en.wikipedia.org/wiki/Greek_cruiser_Georgios_Averof" rel="nofollow">en.wikipedia.org/wiki/Greek_cruiser_Georgios_Averof</a>

            """
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
print(result)

print(result['choices'][0]['message']['content'])
