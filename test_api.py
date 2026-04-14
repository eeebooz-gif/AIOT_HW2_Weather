import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8')

API_KEY = "CWA-037B62A8-78EB-461B-96DB-D4958C4266E0"
url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={API_KEY}"
r = requests.get(url)
data = r.json()

locs = data['records']['location']
print("All locations:")
for loc in locs:
    print(f"  {loc['locationName']}")

print(f"\nTotal: {len(locs)} locations")
print(f"\nTime periods for {locs[0]['locationName']}:")
mint = next(e for e in locs[0]['weatherElement'] if e['elementName'] == 'MinT')
for t in mint['time']:
    print(f"  {t['startTime']} -> MinT={t['parameter']['parameterName']}")
