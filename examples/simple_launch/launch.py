import requests

exp = {
    "name": "Firing baking soda",
    "samples": [{
        "name": "baking_soda"
    }],
    "tasks": [{
        "type": "Starting",
        "next_tasks": [1],
        "parameters": {
            "start_position": "furnace_table",
        },
        "samples": {
            "sample": "baking_soda"
        }
    }, {
        "type": "Pouring",
        "next_tasks": [2],
        "parameters": {},
        "samples": {
            "sample": "baking_soda"
        }
    }, {
        "type": "Weighing",
        "next_tasks": [3],
        "parameters": {},
        "samples": {
            "sample": "baking_soda"
        }
    }, {
        "type": "Heating",
        "next_tasks": [4],
        "parameters": {
            "heating_time": 0.5,
            "heating_temperature": 300.0,
        },
        "samples": {
            "sample": "baking_soda"
        }
    }, {
        "type": "Ending",
        "next_tasks": [5],
        "parameters": {},
        "samples": {
            "sample": "baking_soda"
        }
    }],
}

url = "http://127.0.0.1:8895/api/experiment/submit"

print(requests.post(url, json=exp).json())
