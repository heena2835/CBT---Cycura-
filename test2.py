import asyncio
from fastapi import UploadFile
from backend import api

async def main():
    print("Writing empty file...")
    with open("empty_test.csv", "w") as f:
        f.write("timestamp,cbt\n2022-01-01 00:00,36.5\n")
        
    print("Testing api.analyze_data")
    with open("empty_test.csv", "rb") as f:
        uf = UploadFile(filename="empty_test.csv", file=f)
        resp = await api.analyze_data(file=uf, age=30, name="T", gender="F")
        print("Success! Resp keys:", resp.keys())
        print("Outputs:", resp['outputs'])

if __name__ == "__main__":
    asyncio.run(main())
