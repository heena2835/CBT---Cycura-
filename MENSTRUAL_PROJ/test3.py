import traceback
from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)

print("Starting test...")
try:
    with open("empty.csv", "w") as f:
        f.write("timestamp,cbt\n2022-01-01 00:00,36.5\n")
            
    with open("empty.csv", "rb") as f:
        response = client.post("/analyze", files={"file": ("empty.csv", f, "text/csv")}, data={"age": "30", "name": "Test", "gender": "Female"})
        
    print("Status:", response.status_code)
    try:
        print("Response:", response.json())
    except:
        print("Response:", response.text)
except Exception as e:
    traceback.print_exc()
