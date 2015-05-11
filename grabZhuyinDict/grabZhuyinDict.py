# coding=utf8
import httplib2
import urllib2
import re
from BeautifulSoup import BeautifulSoup
from optparse import OptionParser
import httplib2
import HTMLParser
import codecs
import sys

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

def printAlertContent(searchPage):
    alertPos = searchPage.rfind('alert(\"')
    if(alertPos == -1):
        print 'ERROR: no result but no alert'
    alertStr = searchPage[alertPos+len('alert(\"'):]
    alertStr = alertStr[:alertStr.find('\')')]
    print "ERROR: no result: " + alertStr.decode('big5')
    return

def ParsePage(searchPage, vocabulary, recNo):
    soup = BeautifulSoup(searchPage)    #, fromEncoding="big5"
    num = soup.find('p', attrs={'class':'lable'})
    if(num == None): 
        printAlertContent(searchPage)
        return (False, "", "", False)
    numText = num.string.strip()
    if(len(numText) == 0 or numText.find(u'找到') == -1):
        printAlertContent(searchPage)
        return (False, "", "", False)
    if(recNo == 0):
        print numText
    #找到下一页
    nextPage = soup.find("a", text=re.compile(u"下一頁"))
    
    #找到uKey
    uKeyObj = soup.find("input", attrs={"name":"ukey"})
    if(uKeyObj == None):
        print "ERROR: no ukey found"
        return (False, "", "", False)
    uKey = uKeyObj['value']
    
    #找到serial
    serialObj = soup.find("input", attrs={"name":"serial"})
    if(serialObj == None):
        print "ERROR: no serial found"
        return (False, uKey, "", False)
    serial = serialObj['value']
    
    #找到词条table
    wordTable = num.findNextSibling('table')
    if (wordTable == None):
        print "ERROR: no table after result number"
        return (False, uKey, serial, False)

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
    return (nextPage != None, uKey, serial, True)
    

def GetWordsForZhuyin(strZhuyin, cookies, vocabulary):
    print "getting " + strZhuyin.decode('big5')
    
    recNo = 0
    bNextPage = True
    bResultFound = True
    uKey = ""
    serial = ""

    h = httplib2.Http()

    while (bNextPage and bResultFound):    
        urlSearch = GetUrlString(strZhuyin, recNo, uKey, serial)
        if(cookies != ""):
            myHeaders = {'Cookie':cookies}
        else:
            myHeaders = None

        resp, searchPage = h.request(urlSearch, headers=myHeaders)
        if('set-cookie' in resp):
            thisCookies = resp['set-cookie']
            cookies = thisCookies[:thisCookies.find(";")]

        bNextPage, uKey, serial, bResultFound = ParsePage(searchPage, vocabulary, recNo)
        if(bResultFound):
            recNo += 100
    
    return (cookies, recNo > 0)

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')
    opt = OptionParser()
    opt.add_option("-z", "--zhuyinList", dest="zhuyinList"
                   , default="", help="Zhuyin list file of Big5! encoded")
    opt.add_option("-o", "--outputFile", dest="outputFile"
                   , default="", help="File to store the vocabulary grabbed from the site")

    (options, args) = opt.parse_args()
    if(options.zhuyinList == "" or options.outputFile == ""):
        print "\'python grabZhuyinDict.py -help\' for help"
        exit()

    #"../zhuyinList.big5.txt"
    strFileZhuyinTable = options.zhuyinList

    fZhuyinList = open(strFileZhuyinTable, 'r')

    cookies = ""
    vocabulary = {}

    for strZhuyin in fZhuyinList:
        strZhuyin = strZhuyin.strip("\n \t")
        cookies,bResultFound = GetWordsForZhuyin(strZhuyin, cookies, vocabulary)
        #可能因为数据量太大，服务器不返回结果，可以通过指定声调来减少结果数量
        if(not bResultFound):
            cookies, bResultFound = GetWordsForZhuyin(strZhuyin+u"ˊ".encode('Big5'), cookies, vocabulary)
            cookies, bResultFound = GetWordsForZhuyin(strZhuyin+u"ˇ".encode('Big5'), cookies, vocabulary)
            cookies, bResultFound = GetWordsForZhuyin(strZhuyin+u"ˋ".encode('Big5'), cookies, vocabulary)
            cookies, bResultFound = GetWordsForZhuyin(u"˙".encode('Big5')+strZhuyin, cookies, vocabulary)
    
    fZhuyinList.close();

    #把词典内容存储到文件
    fVoca = codecs.open(options.outputFile, 'w', 'utf-8')
    for word in vocabulary:
        fVoca.write(word + "\t" + vocabulary[word] +"\n")

    fVoca.close()