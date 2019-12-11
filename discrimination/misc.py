################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import urllib.parse
import selenium
from selenium import webdriver
import time
import stem
import requests
import stem.control

################################
################################
####    URL DECODE      ########
################################
################################

def url_decode(url):   
    
    '''Returns a decoded url string where hex-byte-strings and other nasty stuff are substituted with utf8 (e.g. ç instead of %C3%A7).'''  
    
    url = urllib.parse.unquote(url)
    return url;   

################################
################################
# SCROLL TO THE END OF A PAGE  #
################################
################################
def scroll_down(url, sleep = 0.5, strikes = 4, browser = "chrome"):
    
    '''Scroll to the end of the provided url, retrieve the html and return the (Selenium) driver.
    
    Parameters
    ----------
    url     : Well.. the url.
    sleep   : How long to stop (in seconds) between presses of the END button.
    strikes : The number of sleep-times the function will wait for the page to load fully before considering it fully loaded.
    browser : The browser to use: chrome or firefox.''' 
    
    # Setup Selenium and necessary counter
    if browser == "firefox":
        driver = webdriver.Firefox()
    else:
        driver = webdriver.Chrome()
     
    driver.get(url)
    s = 0
    
    # Wait a bit for everything to load
    time.sleep(1)

    # Get page, build a length counter, and find the html body
    page = driver.page_source
    length = len(driver.page_source)  
    body = driver.find_element_by_tag_name('body')
    
    # Change window size if needed
#     driver.set_window_size(1600, 1080) 
    
    # Press END-key roughly once per second. Stop when the new page count is equal with the old 3 times in a row.
    while s < strikes:
        
        # Sleep a little
        time.sleep(sleep)
        
        # Press the End key and check if more of the page has appeared.
        body.send_keys(selenium.webdriver.common.keys.Keys.END)
        page = driver.page_source
        newlength = len(driver.page_source)
        
        # If nothing new has appeared, increase the strikes counter
        if length-1 <=  newlength <= length+1:
            s += 1
        else:
            s = 0
            length = newlength
         
    return driver;

################################
################################
#### REQUEST PAGE VIA TOR  #####
################################
################################
def tor_request(url, timeout = 3, headers = None):
    
    '''Change ip, then request url-page. Set timeout for request if 3sec. is not good'''  
       
    # Set-up TOR proxies
    session = requests.session()
    session.proxies = {}
    session.proxies['http'] = 'socks5h://localhost:9050'
    session.proxies['https'] = 'socks5h://localhost:9050'
    
    # Restart TOR to get new ip
    with stem.control.Controller.from_port(port = 9051) as c:
        c.authenticate(password="0kr3mm1d1dr0m0l0g1T15")
        c.signal(stem.Signal.NEWNYM)
    if headers == None:
        r = session.get(url, timeout = timeout)
    else:
        r = session.get(url, headers = headers, timeout = timeout)
    
    return r;