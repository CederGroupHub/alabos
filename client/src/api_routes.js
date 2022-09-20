
// General

const URL = "http://localhost:8896";
const STATUS_API = process.env.NODE_ENV === "production" ? "/api/status" : URL + "/api/status";
console.log(STATUS_API);
export async function get_status() {
    try {
        const res = await fetch(STATUS_API, { mode: 'cors' });
        const result_1 = await res.json();
        return result_1;
    } catch (error) {
        return console.warn(error);
    }
}

// UserInputs
const RESPOND_USERREQUEST_API = process.env.NODE_ENV === "production" ? "/api/userinput/submit" : URL + "/api/userinput/submit";
const PENDINGIDS_USERREQUEST_API = process.env.NODE_ENV === "production" ? "/api/userinput/pending" : URL + "/api/userinput/pending";
const SPECIFIC_USERREQUEST_PREFIX = process.env.NODE_ENV === "production" ? "/api/userinput/" : URL + "/api/userinput/";

export async function get_pending_userinputrequests() {
    try {
        const res = await fetch(PENDINGIDS_USERREQUEST_API, { mode: 'cors' });
        const result_1 = await res.json();
        var return_values = Object();
        return_values["pending"] = result_1.pending_requests;
        return_values["experiment_id_to_name"] = result_1.experiment_id_to_name;
        return return_values;
    } catch (error) {
        return console.warn(error);
    }
}

export function respond_to_userinputrequest(request_id, response, note) {
    return fetch(RESPOND_USERREQUEST_API, {
        method: 'POST',
        mode: 'cors',
        body: JSON.stringify({
            "request_id": request_id,
            "response": response,
            "note": note
        })
    });
}

// Experiments
const ALL_EXPERIMENT_IDS_API = process.env.NODE_ENV === "production" ? "/api/experiment/get_all_ids" : URL + "/api/experiment/get_all_ids";

const SPECIFIC_EXPERIMENT_API = process.env.NODE_ENV === "production" ? "/api/experiment/" : URL + "/api/experiment/";

export async function get_experiment_ids() {
    try {
        const res = await fetch(ALL_EXPERIMENT_IDS_API, { mode: 'cors' });
        const result_1 = await res.json();
        return result_1.experiment_ids;
    } catch (error) {
        return console.warn(error);
    }
}


export async function get_experiment_status(experiment_id) {
    try {
        const res = await fetch(SPECIFIC_EXPERIMENT_API + experiment_id, { mode: 'cors' });
        const result_1 = await res.json();
        return result_1;
    } catch (error) {
        return console.warn(error);
    }
}

// Devices

const PAUSE_DEVICE_API = process.env.NODE_ENV === "production" ? "/api/pause/" : URL + "/api/pause/";

export function request_device_pause(device_name) {
    return fetch(PAUSE_DEVICE_API + "request", {
        method: 'POST',
        mode: 'cors',
        body: JSON.stringify({
            "device_name": device_name
        })
    });
}

export function release_device_pause(device_name) {
    return fetch(PAUSE_DEVICE_API + "release", {
        method: 'POST',
        mode: 'cors',
        body: JSON.stringify({
            "device_name": device_name
        })
    });
}