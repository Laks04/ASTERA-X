from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
app=FastAPI(title='ASTERA API',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_credentials=True,allow_methods=['GET'],allow_headers=['*'])
DATA=Path(__file__).resolve().parents[2]/'packages'/'shared'/'missions.json'
@app.get('/api/v1/health')
def health():return {'status':'ok','app':'ASTERA'}
@app.get('/api/v1/missions')
def missions():return json.loads(DATA.read_text())
@app.get('/api/v1/missions/{mission_id}')
def mission(mission_id:str):
 from fastapi import HTTPException
 match=next((m for m in missions() if m['id']==mission_id),None)
 if match is None:raise HTTPException(status_code=404,detail='Mission not found')
 return match
