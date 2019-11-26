################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import time
import requests
import bs4
import re
import pymongo
import datetime

################################
################################
####       SCRAPER      ########
################################
################################

def scrape(url, client, database, rescrape_old_posts, page_number = 1):
    
    '''EverydaySexism.com SubScraper, to be used by the scraper function.
    
    Parameters
    ----------
    url                 : string.
        The url (country) to be scraped (all available pages will be scraped).
    client, database    : strings.
        The location of the Mongo DB client and database.
    rescrape_old_posts  : bool.
        When False it stops scraping at the first item that has been rescraped.
    page_number         : int, default 1.
        Page number to start scraping from.'''

    # Needed, otherwise website's firewall denies access
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'}

    # Switch to the correct Mongo table
    table = discrimination.mongo.collection(client, database, collection = "everydaysexism")

    # Make the soup
    if url[-1] == "/":
            url += "page/"
    else:
            url += "/page/"
    page_no = page_number
    while page_no > 0:
        url_page = url + str(page_no)
        
        try:
            page = requests.get(url_page, headers = headers)
            soup = bs4.BeautifulSoup(page.content, "lxml")

            # Break when an empty page is reached
            if "Nothing found for the requested page." in soup.find("article").find("p").text:
                break

            else:
                no_posts = len(soup.find_all("article"))

                for i in range(no_posts):

                    try:
                        text = soup.find_all("article")[i].find("p").text
                    except:
                        text = ""

                    # Date is in form "Xth June 2019" and must be changed slightly prior to converting to datetime
                    try:
                        date = soup.find_all("article")[i].find("span", attrs={"class":"entry-date"}).text
                        day = re.findall('^\d+', date)[0]
                        date = re.sub('^\d+[A-Za-z]+', day, date)
                        date = datetime.datetime.strptime(date, "%d %B %Y")
                    except:
                        date = ""
                    # Get post's url
                    try:
                        post_url = soup.find_all("article")[i].find(attrs={"class":"entry-title"}).find("a").get("href")
                        post_url = post_url.lower()
                    except:
                        post_url = ""
                    # Get post's title
                    try:    
                        title = soup.find_all("article")[i].find(attrs={"class":"entry-title"}).find("a").get("title")
                    except:
                        title = ""
                    # Get post's tags
                    try:
                        list_ = soup.find_all("article")[i].find(attrs={"class":"tag-links"}).find_all("a")
                        tags =[]
                        for item in list_:
                            tags.append(item.text.lower())
                    except:
                        tags = []

                    if table.count_documents({ "url": post_url, "title": title, "date": date }) != 0:
                        if rescrape_old_posts == False:
                            page_no = -42
                            break
                        else:
                            pass
                    else:
                        table.insert_one({
                                "title": title, 
                                "text" : text, 
                                "tags" : tags,
                                "date" : date,
                                "url"  : post_url
                            })

                # Keep track of where the scraper is
                if page_no % 10 == 0:
                    print(page_no)
                page_no += 1
                
        except:
            print("Perhaps blacklisted. Let's wait a little.")
            time.sleep(180)