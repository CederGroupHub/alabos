
// General

const URL = "http://localhost:8895";
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

const DEVICE_API = process.env.NODE_ENV === "production" ? "/api/device/" : URL + "/api/device/";

export async function get_device(device_name) {
    try {
        const res = await fetch(DEVICE_API + encodeURIComponent(device_name), { mode: 'cors' });
        const result_1 = await res.json();
        return result_1.data;
    } catch (error) {
        return console.warn(error);
    }
}

// Omit signal_names to get only the latest value of every signal the device has logged.
export async function get_device_signals(device_name, signal_names, hours) {
    try {
        const params = new URLSearchParams();
        (signal_names || []).forEach(name => params.append("signal", name));
        if (hours) {
            params.append("hours", hours);
        }
        const query = params.toString();
        const res = await fetch(
            DEVICE_API + encodeURIComponent(device_name) + "/signals" + (query ? "?" + query : ""),
            { mode: 'cors' }
        );
        const result_1 = await res.json();
        return result_1.data;
    } catch (error) {
        return console.warn(error);
    }
}

// Sample Positions
const SAMPLE_POSITIONS_API = process.env.NODE_ENV === "production" ? "/api/sample-positions" : URL + "/api/sample-positions";

export async function get_sample_position_racks() {
    try {
        const res = await fetch(SAMPLE_POSITIONS_API + "/racks", { mode: 'cors' });
        return await res.json();
    } catch (error) {
        return console.warn(error);
    }
}

export function place_sample_in_position(position, { sample_id = null, sample_name = "" } = {}) {
    return fetch(SAMPLE_POSITIONS_API + "/place", {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            position,
            sample_id,
            sample_name,
        }),
    });
}

export function clear_sample_position(position) {
    return fetch(SAMPLE_POSITIONS_API + "/clear", {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            position,
        }),
    });
}

// Data exports
const DATA_API = process.env.NODE_ENV === "production" ? "/api/data" : URL + "/api/data";

export async function get_sample_summary_rows() {
    try {
        const res = await fetch(DATA_API + "/sample_summary", { mode: 'cors' });
        return await res.json();
    } catch (error) {
        return console.warn(error);
    }
}

export async function get_powder_dosing_rows() {
    try {
        const res = await fetch(DATA_API + "/powder_dosing_actuals", { mode: 'cors' });
        return await res.json();
    } catch (error) {
        return console.warn(error);
    }
}

export async function get_task_outcome_rows() {
    try {
        const res = await fetch(DATA_API + "/task_outcome_log", { mode: 'cors' });
        return await res.json();
    } catch (error) {
        return console.warn(error);
    }
}

export const DATA_DOWNLOADS = {
    sampleSummary: DATA_API + "/sample_summary.csv",
    powderDosing: DATA_API + "/powder_dosing_actuals.csv",
    taskOutcome: DATA_API + "/task_outcome_log.csv",
};

// Device control
const DEVICE_CONTROL_API = process.env.NODE_ENV === "production" ? "/api/device-control" : URL + "/api/device-control";

export async function get_device_control_catalog() {
    const res = await fetch(DEVICE_CONTROL_API + "/catalog", { mode: 'cors' });
    return await res.json();
}

export async function claim_device_control(device_name) {
    const res = await fetch(DEVICE_CONTROL_API + "/claim", {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ device_name }),
    });
    return await res.json();
}

export async function release_device_control(device_name, manual_task_id) {
    const res = await fetch(DEVICE_CONTROL_API + "/release", {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ device_name, manual_task_id }),
    });
    return await res.json();
}

export async function execute_device_control_command(device_name, command_name, manual_task_id = null, params = {}) {
    const res = await fetch(DEVICE_CONTROL_API + "/command", {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ device_name, command_name, manual_task_id, params }),
    });
    return await res.json();
}
