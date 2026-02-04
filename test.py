import requests
try:
    response = requests.get(" https://157.48.185.203", timeout=5)
    print(f"Odoo server is reachable. Status: {response.status_code}")
except Exception as e:
    print(f"Cannot reach Odoo server: {e}")