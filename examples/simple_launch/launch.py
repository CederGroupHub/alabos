import requests
import time

exp = {
    "samples": [{"name": "test_sample"}],
    "tasks": [{
        "type": "Pouring",
        "next_tasks": [1],
        "parameters": {},
        "samples": {
            "sample": "test_sample"
        }
    }, {
        "type": "Weighing",
        "next_tasks": [2],
        "parameters": {},
        "samples": {
            "sample": "test_sample"
        }
    }, {
        "type": "Heating",
        "next_tasks": [],
        "parameters": {
            "heating_time": 0.5,
            "heating_temperature": 300.0
        },
        "samples": {
            "sample": "test_sample"
        }
    }],
}


url = "http://127.0.0.1:8895/api/experiment/submit"

for i in range(1):
    exp_ = exp.copy()
    exp_["name"] = f"Heating baking soda"
    print(requests.post(url, json=exp_).json())
    time.sleep(1)
