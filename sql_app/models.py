import datetime

from sqlalchemy import Column, Integer, String, DateTime

from .database import Base


class EncryptedTable(Base):
    __tablename__ = 'encrypted_table'

    id = Column(Integer, primary_key=True, index=True)
    encrypted_text = Column(String)
    decrypted_text = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return (f'{self.id} - {self.encrypted_text} - {self.decrypted_text} - '
                f'{self.created_at}')
