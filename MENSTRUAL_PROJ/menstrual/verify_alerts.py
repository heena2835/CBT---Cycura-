import urllib.request
import urllib.parse
import json
import os
import mimetypes

# Minimal multipart/form-data encoder for urllib
def encode_multipart_formdata(fields, files):
    boundary = '----------Boundary_123456789'
    lines = []
    for (key, value) in fields.items():
        lines.append('--' + boundary)
        lines.append('Content-Disposition: form-data; name="%s"' % key)
        lines.append('')
        lines.append(str(value))
    for (key, filename) in files.items():
        lines.append('--' + boundary)
        lines.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        lines.append('Content-Type: %s' % (mimetypes.guess_type(filename)[0] or 'application/octet-stream'))
        lines.append('')
        with open(filename, 'rb') as f:
            lines.append(f.read().decode('latin1')) # simple decoding for this test
    lines.append('--' + boundary + '--')
    lines.append('')
    body = '\r\n'.join(lines).encode('latin1')
    content_type = 'multipart/form-data; boundary=%s' % boundary
    return content_type, body

def test_analyze(filename):
    url = "http://127.0.0.1:8000/analyze"
    print(f"Testing {filename}...")
    
    try:
        content_type, body = encode_multipart_formdata({'age': 30}, {'file': filename})
        req = urllib.request.Request(url, data=body, headers={'Content-Type': content_type})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                resp_body = response.read().decode('utf-8')
                json_resp = json.loads(resp_body)
                alerts = json_resp.get("outputs", {}).get("Alerts", {})
                print("Alerts:", json.dumps(alerts, indent=2))
                return alerts
            else:
                print("Error:", response.read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to connect: {e}")

def confirm_period(date_str):
    url = "http://127.0.0.1:8000/confirm-period"
    print(f"Confirming period for {date_str}...")
    try:
        data = urllib.parse.urlencode({'date': date_str}).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as response:
            print("Response:", response.read().decode('utf-8'))
    except Exception as e:
         # urllib raises error on 4xx/5xx
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    csv_file = "healthy dataset 2(dip).csv"
    if os.path.exists(csv_file):
        test_analyze(csv_file)
    
    confirm_period("2025-12-30")
    
    if os.path.exists(csv_file):
        print("Re-testing after confirmation (if date matches logic)...")
        test_analyze(csv_file)
