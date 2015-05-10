# coding=utf8
import httplib2
import urllib2
import re
from BeautifulSoup import BeautifulSoup
from optparse import OptionParser
import httplib2
import HTMLParser
import codecs


def GetFirstPageUrl(strZhuyin):
    urlSearch = "http://dict.revised.moe.edu.tw/cgi-bin/newDict/dict.sh?idx=dict.idx"
    urlSearch += "&cond=" + urllib2.quote(strZhuyin)
    urlSearch += "&pieceLen=100&fld=3&cat=&imgFont=1"
    return urlSearch

def GetNextPageUrl(strZhuyin, recNo, uKey, serial):
    urlSearch = "http://dict.revised.moe.edu.tw/cgi-bin/newDict/dict.sh?"
    urlSearch += "cond=" + urllib2.quote(strZhuyin)
    urlSearch += "&pieceLen=100&fld=3&cat="
    urlSearch += "&ukey=" + uKey
    urlSearch += "&serial=" + str(serial)
    urlSearch += "&recNo=" + str(recNo)
    urlSearch += "&op=l&imgFont=1"
    return urlSearch

def GetUrlString(strZhuyin, recNo, uKey, serial):
    if recNo == 0:
        return GetFirstPageUrl(strZhuyin)
    else:
        return GetNextPageUrl(strZhuyin, recNo, uKey, serial)

def AddToVocabulary(word, zhuyins, vocabulary):
    if( word in vocabulary):
        ori = vocabulary[word]
        #可能是多音字、多音词
        if(ori.find(zhuyins) == -1):
            ori += ","+zhuyins
            vocabulary[word] = ori
    else:
        vocabulary[word] = zhuyins
    return

def ParsePage(searchPage, vocabulary, recNo):
    soup = BeautifulSoup(searchPage)    #, fromEncoding="big5"
    num = soup.find('p', attrs={'class':'lable'})
    if(num == None): 
        print "ERROR:no result number found"
        return (False, "", "")
    numText = num.string.strip()
    if(len(numText) == 0 or numText.find(u'找到') == -1):
        print "ERROR:no result number found"
        return (False, "", "")
    if(recNo == 0):
        print numText
    #找到下一页
    nextPage = soup.find("a", text=re.compile(u"下一頁"))
    
    #找到uKey
    uKeyObj = soup.find("input", attrs={"name":"ukey"})
    if(uKeyObj == None):
        print "ERROR: no ukey found"
        return (False, "", "")
    uKey = uKeyObj['value']
    
    #找到serial
    serialObj = soup.find("input", attrs={"name":"serial"})
    if(serialObj == None):
        print "ERROR: no serial found"
        return (False, uKey, "")
    serial = serialObj['value']
    
    #找到词条table
    wordTable = num.findNextSibling('table')
    if (wordTable == None):
        print "ERROR: no table after result number"
        return (False, uKey, serial)

    h = HTMLParser.HTMLParser()

    trList = wordTable.findAll('tr')
    for tr in trList:
        tdList = tr.findAll('td')
        if(len(tdList) != 3):continue
        lastNumber = str(tdList[0].string)
        word    = tdList[1].findNext('a').string
        if(word == None):
            continue   #可能是含有以图片表示的汉字
        zhuyins = tdList[2].text
        if(zhuyins == None):
            continue

        AddToVocabulary(h.unescape(word).strip()
                        , h.unescape(zhuyins).strip()
                        , vocabulary)
    print lastNumber
    return (nextPage != None, uKey, serial)
    

def GetWordsForZhuyin(strZhuyin, cookies, vocabulary):
    print "getting " + strZhuyin.decode('big5')
    
    recNo = 0
    bNextPage = True
    uKey = ""
    serial = ""

    h = httplib2.Http()

    while bNextPage:    
        urlSearch = GetUrlString(strZhuyin, recNo, uKey, serial)
        if(cookies != ""):
            myHeaders = {'Cookie':cookies}
        else:
            myHeaders = None

        resp, searchPage = h.request(urlSearch, headers=myHeaders)
        if('set-cookie' in resp):
            thisCookies = resp['set-cookie']
            cookies = thisCookies[:thisCookies.find(";")]

        bNextPage, uKey, serial = ParsePage(searchPage, vocabulary, recNo)
        recNo += 100
    
    return cookies

if __name__ == '__main__':

    opt = OptionParser()
    opt.add_option("-z", "--zhuyinList", dest="zhuyinList"
                   , default="", help="Zhuyin list file of Big5! encoded")
    opt.add_option("-o", "--outputFile", dest="outputFile"
                   , default="", help="File to store the vocabulary grabbed from the site")

    (options, args) = opt.parse_args()
    if(options.zhuyinList == "" or options.outputFile == ""):
        exit()

    #"../zhuyinList.big5.txt"
    strFileZhuyinTable = options.zhuyinList

    fZhuyinList = open(strFileZhuyinTable, 'r')

    cookies = ""
    vocabulary = {}

    for strZhuyin in fZhuyinList:
        strZhuyin = strZhuyin.strip("\n \t")
        cookies = GetWordsForZhuyin(strZhuyin, cookies, vocabulary)
    
    fZhuyinList.close();

    #把词典内容存储到文件
    fVoca = codecs.open(options.outputFile, 'w', 'utf-8')
    for word in vocabulary:
        fVoca.write(word + "\t" + vocabulary[word] +"\n")

    fVoca.close()