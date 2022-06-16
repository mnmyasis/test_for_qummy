import json
import os
from typing import Union, List, Dict
import requests

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from dotenv import load_dotenv

from sql_app.database import SessionLocal
from sql_app import crud
from sql_app import models
from sql_app import schema

load_dotenv()

app = FastAPI()

DOWNLOAD_ENCRYPTED_DATA_URL = 'http://yarlikvid.ru:9999/api/top-secret-data'
DECRYPTED_DATA_URL = 'http://yarlikvid.ru:9999/api/decrypt'
RESULT_API_URL = 'http://yarlikvid.ru:9999/api/result'

USERNAME = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_encrypted_datas(query: Session) -> List[str]:
    encrypted_datas = []
    for data in query:
        encrypted_datas.append(data.encrypted_text)
    return encrypted_datas


def request_in_decrypted_service(data: Union[List, Dict],
                                 url: str) -> Union[List, Dict]:
    data = json.dumps(data)
    session = requests.Session()
    session.auth = (USERNAME, PASSWORD)
    response = session.post(url, data=data)
    if response.status_code != status.HTTP_200_OK:
        response.raise_for_status()
    decrypted_datas = response.json()
    return decrypted_datas


def write_decrypted_text_in_db(db: Session,
                               query: Session,
                               decrypted_datas: List[str]) -> None:
    for data, decrypted_data in zip(query, decrypted_datas):
        data.decrypted_text = decrypted_data
    db.commit()


@app.get("/encrypted-texts", status_code=status.HTTP_201_CREATED,
         response_model=schema.EncryptedTable)
async def encrypted_texts(db: Session = Depends(get_db)):
    response = requests.get(DOWNLOAD_ENCRYPTED_DATA_URL)
    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error request api service",
            headers={"WWW-Authenticate": "Bearer"},
        )
    encrypted_datas = response.json()
    crud.create_encrypted_data(db=db, encrypted_datas=encrypted_datas)
    return encrypted_datas


@app.post("/decrypted-texts", status_code=status.HTTP_201_CREATED,
          response_model=schema.EncryptedTable)
async def decrypted_texts(db: Session = Depends(get_db)):
    query = db.query(models.EncryptedTable).order_by('id')
    encrypted_datas = get_encrypted_datas(query)
    decrypted_datas = request_in_decrypted_service(encrypted_datas,
                                                   DECRYPTED_DATA_URL)
    write_decrypted_text_in_db(db, query, decrypted_datas)
    return decrypted_datas


@app.post("/decrypted-result",
          response_description='Response from the server API')
async def decrypted_result(db: Session = Depends(get_db)):
    datas = []
    for raw in db.query(models.EncryptedTable):
        datas.append(raw.decrypted_text)
    data = {
        'name': 'Мясищев Максим',
        'repo_url': 'https://github.com/mnmyasis/test_for_qummy',
        'result': datas
    }
    response = request_in_decrypted_service(
        data,
        RESULT_API_URL
    )
    return response
