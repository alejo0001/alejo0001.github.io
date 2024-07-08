from datetime import datetime, timedelta
import math
from time import sleep
import time
from fastapi import FastAPI
import pandas as pd
from pydantic import BaseModel
from typing import Optional
from AI_Analyzer_test import Analyze
from price_action_strategy import getMarketZones
from indicators import calculate_bollinger_bands, calculate_rsi
from common import AnalyzeResponse, BybitKlinesResponse, PriceActionCalibrationDto, PriceGroup,SendTelegramMessage,BybitTickersResponse,BybitTickersResultTicker
from typing import List
from getTickers import getBybitTickers
from Klines import getBybitKlines
import asyncio
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
origins = [
    "http://localhost:4200"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
AnalysisList:List[AnalyzeResponse]=[]
lstExceptionTickers = ['ETHUSDT', 'BTCUSDT', 'ADAUSDT','XRPUSDT','MATICUSDT','THETAUSDT','ALGOUSDT','TRXUSDT','DOGEUSDT']
minFundingRate= 0.05
#ejemplo validación de datos con baseModel:
class Libro(BaseModel):
    titulo:str
    autor:str
    paginas:int
    editorial:Optional[str]

#http://127.0.0.1:8000/
@app.get("/")
def index():
    return {"message":"Prueba FastAPI"}

@app.get("/{id}")
def pruebaId(id:int):
    return {"id":id}

@app.post("/libros")
def insertar_libro(libro:Libro):
    return{"message": f"libro {libro.titulo} insertado"}

# @app.on_event("startup")
# async def startup_event():
#     asyncio.create_task(realTimeExecutor()) 

@app.post("/priceActionCalibration", response_model=List[PriceGroup])
def priceActionCalibration(calibration:PriceActionCalibrationDto):
    return getMarketZones(calibration.temporality,calibration.rangeDivisor,calibration.precision,calibration.minBouncesAmount)

print ('server en funcionamiento')
async def AIAnalysis():
    counter : int = 0
    
    while True:
        if(counter == 0):
            counter = 1
            AnalysisList = Analyze()
            messages : str =''
            for item in AnalysisList:
                if(item.score is not None and abs(int(item.score)) >= 1):
                    messages+=f'''noticia: {item.newsItemLink}
análisis: {item.analysis}
puntaje: {item.score}
fecha: {item.newsItemDate}
pares: {str(item.pairs)}
'''
                # print('análisis: '+str(item.analysis))
            print(messages)
            if(messages):
                await SendTelegramMessage(messages)
            
        await asyncio.sleep(540)
        counter = 0

def bybitOperablePairs():
    bybitTickers : BybitTickersResponse
    filteredBybitTickers : List[BybitTickersResultTicker]=[]
    bybitTickers = getBybitTickers()
    for ticker in bybitTickers.result.list:
        if(ticker.funding_rate != ''):
            if(float(ticker.volume24_h) >= 1000000000 and ticker.symbol not in lstExceptionTickers and abs(float(ticker.funding_rate)) < minFundingRate):
                filteredBybitTickers.append(ticker)
                # print(ticker.symbol)
                # print(ticker.volume24_h)
                # print(ticker.funding_rate)
                # print('')
    return filteredBybitTickers

def bollingerBandsAndRSIStrategy(temporality: str ='15m'):
    pairs : List[BybitTickersResultTicker]=bybitOperablePairs()
    closePrices : List[float] = []
    tickerKlines : BybitKlinesResponse
    messages : str =''
    closePricesDates : List[str] = []
    for ticker in pairs:
        closePrices = []
        tickerKlines = getBybitKlines(ticker.symbol,20,int(temporality.split('m')[0]))
        epoch = datetime(1970, 1, 1)
        for kline in tickerKlines.result.list:
            closePrices.append(float(kline.closePrice))
            closePricesDates.append(str(epoch +timedelta(seconds=int(kline.startTime)/1000)))

        closePrices.reverse()
        closePricesDates.reverse()
        print(ticker.symbol+': '+str(str(closePrices[0])+' '+closePricesDates[0]+' '+str(closePrices[-1])+' '+closePricesDates[-1]))
        prices = pd.Series(closePrices)
        rsi = calculate_rsi(prices)

        if(rsi[0]  >30 and rsi[0] <70 | math.isnan(rsi[0])):
            continue
        rolling_mean, upper_band, lower_band = calculate_bollinger_bands(prices)

            
            
        if(((closePrices[-1]> upper_band[len(upper_band)-1] ) & (rsi[0] >=70)) | ((closePrices[-1]< lower_band[len(lower_band)-1] ) & (rsi[0] <=30))):
        
            #coinsCollection.append([coin,str(upper_band[len(upper_band)-1]),str(lower_band[len(lower_band)-1]),str(rsi[0]),str(latest_prices[-1])])
            
            messages+=f'''posible patrón poderoso {ticker.symbol}:
rsi: {rsi[0]}
banda {'superior' if rsi[0]>=70 else 'inferior'}: {upper_band[len(upper_band)-1] if rsi[0]>=70 else lower_band[len(lower_band)-1]}
precio de cierre: {closePrices[-1]}
volumne24h: {ticker.volume24_h}
funding rate: {ticker.funding_rate}
next funding time: {epoch +timedelta(seconds=int(ticker.next_funding_time)/1000)}
'''     
        else:
            print('sin patrón '+ticker.symbol+': rsi= '+str(rsi[0]))
    
    return messages

async def realTimeExecutor():
    temporality = '1m'
    lastMinuteExecuted = None
    maxMinutesInterval = 60
    executingMinutes : List[int]=[]
    counter = 0
    messages : str = ''

    while counter <= maxMinutesInterval:
        counter += int(temporality.split('m')[0])
        if(counter == maxMinutesInterval):
            executingMinutes.append(0)
        else:            
            executingMinutes.append(counter)

    while True:
        now = datetime.now()
        currentMinute = now.minute

        if(currentMinute in executingMinutes and currentMinute != lastMinuteExecuted):
            lastMinuteExecuted = currentMinute
            
            messages = bollingerBandsAndRSIStrategy(temporality)
            if(messages != ''):
                await SendTelegramMessage(f'''alertas {temporality}: 
{messages}
''')

        time.sleep(1)



        



#bybitOperablePairs()
# if __name__ == "__main__":
#     asyncio.run(AIAnalysis())

#print('análisis: '+str(item.analysis))

#da60d6cb5ee743b3aa090e1121ad2247 API KEY GOOGLE NEWS


