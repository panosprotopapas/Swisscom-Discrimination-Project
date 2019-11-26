################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import requests
import re
import pymongo

################################
################################
####   TOP DOMAINS      ########
################################
################################

def top_domains():
    
    ''' Get a complete domain list (top-level, 2nd-level, 3rd-level, etc.). Loads and uses the Requests and Datetime libraries.
    
        The domain list as provided in https://publicsuffix.org/list/public_suffix_list.dat, in the form of a Python list. 
        An asterisk "*" signifies a "capture all" command. E.g. "*.city.com" must capture "abc.city.com", "xyz..city.com" etc.
        The complete specification of the list can be found at https://publicsuffix.org/list/.'''
    
    r = requests.get('https://publicsuffix.org/list/public_suffix_list.dat')
    # Encoding is stated to be utf-8.
    temp = r.content.decode(encoding='utf-8')
    domain_list = []
    
    # If a line in this document is (i) not empty, and (ii) does not start with "//", then it is a domain.
    for line in temp.splitlines():
        if len(line) != 0:
            if line[0:2] != '//':
                domain_list.append(line)
    
    return domain_list;

################################
################################
####       URL LIST     ########
################################
################################

def url_list(
    url_list, 
    client = "mongodb://localhost:27017/", 
    database = "database", 
    collection = "url_list" 
):
    
    ''' Extracts the domain names from a list of urls and stores both domain names and urls in Mongo DB 
        columns domain and url). All urls must be complete (e.g. http:\\www.example.com not www.example.com). 
        Loads and uses the PyMongo, Re, and Datetime libraries.
        
        Notice that the domain list includes some wildcards, e.g. *.com should capture both abc.com and xyz.com. 
        These are not taken into account by the function. These wildcards represent less than 1% of the total domains.
           
        Parameters
        ----------
        url_list                     : list,
            the url list to be stored along with domain names extracte and time of extraction.
        client, database, collection : strings.
            Location of the Mongo DB client, database and collection.''' 
 
    # Setup Mongo DB connection
    table = discrimination.mongo.collection(client, database, collection)
    
    # Get list of domains
    domain_list = discrimination.store.top_domains()

    # Create the table to be stored in Mongo DB
    mongo_list = []
    for url in url_list:
        url = discrimination.misc.url_decode(url)
        # Split the url based on forward slashes in order to keep the "middle" part (www.abc.xyz from http://www.abc.xyz/1/2)
        temp_split = re.split('/', url)
        middle = temp_split[2]
        # Split the middle part by dot ".". 
        split = re.split('\.', middle)
        # Find the domain-name as follows. Split the middle part (www.example.xyz.abc) by dot. If abc in the domain list, check xyz.abc, and so on,
        # until say example.xyz.abc is not in the list (but xyz.abc) is in the list. This implies example is the domain name.
        i = -1
        check = split[i]
        domain = None
        while check in domain_list:
            i -= 1
            domain = split[i]
            check = domain + "." + check
        
        # Only add to Mongo DB if the url-domain combination does not exist already (case insensitive).
        if table.count_documents({
            "url": str(url).lower(), 
            "domain": str(domain).lower()}) == 0:
            
            table.insert_one({
                "url"           : str(url).lower(), 
                "domain"        : str(domain).lower(), 
                "time_added"    : datetime.datetime.utcnow(),
                "time_scraped" : ""
            })