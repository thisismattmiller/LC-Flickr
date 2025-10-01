import os
from openai import OpenAI
from typing import List, Literal
from pydantic import BaseModel


class URLItem(BaseModel):
    name: str
    url: str


class URLList(BaseModel):
  result: List[URLItem]
  # year: int
  # director: str
  # cast: 
  # genre: Literal[
  #     "drama", "thriller", "sci-fi",
  #     "comedy", "horror", "fantasy"
  # ]



client = OpenAI(
    base_url="https://api.studio.nebius.ai/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
)

completion = client.chat.completions.create(
    model="meta-llama/Llama-3.3-70B-Instruct",
    messages=[
        {
            "role": "user",
            "content": """

You are a helpful assistant extracting data from comments made on a photograph:

Title of photograph: Tripoli - Captured Arabs at Fountain of Bu Meliana  (LOC)

From the comment text below there are URLs used, extract each url and pair it with the name of the thing it represents, for example person, place, article, photograph, etc. Structure the url and name as an array of JSON objects in the format: [ {"name": "Person name", "url":"https://…"}]
Only use information from the text provided.
Comment: Probably taken during the Turco-Italian war of 1912, no?

<a href="http://www.warchat.org/history-europe/italo-turkish-war-turko-italian-war-1912.html">www.warchat.org/history-europe/italo-turkish-war-turko-it...</a>

            """
        }
    ],
    temperature=0,
    max_tokens=10000,
    # response_format={
    #     "type": "json_object"
    # },
    extra_body={
        "guided_json": URLList.model_json_schema()
    }        
)


print(completion.to_json())
