from typing import List

from sqlalchemy.orm import Session

from .models import EncryptedTable


def create_encrypted_data(db: Session, encrypted_datas: List):
    datas = [EncryptedTable(encrypted_text=data) for data in encrypted_datas]
    db.add_all(datas)
    db.commit()
    return datas
