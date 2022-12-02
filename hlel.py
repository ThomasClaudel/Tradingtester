import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import mplfinance as mpf
import pathlib
import cProfile, pstats, io
import time
import pytz
import math
import pause

if not mt5.initialize():
    print("initialize() failed")
    mt5.shutdown()

fdgfdg
def profile(fnc):
    """A decorator that uses cProfile to profile a function"""

    def inner(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        retval = fnc(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
        return retval

    return inner


def InitialDataFrames(Stock, LocalTime):
    # I dont yet understand why it has to be +2 hours and not +1 hour
    LocalTime += timedelta(hours=1)
    data1 = pd.DataFrame(mt5.copy_rates_from(Stock, mt5.TIMEFRAME_M5, LocalTime, 288))
    data1['time'] = pd.to_datetime(data1['time'], unit='s')
    data1 = data1.set_index(pd.DatetimeIndex(data1['time']))

    data2 = pd.DataFrame(mt5.copy_rates_from(Stock, mt5.TIMEFRAME_M15, LocalTime, 144))
    data2['time'] = pd.to_datetime(data2['time'], unit='s')
    data2 = data2.set_index(pd.DatetimeIndex(data2['time']))

    data3 = pd.DataFrame(mt5.copy_rates_from(Stock, mt5.TIMEFRAME_H1, LocalTime, 50))
    data3['time'] = pd.to_datetime(data3['time'], unit='s')
    data3 = data3.set_index(pd.DatetimeIndex(data3['time']))

    data1['12_EMA'] = data1.close.ewm(span=12, adjust=False).mean()
    data1['26_EMA'] = data1.close.ewm(span=26, adjust=False).mean()
    data1['15m_EMA'] = data2.close.ewm(span=50, adjust=False).mean()
    data1['1h_EMA'] = data3.close.ewm(span=50, adjust=False).mean()
    data1['macd'] = data1['12_EMA'] - data1['26_EMA']
    data1['macdsignal'] = data1.macd.ewm(span=9, adjust=False).mean()
    data1['histogram'] = data1['macd'] - data1['macdsignal']
    data1 = data1.fillna(method='ffill')
    return data1


def LocalActions(data1):
    Continue = False
    CriteriaInfo = [0, 0, 0]
    if (data1['macd'][-1] < data1['macdsignal'][-1] and data1['macd'][-2] > data1['macdsignal'][-2]) or (
            data1['macd'][-1] > data1['macdsignal'][-1] and data1['macd'][-2] < data1['macdsignal'][-2]):
        Continue = True
    if Continue:
        # macd and macdsignal cross
        count1 = -3
        crossings = np.array([0] * len(data1.index))
        # For previous crossing
        for i in data1['histogram']:
            count1 += 1
            if count1 != -2 and count1 != -1:
                if data1['histogram'][count1] < 0 and data1['histogram'][count1 + 1] > 0:
                    if abs(data1['histogram'][count1]) < abs(data1['histogram'][count1 + 1]):
                        crossings[count1] += 1
                    else:
                        crossings[count1 + 1] += 1
                elif data1['histogram'][count1] > 0 and data1['histogram'][count1 + 1] < 0:
                    if abs(data1['histogram'][count1]) < abs(data1['histogram'][count1 + 1]):
                        crossings[count1] += 1
                    else:
                        crossings[count1 + 1] += 1
            elif count1 == -2:
                if data1['histogram'][count1] < 0 and data1['histogram'][count1 + 1] > 0:
                    crossings[count1 + 1] += 1
                elif data1['histogram'][count1] > 0 and data1['histogram'][count1 + 1] < 0:
                    crossings[count1 + 1] += 1

        data1['Crossings'] = crossings.tolist()
        # Earlier Crossings of the macd and macdsignal while both on same side
        EarlierCrossings = 0
        NearestCrossing = 0
        IntervalStart = 0
        t2 = data1.index[-1]
        count3 = -1
        count4 = -1
        for k in reversed(data1['macdsignal'][:-1]):
            count3 += -1
            if k < 0 and data1['macdsignal'][-1] > 0:
                if abs(k) < abs(data1['macdsignal'][count3 + 1]):
                    t1_signal = data1.index[count3]
                else:
                    t1_signal = data1.index[count3 + 1]
                break
            elif k > 0 and data1['macdsignal'][-1] < 0:
                if abs(k) < abs(data1['macdsignal'][count3 + 1]):
                    t1_signal = data1.index[count3]
                else:
                    t1_signal = data1.index[count3 + 1]
                break
            # This is wrong and could be causing problems, should be minus the length of the columns:
            elif count3 == -len(data1.index):
                t1_signal = data1.index[0]
                break
        for l in reversed(data1['macd'][:-1]):
            count4 += -1
            if l < 0 and data1['macdsignal'][-1] > 0:
                if abs(l) < abs(data1['macdsignal'][count4 + 1]):
                    t1_macd = data1.index[count4]
                else:
                    t1_macd = data1.index[count4 + 1]
                break
            elif l > 0 and data1['macdsignal'][-1] < 0:
                if abs(l) < abs(data1['macdsignal'][count4 + 1]):
                    t1_macd = data1.index[count4]
                else:
                    t1_macd = data1.index[count4 + 1]
                break
            elif count4 == -len(data1.index):
                t1_macd = data1['macd'].index[0]
                break
        if t1_macd > t1_signal:
            t1 = t1_macd
        else:
            t1 = t1_signal
        IntervalStart = t1
        count5 = len(data1.index)
        for m in reversed(data1['Crossings']):
            count5 += -1
            if m == 1:
                if t1 < data1.index[count5] < t2:
                    EarlierCrossings += 1
                    if EarlierCrossings == 1:
                        NearestCrossing = data1.index[count5]
            elif m == 2:
                if t1 < data1.index[count5] < t2:
                    EarlierCrossings += 2
                    if EarlierCrossings == 2:
                        NearestCrossing = data1.index[count5]
        CriteriaInfo = [EarlierCrossings, NearestCrossing, IntervalStart]
        if data1['Crossings'][-1] == 0:
            CriteriaInfo = [0, 0, 0]
        if not (CriteriaInfo[0] > 1 and CriteriaInfo[1] != 0 and CriteriaInfo[2] != 0):
            Continue = False

    return data1, CriteriaInfo, Continue


def LocalCharacteristics(data1, CriteriaInfo):
    # Macd increase of decrease, and macd extreme and macd local extreme
    LocalMacdExtremes = [0, 0]
    LocalMacdExtremesLoc = ['N/A', 'N/A']
    macdIncrease = 'N/A'
    count6 = -1
    t1 = CriteriaInfo[2]
    t2 = data1.index[-1]
    for o in data1['macd']:
        count6 += 1
        if (t1 <= data1.index[count6] <= CriteriaInfo[1]) and (abs(o) > abs(LocalMacdExtremes[0])):
            LocalMacdExtremes[0] = o
            LocalMacdExtremesLoc[0] = data1.index[count6]
        if (CriteriaInfo[1] <= data1.index[count6] <= t2) and (abs(o) > abs(LocalMacdExtremes[1])):
            LocalMacdExtremes[1] = o
            LocalMacdExtremesLoc[1] = data1.index[count6]
    if LocalMacdExtremes[0] < LocalMacdExtremes[1]:
        macdIncrease = True
    else:
        macdIncrease = False
    CriteriaInfo.append(macdIncrease)
    CriteriaInfo.append(LocalMacdExtremesLoc[0])
    CriteriaInfo.append(LocalMacdExtremesLoc[1])

    # Price change between local extremes
    count7 = -1
    PriceIncrease = 'N/A'
    if CriteriaInfo[3] != 'N/A':
        PriceActionPrevious = data1.at[CriteriaInfo[4], 'close']
        PriceActionCurrent = data1.at[CriteriaInfo[5], 'close']
        if PriceActionPrevious < PriceActionCurrent:
            PriceIncrease = True
        else:
            PriceIncrease = False
        CriteriaInfo.append(PriceIncrease)
    return CriteriaInfo


# CriteriaInfo = [EarlierCrossings, NearestCrossing, IntervalStart, macdIncrease, LocalMacdExtremesLoc[0], LocalMacdExtremesLoc[1], PriceIncrease]

def TradeSignal(data1, CriteriaInfo, SpreadFactor, Stock):
    Spread = mt5.symbol_info(Stock).ask - mt5.symbol_info(Stock).bid
    Signal = 0
    ClosingPrice = [0, 0]
    if (CriteriaInfo[3] == True) and (CriteriaInfo[6] == False) and (data1['macd'][-1] < 0):
        if data1['macd'][-2] < data1['macdsignal'][-2]:
            # print(f"{Stock}: First criteria met")
            MaxPrice = 0
            MinPrice = math.inf
            count9 = -1
            for s in data1.index:
                count9 += 1
                if (data1['high'][count9] > MaxPrice) and (CriteriaInfo[2] < data1.index[count9] < data1.index[-1]):
                    MaxPrice = data1['high'][count9]
                if (data1['low'][count9] < MinPrice) and (CriteriaInfo[2] < data1.index[count9] < data1.index[-1]):
                    MinPrice = data1['low'][count9]
            DeltaMinPrice = data1['close'][-1] - MinPrice
            StopLoss = data1['close'][-1] - DeltaMinPrice * 1.125
            TradeProfit = data1['close'][-1] + DeltaMinPrice * 2.25
            ClosingPrice = [StopLoss, TradeProfit]
            if DeltaMinPrice * 2.25 > SpreadFactor * Spread:
                Signal = 1
        # else:
        # print('SpreadFactor prevented a trade', Stock)
    elif (CriteriaInfo[3] == False) and (CriteriaInfo[6] == True) and (data1['macd'][-1] > 0):
        if (data1['macd'][-2] > data1['macdsignal'][-2]):
            # print(f"{Stock}: First criteria met")
            MaxPrice = 0
            MinPrice = math.inf
            count10 = -1
            for q in data1.index:
                count10 += 1
                if (data1['high'][count10] > MaxPrice) and (CriteriaInfo[2] < data1.index[count10] < data1.index[-1]):
                    MaxPrice = data1['high'][count10]
                if (data1['low'][count10] < MinPrice) and (CriteriaInfo[2] < data1.index[count10] < data1.index[-1]):
                    MinPrice = data1['low'][count10]
            DeltaMaxPrice = MaxPrice - data1['close'][-1]
            StopLoss = data1['close'][-1] + DeltaMaxPrice * 1.125
            TradeProfit = data1['close'][-1] - DeltaMaxPrice * 2.25
            ClosingPrice = [StopLoss, TradeProfit]
            if DeltaMaxPrice * 2.25 > SpreadFactor * Spread:
                Signal = -1
            # else:
            # print('SpreadFactor prevented a trade', Stock)
    return Signal, ClosingPrice


# Stockname, SpreadFactor
NiceStyle = mpf.make_mpf_style(base_mpf_style='classic', rc={'figure.facecolor': 'lightgray'})
# TestingStocks
Stocks = [["ETHUSD", 3.07], ["LTCUSD", 2.45], ["AUDCHF", 4], ["EURHKD", 3.78], ["EURNZD", 3.4], ["AUDCAD", 4.3],
          ["GBPPLN", 2.5], ["NZDCHF", 4, 20], ["USDCAD", 3.4], ["USDCHF", 3.2], ["USDHUF", 3.1], ["USDMXN", 2.6],
          ["USDTRY", 1.9], ["USDZAR", 2.6]]


### ["LTCUSD",2.45],["ETHUSD",3.07]
##Stocks = [["MSFT",4],["TSLA",2.55],["FB",2.93],["COIN",4.38],["NFLX",5.05],["SHOP",2.25],["EURGBP",4.84],["GBPJPY",4.71],["AUDUSD",3.63],
##          ["EBAY",2.81],["FSLR",2.42],["IWM",2.70],['NKE',3.59],['NVDA',2.84],['PYPL',3.26],['SQ',2.5],['UNH',2.57],["LTCUSD",2.45],["ETHUSD",3.07]]


def ActiveTradesUpdates(LocalTime, Stocks, AccountBalance, IndividualPositions, ActivePositions, TradingHistory,
                        TotalPeriodData1, TotalPeriodData2, counter):
    StockIndex = -1
    for ActivePosition in ActivePositions:
        StockIndex += 1
        # LocalTimeData = pd.DataFrame(mt5.copy_rates_from(Stocks[StockIndex][0], mt5.TIMEFRAME_M5, LocalTime+timedelta(hours=1)-timedelta(seconds=1), 1))
        LocalTimeData1 = TotalPeriodData1[StockIndex]
        LocalTimeData2 = TotalPeriodData2[StockIndex]
        LocalTimeData1 = LocalTimeData1.loc[LocalTimeData1['time'] == LocalTimeData1['time'].iloc[
            (LocalTimeData1['time'] - datetime.timestamp(LocalTime)).abs().argsort()[0]]]
        LocalTimeData2 = LocalTimeData2.loc[LocalTimeData2['time'] == LocalTimeData2['time'].iloc[
            (LocalTimeData2['time'] - datetime.timestamp(LocalTime)).abs().argsort()[0]]]
        # LocalTimeData2 = pd.DataFrame(mt5.copy_ticks_from(Stocks[StockIndex][0],LocalTime+timedelta(hours=1)-timedelta(seconds=1), 1, mt5.COPY_TICKS_ALL))
        Spread = LocalTimeData2.iloc[0]['ask'] - LocalTimeData2.iloc[0]['bid']
        Profit = 0
        # Improve on the buying or selling inbetween intervals
        if ActivePosition[0] == 1 and (
                LocalTimeData1.iloc[0, LocalTimeData1.columns.get_loc('low')] <= ActivePosition[2] or
                LocalTimeData1.iloc[0, LocalTimeData1.columns.get_loc('high')] >= ActivePosition[3]):
            if LocalTimeData1.iloc[0, LocalTimeData1.columns.get_loc('low')] <= ActivePosition[2]:
                Profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, Stocks[StockIndex][0], ActivePosition[4],
                                               ActivePosition[1], ActivePosition[2])
                TradingHistory.append(
                    [str(datetime.fromtimestamp(ActivePosition[5]))[0:19], Stocks[StockIndex][0], ActivePosition[0],
                     ActivePosition[4], ActivePosition[1], ActivePosition[2], ActivePosition[3], str(LocalTime)[0:19],
                     ActivePosition[2], Profit])
            elif (LocalTimeData1.iloc[0, LocalTimeData1.columns.get_loc('low')] + Spread) <= ActivePosition[3]:
                Profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, Stocks[StockIndex][0], ActivePosition[4],
                                               ActivePosition[1], ActivePosition[3])
                TradingHistory.append(
                    [str(datetime.fromtimestamp(ActivePosition[5]))[0:19], Stocks[StockIndex][0], ActivePosition[0],
                     ActivePosition[4], ActivePosition[1], ActivePosition[2], ActivePosition[3], str(LocalTime)[0:19],
                     ActivePosition[3], Profit])
            IndividualPositions[StockIndex] = 0
            ActivePositions[StockIndex] = [0, 0, 0, 0, 0, 0]
        elif ActivePosition[0] == -1 and (
                (LocalTimeData1.iloc[0, LocalTimeData1.columns.get_loc('high')] + Spread) >= ActivePosition[2] or (
                LocalTimeData1.iloc[0, LocalTimeData1.columns.get_loc('low')] + Spread) <= ActivePosition[3]):
            if (LocalTimeData1.iloc[0, LocalTimeData1.columns.get_loc('high')] + Spread) >= ActivePosition[2]:
                Profit = mt5.order_calc_profit(mt5.ORDER_TYPE_SELL, Stocks[StockIndex][0], ActivePosition[4],
                                               ActivePosition[1], ActivePosition[2])
                TradingHistory.append(
                    [str(datetime.fromtimestamp(ActivePosition[5]))[0:19], Stocks[StockIndex][0], ActivePosition[0],
                     ActivePosition[4], ActivePosition[1], ActivePosition[2], ActivePosition[3], str(LocalTime)[0:19],
                     ActivePosition[2], Profit])
            elif (LocalTimeData1.iloc[0, LocalTimeData1.columns.get_loc('low')] + Spread) <= ActivePosition[3]:
                Profit = mt5.order_calc_profit(mt5.ORDER_TYPE_SELL, Stocks[StockIndex][0], ActivePosition[4],
                                               ActivePosition[1], ActivePosition[3])
                TradingHistory.append(
                    [str(datetime.fromtimestamp(ActivePosition[5]))[0:19], Stocks[StockIndex][0], ActivePosition[0],
                     ActivePosition[4], ActivePosition[1], ActivePosition[2], ActivePosition[3], str(LocalTime)[0:19],
                     ActivePosition[3], Profit])
            IndividualPositions[StockIndex] = 0
            ActivePositions[StockIndex] = [0, 0, 0, 0, 0, 0]
        AccountBalance += Profit
    return AccountBalance, IndividualPositions, ActivePositions, TradingHistory


