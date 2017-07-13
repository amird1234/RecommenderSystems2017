similarities = w[items_to_index['b03wd39x']]
for item in list(np.argsort(similarities)[::-1]):
    if similarities[item] <= 0:
        break
    data = json.loads(urllib.urlopen("http://www.bbc.co.uk/programmes/%s.json" % reverse_index[item]).read())
    print similarities[item]
    print ' - '.join([ reverse_index[item], data['programme']['display_title']['title'], data['programme']['display_title']['subtitle'] ])
