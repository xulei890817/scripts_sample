#!/usr/bin/env python

# encoding: utf-8

'''
 * Create File Script_avg_kline
 * Created by leixu on 2018/5/12
 * IDE PyCharm
'''
import collections

import itertools
from MaxValue.utils import proxy

proxy.proxy = "http://192.168.2.24:1001"

from MaxValue.market import MarketClass
from MaxValue.plan import BasePlan, UpdateHandler
import asyncio
import arrow
from MaxValue.utils.logger import logger
import logging
from copy import deepcopy
from statistics import mean

logger.setLevel(logging.INFO)

from token_dict import okex_api_key
from token_dict import okex_sign


class OkexUpdateHandler(UpdateHandler):

    def ticker(self, data):
        pass

    def k_line(self, data):
        pass

    def depth(self, data):
        pass


class KLineMode(object):
    def __init__(self, timestamp, max_price, min_price, open_price, close_price):
        self.timestamp = timestamp
        self.max_price = float(max_price)
        self.min_price = float(min_price)
        self.open_price = float(open_price)
        self.close_price = float(close_price)


class PlanA(BasePlan):
    def __init__(self, loop):
        super(PlanA, self).__init__(loop)
        self.kline = collections.deque(maxlen=1000)
        self.last_kline_mode = None
        self.current_data = None
        self.current_flag = None

    def login_market(self):
        def okex_update_handler():
            def ticker(data):
                # 记录当前的买一卖一
                self.okex_market.sell = data["data"]["sell"]
                self.okex_market.buy = data["data"]["buy"]

            def k_line(data):
                for item in data["data"]:
                    kline_mode = KLineMode(int(item[0]) / 1000, item[2], item[3], item[1], item[4])

                    if self.last_kline_mode is None:
                        self.last_kline_mode = kline_mode
                        continue

                    if self.last_kline_mode.timestamp != int(item[0]) / 1000:
                        self.kline.appendleft(deepcopy(kline_mode))
                        self.last_kline_mode = kline_mode
                    else:
                        self.last_kline_mode = kline_mode

            def depth(data):
                pass

            # 设置更新的callback
            setattr(okex_update_handler, "ticker", ticker)
            setattr(okex_update_handler, "k_line", k_line)
            setattr(okex_update_handler, "depth", depth)
            return okex_update_handler

        self.okex_market = self.login_into_market(MarketClass.OKEX, api_key=okex_api_key, sign=okex_sign, update_handler=okex_update_handler)

    async def start_rule(self):
        # 订阅频道

        await self.okex_market.api.sub_channel("ok_sub_futureusd_btc_ticker_quarter")
        await self.okex_market.api.sub_channel("ok_sub_futureusd_btc_kline_quarter_1min")
        # 如果无需订阅当前频道，可注释
        # await self.okex_market.api.sub_channel("ok_sub_futureusd_btc_depth_this_week")

        # 保持程序运行
        while True:
            # 每隔60s苏醒一次
            await asyncio.sleep(60)
            logger.info("开始尝试规则")
            if len(self.kline) > 20:
                M50 = list(itertools.islice(self.kline, 0, 20))
                M10 = M50[0:10]

                def compute_avg(data_list):
                    # 如果需要计算的话，可以讲func a改写成一些基本的计算函数
                    def a(item):
                        return item

                    return mean(map(lambda x: x.open_price, data_list))

                MV50 = compute_avg(M50)
                MV10 = compute_avg(M10)
                logger.info(f"计算MV50和MV10:{MV50}---{MV10}")

                # build_type buy_long,buy_short,sell_long,sell_short
                async def begin_trade(build_type="buy_long", price=None):
                    if build_type == "buy_long":
                        self.current_flag = "买多建仓"
                    if build_type == "buy_short":
                        self.current_flag = "买空平仓"
                    if build_type == "sell_long":
                        self.current_flag = "卖多平仓"
                    if build_type == "sell_short":
                        self.current_flag = "卖空建仓"

                    logger.info(f"当前的交易标志:{self.current_flag}")
                    # 预设交易信息
                    trade = self.okex_market.api.trade().lever_rate(10).symbol("btc_usd").contract_type("quarter")
                    # 开仓或者平仓，以市价成交
                    aa = build_type.split("_")
                    # 采用定价方式，使用这种方式即可
                    # trade.start(aa[0], aa[1]).amount(1).price(price)
                    trade.start(aa[0], aa[1]).amount(1).as_market_price()
                    result = await trade.go()
                    # 创建order
                    order = self.okex_market.api.order(result["order_id"], symbol="btc_usd", contract_type="quarter")

                    # 更新order信息
                    # 0等待成交 1部分成交 2全部成交 -1撤单 4撤单处理中 5撤单中
                    # 等待单全部完成
                    while True:
                        await order.info()
                        if order.status == 2:
                            break
                        else:
                            await asyncio.sleep(30)

                    # 如果当前是平仓的操作，则重置交易标志位
                    if "平仓" in self.current_flag:
                        logger.debug("平仓成功，重置标志位，进行下一轮")
                        self.current_flag = None

                if MV10 >= MV50:
                    if self.current_flag is None:
                        logger.info(f"逻辑进入:买多建仓")
                        await begin_trade("buy_long")
                else:
                    if self.current_flag == "sell_short":
                        logger.info(f"逻辑进入:买空平仓")
                        await begin_trade("buy_short")

                if MV10 < MV50:
                    if self.current_flag is None:
                        logger.info(f"逻辑进入:卖空建仓")
                        await begin_trade("sell_short")
                else:
                    if self.current_flag == "sell_short":
                        logger.info(f"逻辑进入:卖多平仓")
                        await begin_trade("sell_long")


if __name__ == "__main__":
    c_loop = asyncio.get_event_loop()

    plan_a = PlanA(c_loop)
    print("开始运行计划" + str(arrow.get()))
    c_loop.run_until_complete(plan_a.start_rule())
