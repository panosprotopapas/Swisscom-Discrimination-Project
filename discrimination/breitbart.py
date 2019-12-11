################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import random
import selenium
from selenium.webdriver.common.by import By
from selenium import webdriver
import time
from selenium.webdriver.common.keys import Keys

################################
################################
#########  SCRAPER    ##########
################################
################################

def scrape(
    url,
    client='mongodb://localhost:27017/',
    database='database'
): 
    
    '''Scraper for Breitbart news articles.
    
    Parameters
    ----------
    url                : A Breitbart news article.
    client, database   : Mongo DB details to store the urls'''
    
    # Set scraped flag
    scraped = False

    # Fix url if needed
    if url[-1] != "/":
        if url[-16:] == "/#disqus_thread/":
            pass
        else:
            url += "#disqus_thread"
    else:
        if url[-15:] == "/#disqus_thread":
            pass
        else:
            url += "/#disqus_thread"
    
    # Load driver and get url.
    driver = webdriver.Chrome()          
    driver.get(url)
    driver.set_window_size(1800, 1080)
    
    # Click close on xmas pop-up (if it exists)
    try:
        xmas_button = driver.find_element_by_xpath('''/html/body/div[1]/div[2]/div/span''')
        xmas_button.click()
    except:
        pass

    # Get article title
    title = driver.title

    # Wait for disqus to load and scroll to the end of the page
    time.sleep(5)
    driver.find_element_by_tag_name('body').send_keys(Keys.END)
    

    # Find iframes
    iframes = driver.find_elements_by_tag_name("iframe")

    # Find the correct iframe
    for iframe in iframes:
        driver.switch_to.frame(iframe)
        try:
            driver.find_element_by_xpath("/html/body/div[3]/div/div/div/section/div[2]/div[4]/a")
            correct_iframe = iframe
        except:
            pass
        driver.switch_to.default_content()

    # Switch to correct iframe, locate "More comments" button.
    driver.switch_to.frame(correct_iframe)
    button = driver.find_element_by_xpath("/html/body/div[3]/div/div/div/section/div[2]/div[4]/a")

    # Until page is exhausted of more comments, keep pushing the button and scrolling to the end of it.
    x = 0
    try:
        # The while loop will end when the page won't be update 3 times in a row
        while  x != 3:
            check = len(driver.page_source)
            
            # Click the button
            button.click()
            # Wait for more comments to load
            time.sleep(1.5)
            # Scroll to the end of the page
            driver.find_element_by_tag_name('body').send_keys(Keys.END)
            # Wait some more
            time.sleep(0.5)
            
            if check == len(driver.page_source):
                x += 1
            else:
                check = len(driver.page_source)
                x = 0
    except:
        pass

    # Get all comments
    lista = driver.find_elements_by_css_selector('div.post-message')
    comments = []
    for item in lista:
        comments.append(item.text)
        
    # Close browser
    driver.quit()
        
    # Save the text and news title to Mongo (if they don't exist)
    table = discrimination.mongo.collection(client, database, collection = "breitbart")
    for comment in comments:
        if table.count_documents({
                    "text"     : comment, 
                    "article" : title}) == 0:

                table.insert_one({
                    "text"     : comment, 
                    "article" : title
                })
    
    # Set scraped flag
    scraped = True
    return(scraped);  