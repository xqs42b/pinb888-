# coding=utf-8


import requests
import json
import time
import uuid
import re
import traceback
import mybooks
import DB_manager
from fuzzywuzzy import fuzz

import sys
reload(sys)
sys.setdefaultencoding('utf8')

_SAVE_LOGIN_PATH = './cookies/pinnacle_login.txt'
_SP = '29' # 足球
# _SP = '33' # 网球
# _LOCALE = 'zh_CN'
_LOCALE = 'en_US'

class Pinnacle:
    '''pinnacle操作模块'''

    def __init__(self, username=None, password=None):
        self._username = username
        self._password = password
        self._init_cookies = self.get_init_cookie()

    def is_login(self):
        '''判断是否登录'''
        try:
            with open(_SAVE_LOGIN_PATH, 'r') as f:
                cookies_str = f.read()
            if cookies_str:
                content = self.get_balance()
                if content:
                    return True
                else:
                    return False
            else:
                return False
        except Exception as err:
            print('is_login:', err)
            return False

    def login(self):
        '''账户登录'''
        url = 'https://www.pinb888.com/member-service/v1/login'
        headers = self.make_headers()
        form_data = {
            'loginId': self._username,
            'password': self._password
        }
        params = {
            'locale': _LOCALE
        }
        cookies = self._init_cookies
        response = self.request_server(url, isGet=False, cookies=cookies, params=params,\
            headers=headers, formData=form_data, timeout=60)
        if not response:
            return ''
        login_cookies = dict(response.cookies)
        try:
            str_cookies = json.dumps(login_cookies)
            with open(_SAVE_LOGIN_PATH, 'w') as f:
                f.write(str_cookies)
            return login_cookies
        except Exception as err:
            print('login:', err)
            return ''

    def get_init_cookie(self):
        '''获取初始cookie'''
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            # 'accept-encoding': 'gzip, deflate, br',
            # 'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'accept-language': 'en-us,en;q=0.5',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)\
                Chrome/68.0.3440.106 Safari/537.36',
        }
        url = 'https://www.pinb888.com/en/'
        init_num = 0
        while True:
            if init_num > 5:
                print u'网络有问题,请稍后在试!'
                return ''
            response = self.request_server(url, headers)
            if response:
                init_cookies = dict(response.cookies)
            else:
                init_num += 1
                continue

            try:
                return init_cookies
            except Exception as err:
                print('get_init_cookie:', err)
                init_num += 1
                continue                

    def get_balance(self):
        '''判断用户是否登录，获取用户剩余金额'''
        url = 'https://www.pinb888.com/member-service/v1/account-balance'
        headers = self.make_headers()
        # headers['referer'] = 'https://www.pinb888.com/zh-cn/sports'
        headers['referer'] = 'https://www.pinb888.com/en/sports'
        headers['content-type'] = '4'
        form_data = {
            'json': ''
        }
        params = {
            'locale': _LOCALE 
        }
        try:
            with open(_SAVE_LOGIN_PATH, 'r') as f:
                cookies_str = f.read()
            if cookies_str:
                cookies = json.loads(cookies_str)
            else:
                return ''
        except Exception as err:
            print('get_balance:', err)
            return ''
        cookies = cookies 
        response = self.request_server(url, isGet=False, headers=headers, formData=form_data, params=params, \
            cookies=cookies)
        if response:
            content = response.content
        else:
            return ''
        if content:
            content = json.loads(content)
            if content['success']:
                return content
            else:
                return ''
        else:
            return ''

    def get_login_cookie(self):
        ''' 获取登录的cookie '''
        if self.is_login():
            print u'不用重现登录'
            try:
                with open(_SAVE_LOGIN_PATH, 'r') as f:
                    cookies_str = f.read()
                cookies = json.loads(cookies_str)
                # cookies如果为空
                if not cookies:
                    return self.login
                return cookies
            except Exception as error:
                print('get_login_cookie:', error)
                return ''
        else:
            print u'需要重现登录'
            return self.login()

    def get_sport_data(self):
        '''获取所有足球滚球比赛的数据'''
        url = 'https://www.pinb888.com/sports-service/sv/odds/events'
        headers = self.make_headers()
        headers['referer'] = 'https://www.pinb888.com/en/sports'
        d = time.strftime('%Y-%m-%d', time.localtime(time.time() + (24 * 3600)))
        params = {
            'mk': '2', 
            'sp': _SP,
            'ot': '1',
            'btg': '1',
            'o': '1',
            'lg': '',
            'ev': '',
            'd': d,
            'l': '3',
            'v': '',
            'more': 'false',
            'c': 'CN',
            # 'c': 'US',
            'tm': '0',
            'g': '',
            'pa': '0',
            '_': int((time.time()) * 1000),
            'locale': _LOCALE,
        }
        cookies = self.get_login_cookie()
        response = self.request_server(url, cookies=cookies, headers=headers, params=params)
        if response:
            try:
                content = json.loads(response.content)
                live_datas = content['l'][0][2]
                if live_datas:
                    sport_data = []
                    for live_data in live_datas:
                        match_datas = live_data[2]
                        for match_data in match_datas:
                            new_match = {}
                            match_id = match_data[0]
                            home = match_data[1]
                            away = match_data[2]
                            new_match['home'] = home
                            new_match['away'] = away
                            new_match['hdp'] = {}
                            new_match['ou'] = {}
                            new_match['1x2'] = {}
                            all_handicaps = match_data[8]
                            if '0' in all_handicaps:
                                handicaps0 = all_handicaps['0']
                                # 让分盘数据
                                if handicaps0[0]:
                                    resHDPs = handicaps0[0]
                                    hdp_data = self.each_handicap(resHDPs, match_id, hdp_name='hdp', is_half=False)
                                    new_match['hdp']['0'] = hdp_data
                                # 大小盘数据
                                if handicaps0[1]:
                                    resOU = handicaps0[1]
                                    ou_data = self.each_handicap(resOU, match_id, hdp_name='ou', is_half=False)
                                    new_match['ou']['0'] = ou_data
                                # 1x2数据
                                if handicaps0[2]:
                                    res1X2 = handicaps0[2]
                                    data_1x2 = self.each_handicap(res1X2, match_id, hdp_name='1x2', is_half=False)
                                    new_match['1x2']['0'] = data_1x2
                            if '1' in all_handicaps:
                                handicaps1 = all_handicaps['1']
                                # 让分盘数据
                                if handicaps1[0]:
                                    resHDPs = handicaps1[0]
                                    hdp_data = self.each_handicap(resHDPs, match_id, hdp_name='hdp')
                                    new_match['hdp']['1'] = hdp_data
                                # 大小盘数据
                                if handicaps1[1]:
                                    resOU = handicaps1[1]
                                    ou_data = self.each_handicap(resOU, match_id, hdp_name='ou')
                                    new_match['ou']['1'] = ou_data
                                # 1x2数据
                                if handicaps1[2]:
                                    res1X2 = handicaps1[2]
                                    data_1x2 = self.each_handicap(res1X2, match_id, hdp_name='1x2')
                                    new_match['1x2']['1'] = data_1x2
                            sport_data.append(new_match)
                    print '========================================'
                    return sport_data
                else:
                    return ''
            except Exception as err:
                print('get_sport_data:', err)
                traceback.print_exc()
                return ''
        else:
            return '' 

    def each_handicap(self, hdpData, match_id, hdp_name, is_half=True):
        '''
        遍历盘口数据,返回清洗后的数据
        hdpData: 每个盘口类型的数据,如：让分盘数据，1x2数据
        match_id: 比赛的id
        hdp_name: 盘口类型的名字，如：hdp, 1x2, ou
        is_half: 判断是不是半场，如果是True，表示半场；False表示全场
        '''
        if not hdpData:
            return ''
        if is_half:
            half_val = '|1'
        else:
            half_val = '|0'

        hdp_list = []
        if hdp_name == 'hdp':
            hdp_num = '2'
            for hdp in hdpData:
                one_hdp1 = {}
                one_hdp2 = {}
                position1 = '|0'
                position2 = '|1'
                one_hdp1['koef'] = hdp[3]
                one_hdp1['bet_name'] = 'AH1'
                one_hdp1['bet_value'] = hdp[1] if hdp[1] != 0.0 else 0
                one_hdp1['selectionId'] = str(hdp[7]) + '|' + str(match_id) + \
                    half_val + '|' + hdp_num + position1 + ('|' + str(hdp[8]))\
                    + ('|' + str(one_hdp1['bet_value'])) + position1
                # print one_hdp1['selectionId']
                one_hdp2['koef'] = hdp[4]
                one_hdp2['bet_name'] = 'AH2'
                one_hdp2['bet_value'] = hdp[0] if hdp[0] != 0.0 else 0
                one_hdp2['selectionId'] = str(hdp[7]) + '|' + str(match_id) +\
                    half_val + '|' + hdp_num + position2 + ('|' + str(hdp[8]))\
                    + ('|' + str(one_hdp2['bet_value'])) + position2
                # print one_hdp2['selectionId']
                hdp_list.append(one_hdp1)
                hdp_list.append(one_hdp2)
            return hdp_list
        elif hdp_name == 'ou':
            for ou in hdpData:
                hdp_num = '3'
                one_ou1 = {}
                one_ou2 = {}
                position1 = '0'
                position2 = '1'
                one_ou1['koef'] = ou[2] 
                one_ou1['bet_name'] = 'TO'
                one_ou1['bet_value'] = ou[1] if (int(ou[1]) != ou[1]) else int(ou[1])
                one_ou1['selectionId'] = str(ou[4]) + '|' + str(match_id) + half_val\
                    + '|' + hdp_num + '|' + str(int(hdp_num) + int(position1)) +\
                    ('|' + str(ou[5])) + ('|' + str(one_ou1['bet_value'])) + ('|' + position1)
                one_ou2['koef'] = ou[3]
                one_ou2['bet_value'] = ou[1] if (int(ou[1]) != ou[1]) else int(ou[1])
                one_ou2['bet_name'] = 'TU'
                one_ou2['selectionId'] = str(ou[4]) + '|' + str(match_id) + half_val\
                    + '|' + hdp_num + '|' + str(int(hdp_num) + int(position2)) +\
                    ('|' + str(ou[5])) + ('|' + str(one_ou2['bet_value'])) + ('|' + position2)
                # print one_ou1['koef'], one_ou1['selectionId']
                # print one_ou2['koef'], one_ou2['selectionId']
                hdp_list.append(one_ou1)
                hdp_list.append(one_ou2)
            return hdp_list
        elif hdp_name == '1x2':
            hdp_num = '1'
            one_1x2_1 = {}
            one_1x2_2 = {}
            one_1x2_3 = {}
            position1 = '0'
            position2 = '1'
            position3 = '2'
            points = '0'
            one_1x2_1['koef'] = hdpData[1]
            one_1x2_1['bet_name'] = '1'
            one_1x2_1['bet_value'] = None
            one_1x2_1['selectionId'] = str(hdpData[3]) + '|' + str(match_id) + half_val\
                + '|' + hdp_num + '|' + position1 + ('|' + str(hdpData[4])) + ('|' + points)\
                + ('|' + position1)
            one_1x2_2['koef'] = hdpData[0]
            one_1x2_2['bet_name'] = '2'
            one_1x2_2['bet_value'] = None
            one_1x2_2['selectionId'] = str(hdpData[3]) + '|' + str(match_id) + half_val\
                + '|' + hdp_num + '|' + position2 + ('|' + str(hdpData[4])) + ('|' + points)\
                + ('|' + position2)
            one_1x2_3['koef'] = hdpData[2]
            one_1x2_3['bet_name'] = 'X'
            one_1x2_3['bet_value'] = None
            one_1x2_3['selectionId'] = str(hdpData[3]) + '|' + str(match_id) + half_val\
                + '|' + hdp_num + '|' + position3 + ('|' + str(hdpData[4])) + ('|' + points)\
                + ('|' + position3)
            # print hdpData[1], one_1x2_1['selectionId']
            # print hdpData[0], one_1x2_2['selectionId']
            # print hdpData[2], one_1x2_3['selectionId']
            hdp_list.append(one_1x2_1)
            hdp_list.append(one_1x2_2)
            hdp_list.append(one_1x2_3)
            return hdp_list
        else:
            return ''

    def open_ticket(self, selectionId):
        '''
        打开盘口
        selectionId: 盘口id
        '''
        url = 'https://www.pinb888.com/member-service/v1/ticket'
        params = {
            'selectionId': selectionId,
            'ot': '1',
            '_': int(time.time() * 1000),
            'locale': _LOCALE 
        }
        headers = self.make_headers()
        try:
            with open(_SAVE_LOGIN_PATH, 'r') as f:
                cookies_str = f.read()
            if cookies_str:
                cookies = json.loads(cookies_str)
            else:
                return ''
        except Exception as err:
            print('open_ticket:', err)
            return ''
        response = self.request_server(url, headers=headers, params=params, cookies=cookies)
        if not response:
            return ''
        ticket_res = response.content
        print ticket_res
        if ticket_res:
            ticket_info = json.loads(ticket_res)
            return ticket_info
        else:
            return ''

    def place_bet(self, stake, selectionId, odds):
        '''
        投注
        stake: 投注金额
        selectionId: 盘口id,
        odds: 该盘口最新的赔率
        '''
        url = 'https://www.pinb888.com/bet-placement/buyV2'
        uuid_str = str(uuid.uuid4())
        params = {
            'uniqueRequestId': uuid_str,
            'locale': _LOCALE
        }
        payload_data = {
            "oddsFormat": 1,
            "selections":[
                {
                    "stake": str(stake),
                    "selectionId": selectionId,
                    "odds": str(odds),
                    "uniqueRequestId": str(uuid.uuid4()),
                    "wagerType": "NORMAL"
                }
            ]
        }
        headers = self.make_headers()
        headers['accept'] = 'application/json, text/javascript, */*; q=0.01'
        # headers['referer'] = 'https://www.pinb888.com/zh-cn/sports'
        headers['referer'] = 'https://www.pinb888.com/en/sports'
        headers['content-type'] = 'application/json'
        headers['content-length'] = str(len(str(payload_data)))
        try:
            with open(_SAVE_LOGIN_PATH, 'r') as f:
                cookies_str = f.read()
            if cookies_str:
                cookies = json.loads(cookies_str)
            else:
                return ''
        except Exception as err:
            print('place_bet:', err)
            return ''
        response = self.request_server(url, isGet=False, headers=headers,\
            cookies=cookies, params=params, jsonData=payload_data) 
        try:
            result = response.content
            result = json.loads(result)
        except:
            return ''
        print json.dumps(result)
        return result 

    def make_headers(self):
        ''''制作头信息'''
        headers = {
            'accept': '*/*',
            # 'accept-encoding': 'gzip, deflate, br',
            # 'accept-language': 'zh-CN,zh;q=0.9',
            'accept-language': 'en-us,en;q=0.5',
            'adrum': 'isAjax:true',
            # 'content-length': '0',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://www.pinb888.com',
            'referer': 'https://www.pinb888.com/en/',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36\
                (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest'
        }
        return headers

    def request_server(self, url, headers, isGet=True, cookies=None, jsonData=None, formData=None, params=None, timeout=3):
        '''
        向服务器发出请求
        url: 请求路径
        headers: 请求头信息
        isGET: 是get请求还是post请求，默认是get请求，isGet=False表示post请求
        cookies: 请求的cookie
        params: url后缀传值，传值类型是字典
        jsonData: 表示post请求json传值, 传值类型是字典
        formData: 表示post请求字典传值, 传值类型是字典
        '''
        try:
            if isGet:
                response = requests.get(url, headers=headers, params=params,\
                    cookies=cookies, allow_redirects=False, timeout=timeout)
            else:
                response = requests.post(url, headers=headers, data=formData, json=jsonData,\
                    params=params, cookies=cookies, allow_redirects=False, timeout=timeout)
            if response.status_code == 200:
                print response.url
                return response
            else:
                print(response.status_code)
                print response.url
                # print(response.content)
                return ''
        except Exception as err:
            print('request_server:', err)
            traceback.print_exc()
            return ''

    ''' pinb888操作部分 '''

    def find_event(self, bet):
        ''' 接收数据 '''

        live_data_num = 3
        while True:
            if live_data_num > 5:
                return False
            live_data = self.get_sport_data()
            is_continue = False
            for ld in live_data:
                chinese_word_obj = re.compile(u'[\u4e00-\u9fa5]')
                chinese_match = chinese_word_obj.search(ld['home'])
                if chinese_match:
                    print u'有中文, 从新获取pinb888的数据！'
                    live_data_num += 1
                    is_continue = True
                    break
            if is_continue:
                time.sleep(3)
                continue
            if not live_data:
                live_data_num += 1
            else:
                break

        if not bet:
            return False
        bet_home = bet['home']
        bet_away = bet['away']
        print bet_home
        print bet_away
        print bet['bet_name']
        print bet['bet_value']
        print bet['koef']

        for data in live_data: 
            print '--------------'
            # print data['home']
            # print data['away']
            home_fuzzy_res = fuzz.ratio(data['home'], bet_home)
            away_fuzzy_res = fuzz.ratio(data['away'], bet_away)
            print 'home_fuzzy_res:', home_fuzzy_res
            print 'away_fuzzy_res:', away_fuzzy_res
            if (home_fuzzy_res > 85) and (away_fuzzy_res > 85):
                print 'bet_name:', bet['bet_name']
                if bet['bet_name'] in mybooks.bet_1x2_list:
                    data_1x2 = data['1x2']
                    operate_res = self.operate_1x2(bet, data_1x2)
                elif bet['bet_name'] in mybooks.bet_ah_list:
                    data_ah = data['hdp']
                    operate_res = self.operate_ah(bet, data_ah)
                elif bet['bet_name'] in mybooks.bet_ou_list:
                    data_ou = data['ou']
                    operate_res = self.operate_ou(bet, data_ou)
                else:
                    operate_res = False
                return operate_res
        else:
            return False


    def operate_1x2(self, bet, data):
        ''' 胜负盘操作 '''
        print u'开始胜负盘操作'
        if bet['period'] == 'regular time':
            current_data = data.get('0', '')
        elif bet['period'] == '1st quarter':
            current_data = data.get('1', '')
        else:
            return False
        for c_data in current_data:
            if c_data['bet_name'] == bet['bet_name']:
                ticket_res = self.open_ticket(c_data['selectionId'])
                return self.to_do_bet(ticket_res)
        else:
            return False

    def operate_ah(self, bet, data):
        ''' 让分盘操作 '''
        print u'开始让分盘操作'
        if bet['period'] == 'regular time':
            current_data = data.get('0', '')
        elif bet['period'] == '1st quarter':
            current_data = data.get('1', '')
        else:
            return False
        for c_data in current_data:
            if (c_data['bet_name'] == bet['bet_name']) and (c_data['bet_value'] == bet['bet_value']):
                ticket_res = self.open_ticket(c_data['selectionId'])
                return self.to_do_bet(ticket_res)
        else:
            return False

    def operate_ou(self, bet, data):
        ''' 大小球操作 '''
        print u'开始大小球操作'
        if bet['period'] == 'regular time':
            current_data = data.get('0', '')
        elif bet['period'] == '1st quarter':
            current_data = data.get('1', '')
        else:
            return False
        for c_data in current_data:
            if (c_data['bet_name'] == bet['bet_name']) and (c_data['bet_value'] == bet['bet_value']):
                ticket_res = self.open_ticket(c_data['selectionId'])
                return self.to_do_bet(ticket_res)
        else:
            return False

    def to_do_bet(self, ticket_info):
        ''' 开始投注 '''
        print u'开始投注'
        if not ticket_info:
            return False
        try:
            if ticket_info['status'] == 'OK':
                odds = ticket_info['odds']
                stake = 2 
                selectionId = ticket_info['selectionId']
                place_bet_res = self.place_bet(selectionId=selectionId, odds=odds, stake=stake)
                if not place_bet_res:
                    return False
                try:
                    place_status = place_bet_res['response'][0]['status']
                    if(place_status == 'ACCEPTED') or (place_status == 'PENDING_ACCEPTANCE'):
                        return True
                    else:
                        print u'投注结果:', place_bet_res['response'][0]['status']
                        return False
                except Exception as error:
                    print('to_do_bet_error:', error)
                    return False
            else:
                print u'打开盘口错误原因：', ticket_info['status']
                return False
        except Exception as error:
            print 'to_do_bet_error:', error
            print 'ticket_info:',ticket_info
            return False


