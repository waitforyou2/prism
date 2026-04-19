import requests, json, re
from bs4 import BeautifulSoup
url = 'https://www.zhihu.com/search?type=content&q=Harness%20Engineering'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml'
}
resp = requests.get(url, headers=headers)
print('Status:', resp.status_code)
html = resp.text
match = re.search(r'id="js-initialData".*?>({.*?})</script>', html)
if match:
    # the JSON string has HTML entities like &quot; so it's easier to just print
    data = match.group(1)
    print('Found js-initialData! Length:', len(data))
    print(data[:500])
else:
    print('No js-initialData found. Length:', len(html))
    print(html[:500])
