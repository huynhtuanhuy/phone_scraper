import os
import json
import logging
from threading import Thread
import sys
from queue import Queue
import requests
import random
from pyquery import PyQuery as pq

concurrent = 50

logging.basicConfig(
    filename='./logs/log.txt',
    format='%(asctime)s - %(levelname)s: %(message)s',
    level=logging.INFO
)

def doWork():
    while True:
        phoneNumber = q.get()
        with open('companies.json') as json_file:
            data = {'country':phoneNumber[:2], 'number':phoneNumber[2:]}

            companyList = json.load(json_file)
            for company in companyList:
                try:
                    randomIndex = random.randint(0, len(company['domains']) - 1)
                    domain = company['domains'][randomIndex]
                    get_url = domain+company['get_url']
                    post_url = domain+company['post_url']
                    string_requestverificationtoken = company['string_requestverificationtoken']

                    s = requests.Session()
                    s.proxies = "http://jimmyjo:bbe8a0-ba74c9-402fe3-e5b6d4-05df22@megaproxy.rotating.proxyrack.net:222"

                    cookieResponse = s.get(get_url).text
                    d = pq(cookieResponse)
                    token = d('#hdnAntiForgeryTokens').val()

                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Host': domain.replace('https://', '', 1).replace('http://', '', 1),
                        'Origin': domain,
                        'Referer': get_url,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                    headers[string_requestverificationtoken] = token
                    s.headers.update(headers)

                    response = s.post(post_url, data=data)
                    responseJson = json.loads(response.text)
                    # print(responseJson)
                    if responseJson['Code'] != 0:
                        f = open("./results/results.csv", "a")
                        f.write(str(phoneNumber)+"\n")
                        f.close()
                        break
                    pass
                except Exception as e:
                    logging.error("An error occurred: " + phoneNumber + " - " + str(e))
                    pass
            # logging.info("End check: " + phoneNumber.strip())
            q.task_done()

q = Queue(concurrent)

for i in range(concurrent):
    t = Thread(target=doWork)
    t.daemon = True
    t.start()

try:
    for subdir, dirs, files in os.walk("./raw_data"):
        for file in files:
            logging.info("Start check!")
            filepath = subdir + os.sep + file
            if filepath.endswith(".csv"):
                f = open(filepath, "r")
                f1 = f.readlines()
                i = 0
                for phoneNumber in f1:
                    if i < 500:
                        # logging.info("Start check: " + phoneNumber.strip())
                        q.put(phoneNumber.strip())
                        print(i)
                    i += 1
                q.join()
        logging.info("End check!")
except KeyboardInterrupt:
    sys.exit(1)
