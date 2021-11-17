import requests
import time

exp = {
    "samples": [{"name": "test_sample"}],
    "tasks": [{
        "type": "Starting",
        "next_tasks": [1],
        "parameters": {
            "dest": "furnace_table"
        },
        "samples": {
            "sample": "test_sample"
        }
    }, {
        "type": "Heating",
        "next_tasks": [2],
        "parameters": {
            "setpoints": [(10, 100)]
        },
        "samples": {
            "sample": "test_sample"
        }
    }, {
        "type": "Ending",
        "next_tasks": [],
        "parameters": {},
        "samples": {
            "sample": "test_sample"
        }
    }],
}

url = "http://127.0.0.1:8895/api/experiment/submit"

for i in range(10):
    exp_ = exp.copy()
    exp_["name"] = f"Heating @ {i * 100 + 400}°C"
    print(requests.post(url, json=exp_).json())
    time.sleep(1)
