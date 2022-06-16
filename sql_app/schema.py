from pydantic import BaseModel


class EncryptedTable(BaseModel):
    encrypted_text: str
    decrypted_text: str
