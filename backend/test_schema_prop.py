import requests

payload = {
    "trigger_reason": "Librarian agent detected a consistent pattern of User Location metadata across documents, proposing a new UserLocation tracking model.",
    "proposed_code": '''class UserLocation(BaseModel):
    __tablename__ = "user_locations"
    __table_args__ = {"extend_existing": True}

    user_id = Column(String(255), nullable=False, index=True)
    city = Column(String(255), nullable=True)
    country = Column(String(255), nullable=True)
    trust_score = Column(Float, default=0.5)
'''
}

try:
    res = requests.post("http://127.0.0.1:8000/api/schema-evolution/proposals", json=payload)
    print(res.status_code, res.text)
except Exception as e:
    print("Error:", str(e))
