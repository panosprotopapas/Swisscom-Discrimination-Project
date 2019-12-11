################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
from bs4 import BeautifulSoup
import re
import requests

################################
################################
########  GET URLS  ############
################################
################################

def get_urls(
    url, 
    tor = False
):
    
    '''Gather the links directing to the comment-pages of all the topics listed in the provided url. Stores the links in Mongo. Set tor to True to request pages with a random ip.'''
    
    # Request page and  make the soup
    if tor == True:
        p = discrimination.misc.tor_request(url)
    else:
        p = requests.get(url)
    
    # Make the soup
    soup = BeautifulSoup(p.content, features="lxml")

    # Get all topics
    topics = soup.select("li.bbp-topic-title")

    # Get all topics' urls
    t_urls = ["https://www.mgtow.com" + x.select_one("a.bbp-topic-permalink")["href"] for x in topics[1:]]

    # Get the number of pages per topic
    n_of_pages = []
    for x in topics[1:]:
        n = x.select_one("span.bbp-topic-pagination").select("a")[-1].text
        n_of_pages.append(int(n))

    # Construct all topics' pages urls
    p_urls = []
    for i, url in enumerate(t_urls):
        for j in range(1, n_of_pages[i] + 1):
            page = url + "page/" + str(j) + "/"
            p_urls.append(page)
    
    # Store all urls
    discrimination.store.url_list(p_urls)
    
################################
################################
##########   SCRAPE  ###########
################################
################################

def scrape(
    url,
    client='mongodb://localhost:27017/',
    database='database',
    tor = False
): 
    
    '''Scraper for mgtow topics-pages urls.
    
    Parameters
    ----------
    url                : An mgtow topic-page url.
    client, database   : Mongo DB details to store the urls
    tor                : bool; default False. Whether to request the page via Tor.'''
    
    # Set scraped flag
    scraped = False
    
    # Set Mongo collection name
    collection = "mgtow"
    
    try:
        # Request page and  make the soup
        if tor == True:
            p = discrimination.misc.tor_request(url)
        else:
            p = requests.get(url)

        # Make the soup
        soup = BeautifulSoup(p.content, features="lxml")

        # Get the page's title
        title = soup.select_one("h1").text

        # Scrape the comments
        posts = soup.select("div#bbpress-forums>ul>li.bbp-body>div:not(div.bbp-reply-header)")
        comments = []
        for post in posts:
            comment = post.select("div.bbp-reply-content>p")
            comment = [x.text for x in comment]
            comment = " /n ".join(comment)
            comments.append(comment)

        # Store everything in Mongo
        table = discrimination.mongo.collection(client, database, collection)
        for comment in comments:
            table.insert_one({
                        "text"  : comment, 
                        "title" : title 
                    })

        # Set scraped flag
        scraped = True
        return(scraped);
    
    except:
        return(scraped);