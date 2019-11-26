################################
################################
######    PACKAGES      ########
################################
################################

import discrimination
import re
import nltk
import langdetect
import matplotlib.pyplot
import spellchecker

################################
################################
####     CLEAN TEXTS    ########
################################
################################

def clean(texts):
    
    ''' Cleans (most) urls, html, hashtags, long non-existing words, long strings of non-word text, and very short pieces of text from the list. Returns the cleaned list.
           
        Parameters
        ----------
        texts : the list to clean'''
    
    # Remove urls
    for i, text in enumerate(texts):
        list_temp = re.findall('\S{20,}', text)
        for item in list_temp:
            if "http" in item:
                texts[i] = texts[i].replace(item, "")
            elif "www" in item:
                texts[i] = texts[i].replace(item, "")
            elif ".com" in item:
                texts[i] = texts[i].replace(item, "")

    # Remove html
    for i, text in enumerate(texts):
        list_temp = re.findall('<iframe.+iframe>', text)
        for item in list_temp:
            texts[i] = texts[i].replace(item, "")
    for i, text in enumerate(texts):
        list_temp = re.findall('<object.+object>', text)
        for item in list_temp:
            texts[i] = texts[i].replace(item, "")
    for i, text in enumerate(texts):
        list_temp = re.findall('<br.+/>', text)
        for item in list_temp:
            texts[i] = texts[i].replace(item, "")

    # Remove hashtags
    for i, text in enumerate(texts):
        list_temp = re.findall('#\S+', text)
        for item in list_temp:
            texts[i] = texts[i].replace(item, "")

    # Remove long words that most probably are not words
    for i, text in enumerate(texts):
        list_temp = re.findall('\w{20,}', text)
        for item in list_temp:
            texts[i] = texts[i].replace(item, "")

    # Remove long strings of no whitespace
    for i, text in enumerate(texts):
        list_temp = re.findall('\S{100,}', text)
        for item in list_temp:
            texts[i] = texts[i].replace(item, "")
            
    # Remove texts with less than 20 characters
    list_temp = []
    for text in texts:
        if len(text) >= 20:
            list_temp.append(text)
    texts.clear()
    texts = list_temp.copy()

    return texts;

################################
################################
####  TOKENIZE TEXTS    ########
################################
################################

def tokenize(
    texts,
    remove_stopwords = True
):
    
    ''' Tokenizes texts and (optionally) removes stop-words. Will only keep words containing only letters, e.g. "hey m8, pub?" will become [hey, pub].
           
        Parameters
        ----------
        texts            : the list of texts to be tokenized
        remove_stopwords : True by default. Set to False if you want to keep stopwords'''
    
    # Setup tokenizer's regex and stop-words
    tokenizer = nltk.tokenize.RegexpTokenizer('(?<!\w)[a-z]+(?!\w)')
    stop_words = set(nltk.corpus.stopwords.words('english')) 
    list_of_tokens = []
    
    for text in texts:
        token = tokenizer.tokenize(text)
    
        if remove_stopwords == True:
            temp = token.copy()
            token.clear()   
            for word in temp:
                if word not in stop_words: 
                    token.append(word)
    
        list_of_tokens.append(token)
    
    return list_of_tokens;

################################
################################
####  LOWERCASE TEXTS   ########
################################
################################

def lowercase(texts):    
     
    ''' Turns all texts in the list provided to lowercase. Returns the new list.'''
        
    for i, text in enumerate(texts):
        texts[i] = text.lower()
    
    return texts;

################################
################################
##  ONLY KEEP ENGLISH TEXTS ####
################################
################################

def keep_english(texts, notify = 10000 ):    
     
    ''' Only keeps the English texts from the provided list of texts. Returns the (almost) English-only list.
    
    Parameters
        ----------
        texts  : The list of texts to be checked for English
        notify : Every selected number of checks a notification is printed to act as a timer.'''
    
    list_temp = texts.copy()
    texts.clear()
    counter = 0

    # Print a notice every 10,000 texts checked, only keep texts in english
    for item in list_temp:
        counter += 1
        if counter%notify == 0:
            print(str(counter) + " texts checked.")
        try:
            language = langdetect.detect(item)
        except:
            language = ""
        if language == "en":
            texts.append(item)
            
    return texts;


