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
def scroll_down(url):
    
    '''Scroll to the end of the provided url, retrieve the html and return the (Selenium) driver.'''  
    
    # Setup Selenium and necessary counter
    driver = webdriver.Firefox()
    driver.get(url)
    strikes = 0

    # Get page and build a length counter
    page = driver.page_source
    length = len(driver.page_source)      
    
    driver.set_window_size(1600, 1080)   
    # Press END-key roughly once per second. Stop when the new page count is equal with the old 3 times in a row.
    while strikes < 4:
        driver.find_element_by_tag_name('body').send_keys(selenium.webdriver.common.keys.Keys.END)
        page = driver.page_source
        newlength = len(driver.page_source)
        if length-1 <=  newlength <= length+1:
            strikes += 1
        else:
            strikes = 0
            length = newlength
            time.sleep(0.5)
    
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