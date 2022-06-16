import json
import os
from datetime import timedelta, datetime
from typing import Union, List, Dict
import requests

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette import status
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv

from sql_app.database import SessionLocal
from sql_app import crud
from sql_app import models
from sql_app.schema import User, UserInDB, TokenData, Token

load_dotenv()

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

DOWNLOAD_ENCRYPTED_DATA_URL = 'http://yarlikvid.ru:9999/api/top-secret-data'
DECRYPTED_DATA_URL = 'http://yarlikvid.ru:9999/api/decrypt'
RESULT_API_URL = 'http://yarlikvid.ru:9999/api/result'

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = 30

USERNAME = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')

fake_users_db = {
    "admin": {
        "email": "admin",
        "hashed_password": "$2b$12$Fs2rfdMJSkNIAh/YEgkLC.dw4AQHP3G7avFxOfyIvvWfNdnmWoMCG",
        "is_active": True,
    },
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict,
                        expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


@app.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username,
                             form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}


@app.get("/encrypted-texts", status_code=status.HTTP_201_CREATED)
async def encrypted_texts(db: Session = Depends(get_db),
                          token: str = Depends(oauth2_scheme)):
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


def get_encrypted_datas(db: Session,
                        query: Session) -> List[str]:
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


@app.post("/decrypted-texts", status_code=status.HTTP_201_CREATED)
async def decrypted_texts(db: Session = Depends(get_db),
                          token: str = Depends(oauth2_scheme)):
    query = db.query(models.EncryptedTable).order_by('id')
    encrypted_datas = get_encrypted_datas(db, query)
    decrypted_datas = request_in_decrypted_service(encrypted_datas,
                                                   DECRYPTED_DATA_URL)
    write_decrypted_text_in_db(db, query, decrypted_datas)
    return decrypted_datas


@app.post("/decrypted-result")
async def decrypted_result(db: Session = Depends(get_db)):
    datas = []
    for raw in db.query(models.EncryptedTable):
        datas.append(raw.decrypted_text)
    data = {
        'name': 'Мясищев Максим',
        'repo_url': 'https://github.com/mnmyasis/test_for_qummy',
        'result': datas
    }
    request_in_decrypted_service(
        data,
        RESULT_API_URL
    )
    return data
