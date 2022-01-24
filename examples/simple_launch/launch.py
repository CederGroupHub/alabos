import requests

exp = {
    "name": "Firing baking soda",
    "samples": [{
        "name": "baking_soda"
    }],
    "tasks": [{
        "type": "Starting",
        "prev_tasks": [],
        "parameters": {
            "start_position": "furnace_table",
        },
        "samples": {
            "sample": "baking_soda"
        }
    }, {
        "type": "Pouring",
        "prev_tasks": [0],
        "parameters": {},
        "samples": {
            "sample": "baking_soda"
        }
    }, {
        "type": "Weighing",
        "prev_tasks": [1],
        "parameters": {},
        "samples": {
            "sample": "baking_soda"
        }
    }, {
        "type": "Heating",
        "prev_tasks": [2],
        "parameters": {
            "heating_time": 0.5,
            "heating_temperature": 300.0,
        },
        "samples": {
            "sample": "baking_soda"
        }
    }, {
        "type": "Ending",
        "prev_tasks": [3],
        "parameters": {},
        "samples": {
            "sample": "baking_soda"
        }
    }],
}

url = "http://127.0.0.1:8895/api/experiment/submit"

print(requests.post(url, json=exp).json())