def main():
    IndividualPositions = [0] * len(Stocks)
    EnteringPrices = [0] * len(Stocks)
    ExitingPrices = [0] * len(Stocks)
    ActivePositions = np.zeros((len(Stocks), 6))
    TradingHistory = []
    TotalPeriodData1 = []
    TotalPeriodData2 = []
    AccountBalance = 600
    Investment = 250

    StartTime = datetime(2022, 11, 15, 3, 30)
    DurationHours = 5
    LocalTime = StartTime - timedelta(minutes=5)

    while True:
        if (str(LocalTime)[15:19] != '4:59') and (str(LocalTime)[15:19] != '9:59'):
            LocalTime += -timedelta(seconds=1)
        else:
            break
    for Stock in Stocks:
        TotalPeriodData1.append(pd.DataFrame(mt5.copy_rates_from(Stock[0], mt5.TIMEFRAME_M5,
                                                                 LocalTime + timedelta(minutes=5) + timedelta(
                                                                     hours=DurationHours), DurationHours * 12)))
        TotalPeriodData2.append(pd.DataFrame(mt5.copy_ticks_range(Stock[0], LocalTime + timedelta(minutes=5),
                                                                  LocalTime + timedelta(minutes=5) + timedelta(
                                                                      hours=DurationHours), mt5.COPY_TICKS_ALL)))
    counter = -1
    for TradingLoop in range(DurationHours * 12):
        LocalTime += timedelta(minutes=5)
        counter += 1
        ##    print('\n')
        ##    print(str(LocalTime)[0:19])
        AccountBalance, IndividualPositions, ActivePositions, TradingHistory = ActiveTradesUpdates(LocalTime, Stocks,
                                                                                                   AccountBalance,
                                                                                                   IndividualPositions,
                                                                                                   ActivePositions,
                                                                                                   TradingHistory,
                                                                                                   TotalPeriodData1,
                                                                                                   TotalPeriodData2,
                                                                                                   counter)
        if sum(IndividualPositions) <= 2:
            StockIndex = -1
            for Stock in Stocks:
                AccountBalance, IndividualPositions, ActivePositions, TradingHistory = ActiveTradesUpdates(LocalTime,
                                                                                                           Stocks,
                                                                                                           AccountBalance,
                                                                                                           IndividualPositions,
                                                                                                           ActivePositions,
                                                                                                           TradingHistory,
                                                                                                           TotalPeriodData1,
                                                                                                           TotalPeriodData2,
                                                                                                           counter)
                StockIndex += 1
                if sum(IndividualPositions) <= 1 and IndividualPositions[StockIndex] == 0:
                    data1 = InitialDataFrames(Stock[0], LocalTime)
                    data1, CriteriaInfo, Continue = LocalActions(data1)
                    if (LocalTime - data1.index[-1]) < timedelta(minutes=10):
                        if Continue:
                            CriteriaInfo = LocalCharacteristics(data1, CriteriaInfo)
                            Signal, ClosingPrice = TradeSignal(data1, CriteriaInfo, Stock[1], Stock[0])
                            if (Signal != 0):
                                apds = [mpf.make_addplot(data1['15m_EMA'][250:], color='lime'),
                                        mpf.make_addplot(data1['1h_EMA'][250:], color='c'),
                                        mpf.make_addplot(data1['histogram'][250:], type='bar', width=0.7, panel=1,
                                                         color='dimgray', alpha=1, secondary_y=False),
                                        mpf.make_addplot(data1['macd'][250:], panel=1, color='darkblue',
                                                         secondary_y=True, width=1),
                                        mpf.make_addplot(data1['macdsignal'][250:], panel=1, color='red',
                                                         secondary_y=True, width=1)]
                                Lot = 0
                                MinLot = float(mt5.symbol_info(Stock[0]).volume_min)
                                if Signal == 1:
                                    while True:
                                        if mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, Stock[0], (Lot + MinLot),
                                                                 mt5.symbol_info_tick(Stock[0]).ask) > Investment:
                                            break
                                        Lot += MinLot
                                    if mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, Stock[0], Lot,
                                                             mt5.symbol_info_tick(Stock[0]).ask) > Investment:
                                        Lot = 0
                                        while True:
                                            if mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, Stock[0], (Lot + MinLot),
                                                                     mt5.symbol_info_tick(Stock[0]).ask) > Investment:
                                                break
                                            Lot += MinLot
                                    if Lot != 0:
                                        LocalTimeData = pd.DataFrame(mt5.copy_ticks_from(Stock[0],
                                                                                         LocalTime + timedelta(
                                                                                             hours=1) - timedelta(
                                                                                             seconds=1), 1,
                                                                                         mt5.COPY_TICKS_ALL))
                                        FolderName = f"{Stock[0]}_{str(LocalTime)[:19]}_Buy.png"
                                        FolderName = FolderName.replace(":", "_")
                                        FilePath = pathlib.Path(
                                            "C:/Users/thoma/Desktop/New folder/TradeGraphsHistorical") / FolderName
                                        mpf.plot(data1[250:], type='candle', addplot=apds, figscale=1.1,
                                                 figratio=(8, 5), panel_ratios=(6, 3), style=NiceStyle,
                                                 savefig=FilePath)
                                        IndividualPositions[StockIndex] = 1
                                        ActivePositions[StockIndex, 0] = 1
                                        ActivePositions[StockIndex, 1] = LocalTimeData['ask'][0]
                                        ActivePositions[StockIndex, 2] = ClosingPrice[0]
                                        ActivePositions[StockIndex, 3] = ClosingPrice[1]
                                        ActivePositions[StockIndex, 4] = Lot
                                        ActivePositions[StockIndex, 5] = datetime.timestamp(LocalTime)
                                        # print(str(LocalTime))
                                        # print(data1.to_string(), Stock[0], CriteriaInfo)
                                else:
                                    while True:
                                        if mt5.order_calc_margin(mt5.ORDER_TYPE_SELL, Stock[0], (Lot + MinLot),
                                                                 mt5.symbol_info_tick(Stock[0]).bid) > Investment:
                                            break
                                        Lot += MinLot
                                    if Lot != 0:
                                        LocalTimeData = pd.DataFrame(mt5.copy_ticks_from(Stock[0],
                                                                                         LocalTime + timedelta(
                                                                                             hours=1) - timedelta(
                                                                                             seconds=1), 1,
                                                                                         mt5.COPY_TICKS_ALL))
                                        FolderName = f"{Stock[0]}_{str(LocalTime)[:19]}_Sell.png"
                                        FolderName = FolderName.replace(":", "_")
                                        FilePath = pathlib.Path(
                                            "C:/Users/thoma/Desktop/New folder/TradeGraphsHistorical") / FolderName
                                        mpf.plot(data1[250:], type='candle', addplot=apds, figscale=1.1,
                                                 figratio=(8, 5), panel_ratios=(6, 3), style=NiceStyle,
                                                 savefig=FilePath)
                                        IndividualPositions[StockIndex] = 1
                                        ActivePositions[StockIndex, 0] = -1
                                        ActivePositions[StockIndex, 1] = LocalTimeData['bid'][0]
                                        ActivePositions[StockIndex, 2] = ClosingPrice[0]
                                        ActivePositions[StockIndex, 3] = ClosingPrice[1]
                                        ActivePositions[StockIndex, 4] = Lot
                                        ActivePositions[StockIndex, 5] = datetime.timestamp(LocalTime)
                                        # print(str(LocalTime))
                                        # print(data1.to_string(), Stock[0], CriteriaInfo)
    ##        if sum(IndividualPositions) !=1:
    ##            print(f"there are {sum(IndividualPositions)} trades ongoing")
    ##        else:
    ##            print("there is 1 trade going")
    ##    else:
    ##        print("There are 2 trades ongoing")
    TradingHistory = pd.DataFrame(TradingHistory,
                                  columns=['TimeStart', 'Symbol', 'Type', 'Volume', 'PriceStart', 'S/L', 'T/P',
                                           'TimeEnd', 'PriceEnd', 'Profit'])
    print(TradingHistory.to_string())


main()
