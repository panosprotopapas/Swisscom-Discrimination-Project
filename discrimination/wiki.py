################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import random
import re
import wikipedia
import requests

################################
################################
########   SEARCH   ############
################################
################################

def search(query, results = 500, language = "en"):
    
    '''Search Wikipedia using the provided query and return (up to) 500 results (page titles).
    
     Parameters
    ----------
    query    : str.
    results  : int, default = 500. The number of results to return (500 is max).
    language : str, default = "en", English. The language in which to search in.''' 
    
    wikipedia.set_lang(language)
    titles = wikipedia.search(query, results)
    
    return titles;

################################
################################
######  RELATED TITLES  ########
################################
################################

def related(titles, language = "en"):
    
    '''Search all provided Wikipedia page-titles, for the "See also" section's titles. All page-titles must be from the same Wiki country website.
    
     Parameters
    ----------
    titles : list containing the page-titles.
    language : str, default = "en", English. The language in which the pages are written in.''' 
    
    related_titles = []
        
    for title in titles:
       
        # Construct url
        a = "https://"
        b = language
        c = ".wikipedia.org/w/api.php?action=parse&prop=sections&page="
        d = title
        e = "&format=json"
        url = a + b + c + d + e
        
        # Get json file
        r = requests.get(url)
        j = r.json()
        
        # Find the index number, if it exists
        index = -1
        for sec in j["parse"]["sections"]:
            if sec["line"] == "See also":
                index = sec["index"]
        
        # If index exists, get all related page-titles
        if index != -1:
            # Construct url
            c = ".wikipedia.org/w/api.php?action=parse&prop=links&page="
            e = "&section="
            f = index
            g = "&format=json"
            url = a + b + c + d + e + f + g
            
            # Get json file
            r = requests.get(url)
            j = r.json()
            
            for link in j["parse"]["links"]:
                if link["ns"] == 0:
                    related_titles.append(link["*"])
    
    return related_titles;