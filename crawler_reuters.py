#!/usr/bin/python
import re
import urllib3
import csv
import os
import sys
import time
import datetime

import numpy as np
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

api_key = os.getenv("NEWSAPI_APIKEY")

class news_Reuters:
    def __init__(self):
        fin = open('./input/tickerList.csv')
        self.newsapi = NewsApiClient(api_key=api_key)
        filterList = set()
        try: # this is used when we restart a task
            fList = open('./input/finished.reuters')
            for l in fList:
                filterList.add(l.strip())
        except: pass

        dateList = self.dateGenerator(1000) # look back on the past X days
        for line in fin: # iterate all possible tickers
            line = line.strip().split(',')
            ticker, name, exchange, MarketCap = line
            if ticker in filterList: continue
            print("%s - %s - %s - %s" % (ticker, name, exchange, MarketCap))
            self.contents(ticker, name, line, dateList, exchange)

    def contents(self, ticker, name, line, dateList, exchange):
        # https://uk.reuters.com/info/disclaimer
        suffix = {'AMEX': '.A', 'NASDAQ': '.O', 'NYSE': '.N'}
        # e.g. http://www.reuters.com/finance/stocks/company-news/BIDU.O?date=09262017
        url = "http://www.reuters.com/finance/stocks/companyNews/" + ticker + suffix[exchange]
        http = urllib3.PoolManager()
        has_Content = 0
        repeat_times = 0
        # check the website to see if that ticker has many news
        # if true, iterate url with date, otherwise stop
        for _ in range(repeat_times): # repeat in case of http failure
            try:
                # time.sleep(np.random.poisson(3))
                response = http.request('GET', url)
                soup = BeautifulSoup(response.data, "lxml")
                #print(soup.prettify())
                has_Content = len(soup.find_all("div", {'class': ['topStory', 'feature']}))
                break
            except:
                continue

        # spider task for the past
        # if some company has no news even if we don't input date
        #     set this ticker into the lowest priority list
        #
        # else
        #     if it doesn't have a single news for NN consecutive days, stop iterating dates
        #     set this ticker into the second-lowest priority list
        ticker_failed = open('./input/news_failed_tickers.csv', 'a+')
        if has_Content > 0:
            missing_days = 0
            for timestamp in dateList:
                hasNews = self.repeatDownload(ticker, line, url, timestamp)
                if hasNews: missing_days = 0 # if get news, reset missing_days as 0
                else: missing_days += 1
                if missing_days > has_Content * 5 + 20: # 2 NEWS: wait 30 days and stop, 10 news, wait 70 days
                    break # no news in X consecutive days, stop crawling
                if missing_days > 0 and missing_days % 20 == 0: # print the process
                    print("%s has no news for %d days, stop this candidate ..." % (ticker, missing_days))
                    ticker_failed.write(ticker + ',' + timestamp + ',' + 'LOW\n')
        else:
            print("%s has no news" % (ticker))
            today = datetime.datetime.today().strftime("%Y%m%d")
            ticker_failed.write(ticker + ',' + today + ',' + 'LOWEST\n')
        ticker_failed.close()

    def repeatDownload(self, ticker, line, url, timestamp):
        http = urllib3.PoolManager()
        repeat_times = 3 # repeat downloading in case of http error

        fout = open('./input/news_reuters.csv', 'a+')
        all_articles = self.newsapi.get_everything(q=ticker,
                                              language='en',
                                              from_param=timestamp,
                                              to=timestamp,
                                              sort_by='relevancy')
        if all_articles['articles']:
            article =  all_articles['articles'][0]
            print('------------------------------------News---------------------------------------')
            print('Title:', article['title'])
            fout.write(','.join([ticker, line[1], timestamp, title, body, news_type]).encode('utf-8') + '\n')
        fout.close()
        return 0

    def parser(self, soup, line, ticker, timestamp):
        content = soup.find_all("div", {'class': ['topStory', 'feature']})
        if len(content) == 0: return 0
        fout = open('./input/news_reuters.csv', 'a+',encoding = 'utf-8')
        for i in range(len(content)):
            title = content[i].h2.get_text().replace(",", " ").replace("\n", " ")
            body = content[i].p.get_text().replace(",", " ").replace("\n", " ")

            if i == 0 and len(soup.find_all("div", class_="topStory")) > 0: news_type = 'topStory'
            else: news_type = 'normal'

            print(ticker, timestamp, title, news_type)
            fout.write(','.join([ticker, line[1], timestamp, title, body, news_type])+'\n')

        fout.close()
        return 1

    def dateGenerator(self, numdays): # generate N days until now
        base = datetime.datetime.today()
        date_list = [base - datetime.timedelta(days=x) for x in range(0, numdays)]
        for i in range(len(date_list)): date_list[i] = date_list[i].strftime("%Y-%m-%d")
        return date_list

def main():
    news_Reuters()

if __name__ == "__main__":
    main()
