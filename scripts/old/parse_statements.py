import glob
import json
import collections

predicates = {}

for file in glob.glob("../data/statements/*.json"):

	data = json.load(open(file))

	for stmt in data['results']['results']:

		if stmt['subject'].lower() == 'you':
			continue

		# if stmt['subject'].lower() == 'i':
		# 	print(stmt)

		p = stmt['verb']
		p = stmt['subject']
		p = p.lower().strip()

		if p not in predicates:
			predicates[p] = 0

		predicates[p]=predicates[p]+1

		# if stmt['verb'] == 'was renamed':
		# 	print(stmt)



od = dict(sorted(predicates.items(), key=lambda item: item[1], reverse=True))

print(od)

