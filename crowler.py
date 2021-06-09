import logging
from logging.handlers import RotatingFileHandler
import os, json, time, requests
from datetime import date, datetime, timedelta
import schedule
from environs import Env
import hmac
import hashlib
import pandas as pd
from urllib.parse import urlencode
from clickhouse_driver import Client
import telegram_send


log_file = "logs/debug.log"
env = Env()
env.read_env()
logger = logging.getLogger('coins')

KEY = env("API_KEY")
SECRET = env("SECRET_KEY")
COINS = env.list("COINS")
BASE_URL = env("BINANCE_ROOT_URL")
TIME_CALC = env("TIME_CALC")
BOT_TOKEN = env("BOT_TOKEN")
CHAT_ID = env("CHAT_ID")

epoch = datetime.utcfromtimestamp(0)

def setup_logging(logdir):
    global logger
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.DEBUG,
                        format=format_str,
                        filename=os.path.join(logdir, 'debug.log'),
                        filemode='a')

def unixtime_to_ms(dt):
    return int((dt - epoch).total_seconds() * 1000)

def ms_to_unixtime(ms):
    return datetime.fromtimestamp(ms/1000.0).strftime("%Y-%m-%d %H:%M:%S")

def str_to_dt(str_dt):
    return datetime.strptime(str_dt,'%Y-%m-%d %H:%M:%S')

def hashing(query_string):
    return hmac.new(SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_timestamp():
    return int(time.time() * 1000)

def dispatch_request(http_method):
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json;charset=utf-8',
        'X-MBX-APIKEY': KEY
    })
    return {
        'GET': session.get,
        'DELETE': session.delete,
        'PUT': session.put,
        'POST': session.post,
    }.get(http_method, 'GET')

def send_signed_request(http_method, url_path, payload={}):
    query_string = urlencode(payload, True)
    if query_string:
        query_string = "{}&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = 'timestamp={}'.format(get_timestamp())

    url = BASE_URL + url_path + '?' + query_string + '&signature=' + hashing(query_string)
    logger.info("{} {}".format(http_method, url))
    params = {'url': url, 'params': {}}
    response = dispatch_request(http_method)(**params)
    return response.json()

def send_public_request(url_path, payload={}):
    query_string = urlencode(payload, True)
    url = BASE_URL + url_path
    if query_string:
        url = url + '?' + query_string
    logger.info("{}".format(url))
    response = dispatch_request('GET')(url=url)
    return response.json()

def get_price():
    one_coin_price = []
    list_of_coins_price = []
    if not COINS:
        logger.error("List of coins is empty")
        return
    for coin in COINS:
        params = {
        "symbol": coin,
        "limit": "1"
        }
        response = send_public_request('/api/v3/trades' , params)
        for j in response:
            data = json.loads(json.dumps(j))
            get_time = ms_to_unixtime(data["time"])
            price = data["price"]
            if "BTC" in coin:
                response = send_public_request('/api/v3/trades' , {"symbol": "BTCUSDT", "limit": "1"})
                for b in response:
                    data = json.loads(json.dumps(b))
                    price_btc = data["price"]
                    price = float(price_btc) * float(price)
            one_coin_price = (str_to_dt(get_time),coin,float(price))
        list_of_coins_price.append(one_coin_price)
    return list_of_coins_price

def price_coins_to_click():
    try:
        click_client = Client('localhost',database='coins',user='stat', password='stat')
        click_client.execute (
            'INSERT INTO market (get_time,symbol,price_usdt) VALUES', get_price()
        )
        logger.info('Success insert')
    except Exception as exp:
        logger.error(exp)
        return print(str(exp))
    return

def get_transactions():
    one_coin_trn = []
    list_of_one_coin_trn =[]
    start_day = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    end_day = date.today().strftime("%Y-%m-%d 00:00:00")
    if not COINS:
        logger.error("List of coins is empty")
        return    
    for coin in COINS:
        params = {
        "symbol": coin,
        "startTime": unixtime_to_ms(str_to_dt(str(start_day))),
        "endTime": unixtime_to_ms(str_to_dt(str(end_day)))
        }
        response = send_signed_request('GET','/api/v3/myTrades' , params)
        if response:
           for j in response:
             data = json.loads(json.dumps(j))
             event_time = ms_to_unixtime(data["time"])
             amount = data["qty"]
             price = data["price"]
             action = 1 if bool(data["isBuyer"]) else 0 
             one_coin_trn = (str_to_dt(event_time),coin,float(amount),float(price),int(action),1)
             list_of_one_coin_trn.append(one_coin_trn)
    return(list_of_one_coin_trn)
    