################################
################################
#####  SPLIT IN SENTENCES ######
################################
################################

def sentences_split(texts):    
     
    '''Splits each text into a list of sentences. Returns a list of lists (of sentences)'''

    list_sentences = []
    for text in texts:
        text = text.replace(".", ". ")
        text = text.replace("\n", ". ")
        sentences = re.split("((?<=\.|\?)(\s|\.))", text)
        sentences2 = []
        for sentence in sentences:
            if len(sentence) > 5:
                sentences2.append(sentence)
        list_sentences.append(sentences2)
        
    return list_sentences;

################################
################################
### PLOT NUMBER OF SENTENCES ###
################################
################################

def sentences_plot(list_of_texts, ylim = (0, 0.3), max_sentences = 20, figsize = None, dpi = None, legend = None):    
     
    '''Produces a simple plot of the percentage frequency of texts according to their number of sentences. Set the maximum number of sentences to plot (default is 20) and the y-limits. Texts must already be split into lists of sentences.'''
    
    matplotlib.pyplot.figure(figsize = figsize, dpi = dpi)
    matplotlib.pyplot.ylim(ylim)
    matplotlib.pyplot.xlabel("Sentences per text")
    matplotlib.pyplot.ylabel("Percentage of texts")
    
    for texts in list_of_texts:
        lengths = []
        for sentences in texts:
            lengths.append(len(sentences))
        number_of_sentences = []
        frequency = []
        for i in range(1, max_sentences + 1):
            number_of_sentences.append(i)
            percent = lengths.count(i)/len(lengths)
            frequency.append(percent)        
        matplotlib.pyplot.plot(number_of_sentences, frequency)
    
    if legend != None:
        matplotlib.pyplot.legend(legend)
    
################################
################################
######### SPELL-CHECK ##########
################################
################################

def spellcheck_tokens(
    tokens, 
    language = "en",
    distance = 1               
):    
     
    '''Spell-checks the provided list of tokens and returns the corrected ones.
    
    Parameters
        ----------
        tokens   : the list of tokens to be spell-checked
        language : the language to perform the spell-check in
        distance : can be set to 1 or 2. It considers all words that are 1 or 2 letter permutations away (i.e. number of letter swaps) and then selects the most frequent one. The creator of the package suggests to use a distance of 1 to avoid silly things happening in longer words.'''
    
    spell = spellchecker.SpellChecker(language = language, distance = distance)
    counter = 0
    
    for token in tokens:
        counter += 1
        for i, word in enumerate(token):
            token[i] = spell.correction(word)
        if counter%20000 == 0:
            print(str(counter) + " tokens spell-checked.", sep=" ")
    
    return tokens;

################################
################################
# REMOVE STOPWORDS FROM TOKENS #
################################
################################

def remove_stopwords(tokens):    

    '''Removes stopwords from provided list of tokens. Returns the cleaned list.'''

    stop_words = set(nltk.corpus.stopwords.words('english')) 
    
    new_tokens = []
    
    for token in tokens:
        new_token = []
        for word in token:
            if word not in stop_words: 
                new_token.append(word)
        new_tokens.append(new_token)
                
    return new_tokens;

################################
################################
####### VECTORIZE TOKENS #######
################################
################################

def vectorize(
    tokens,
    index
):
    
    '''Vectorize a list of tokens given an embeddings index.
    
    Parameters
        ----------
        tokens : list; the list of tokens to be vectorized.
        index  : dict; the embeddings index to be used'''
        
    vectors = []
    for token in tokens:
        vector = []
        for word in token:
            vector.append(index.get(word))
        vectors.append(vector)
    
    return vectors;