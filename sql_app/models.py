import datetime

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, )
    is_active = Column(Boolean, default=True)
    token = relationship('Token', back_populates='user', uselist=False)


class Token(Base):
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(String)
    token_type = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User', back_populates='token')


class EncryptedTable(Base):
    __tablename__ = 'encrypted_table'

    id = Column(Integer, primary_key=True, index=True)
    encrypted_text = Column(String)
    decrypted_text = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return (f'{self.id} - {self.encrypted_text} - {self.decrypted_text} - '
                f'{self.created_at}')