def transactions_to_click():
    try:
        click_client = Client('localhost',database='coins',user='stat', password='stat')
        click_client.execute (
            'INSERT INTO transactions (event_time,symbol,amount,price,action,use) VALUES', get_transactions()
        )
        logger.info('Success insert')
    except Exception as exp:
        logger.error(exp)
        return print(str(exp))
    return

def profit_by_coins():
    profit_by_coin =[]
    list_of_all_profits = []
    if not COINS:
        logger.error("List of coins is empty")
        return
    try:
        click_client = Client('localhost',database='coins',user='stat', password='stat')
        for coin in COINS:
            result, columns = click_client.execute (
                f"select amount,price,action from coins.transactions where symbol='{coin}'",with_column_types=True
            )
            buy_calc = []
            buy_amount = []
            sell_calc = []
            sell_amount = []
            df = pd.DataFrame(result,columns=[tuple[0] for tuple in columns])
            for row in df.itertuples(index=False):
                if row[2] == 'buy':
                    m = row[0]*row[1]
                    buy_calc.append(m)
                    buy_amount.append(row[0])
                if row[2] == 'sell':
                    m = row[0]*row[1]
                    sell_calc.append(m)
                    sell_amount.append(row[0])
            start_market = sum(buy_calc) - sum(sell_calc)
            current_amount = sum(buy_amount) - sum(sell_amount)
            price_coin, = click_client.execute (
                f"select price_usdt from market where symbol='{coin}' order by get_time desc limit 1;"
            )
            current_market = price_coin[0]*current_amount
            profit_by_coin =[datetime.today(),coin,round(current_amount,2),round(start_market,2),round(current_market-start_market,2)]
            list_of_all_profits.append(profit_by_coin)        
    except Exception as exp:
        logger.error(exp)
        return print(str(exp))
    return list_of_all_profits

def telegram_bot_sendtext(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    headers = {'Content-type': 'application/json'}

    data = {
       "chat_id" : CHAT_ID,
       "text" : message,
       "parse_mode" : "HTML",
       "disable_web_page_preview" : True,
       "disable_notification" : True
    }
    try:
       response = requests.post(url, data=json.dumps(data), headers=headers)
       if response.status_code == 200:
          r_data = response.json()
          logger.info(r_data)
       else:
          logger.error(f"http status from Telegram API: {response.status_code}, {response.text}")
    except Exception as exp:
       logger.error (str(exp))

def profit_to_click():
    try:
        sum_profit = 0
        message = "<b>Coins:</b>\n"
        price_coins_to_click()
        agg_coins_road = profit_by_coins()
        click_client = Client('localhost',database='coins',user='stat', password='stat')
        click_client.execute (
            'INSERT INTO coins_road (calc_time,symbol,amount,start_market,profit) VALUES', agg_coins_road
        )
        for coin in agg_coins_road:
           sum_profit =  sum_profit + coin[4]
           message = message + f" {coin[0].strftime('%d%m%Y %H:%M:%S')} <a href=\"https://ru.tradingview.com/symbols/{str(coin[1])}/\">{str(coin[1])}</a>: <b>{str(coin[4])}</b>" + "\n"
        logger.info('Success insert')
        telegram_bot_sendtext(message + f"<b>Profit</b>: {round(sum_profit,2)} \n")
    except Exception as exp:
        logger.error(exp)
        return print(str(exp))
    return
    
if __name__ == '__main__':
    setup_logging("logs")
    schedule.every().day.at('00:00:01').do(transactions_to_click)
    schedule.every(int(TIME_CALC)).minutes.do(profit_to_click)
    while True:
        schedule.run_pending()
        time.sleep(1)
    