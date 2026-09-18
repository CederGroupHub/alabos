
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

const RESET_LAB_API = process.env.NODE_ENV === "production" ? "/api/experiment/reset_lab" : URL + "/api/experiment/reset_lab";

export async function reset_lab() {
    const res = await fetch(RESET_LAB_API, {
        method: "POST",
        mode: "cors",
    });
    return res.json();
}

const LAB_SETTINGS_API = process.env.NODE_ENV === "production" ? "/api/lab-settings" : URL + "/api/lab-settings";
const CONTROL_API_BASE = process.env.NODE_ENV === "production"
  ? "http://127.0.0.1:8894/api/control"
  : "http://127.0.0.1:8894/api/control";

export async function get_lab_idle() {
    const res = await fetch(LAB_SETTINGS_API + "/idle", { mode: "cors" });
    return res.json();
}

export async function clear_lab_occupancy() {
    const res = await fetch(LAB_SETTINGS_API + "/clear_occupancy", {
        method: "POST",
        mode: "cors",
    });
    return res.json();
}

export async function control_status() {
    const res = await fetch(CONTROL_API_BASE + "/status", { mode: "cors" });
    return res.json();
}

export async function control_backup() {
    const res = await fetch(CONTROL_API_BASE + "/backup", {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: "{}",
    });
    return res.json().then((data) => ({ ok: res.ok, status: res.status, data }));
}

export async function control_refresh_definitions() {
    const res = await fetch(CONTROL_API_BASE + "/refresh-definitions", {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: "{}",
    });
    return res.json().then((data) => ({ ok: res.ok, status: res.status, data }));
}

export async function control_nuclear(confirmDropDatabase) {
    const res = await fetch(CONTROL_API_BASE + "/nuclear", {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm_drop_database: confirmDropDatabase }),
    });
    return res.json().then((data) => ({ ok: res.ok, status: res.status, data }));
}

export async function get_control_config() {
    const res = await fetch(CONTROL_API_BASE + "/config", { mode: "cors" });
    return res.json().then((data) => ({ ok: res.ok, status: res.status, data }));
}

export async function put_control_config(payload) {
    const res = await fetch(CONTROL_API_BASE + "/config", {
        method: "PUT",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    return res.json().then((data) => ({ ok: res.ok, status: res.status, data }));
}

export async function apply_control_profile(profileId) {
    const res = await fetch(CONTROL_API_BASE + "/profile/" + profileId, {
        method: "POST",
        mode: "cors",
        headers: { "Content-Type": "application/json" },
        body: "{}",
    });
    return res.json().then((data) => ({ ok: res.ok, status: res.status, data }));
}

const CANCEL_EXPERIMENT_API = process.env.NODE_ENV === "production" ? "/api/experiment/cancel/" : URL + "/api/experiment/cancel/";
const CANCEL_TASK_API = process.env.NODE_ENV === "production" ? "/api/task/cancel/" : URL + "/api/task/cancel/";

export async function cancel_experiment(experiment_id) {
    const res = await fetch(CANCEL_EXPERIMENT_API + experiment_id, {
        method: "GET",
        mode: "cors",
    });
    return res.json();
}

export async function cancel_task(task_id) {
    const res = await fetch(CANCEL_TASK_API + task_id, {
        method: "GET",
        mode: "cors",
    });
    return res.json();
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

export async function get_device_verbose_log(device_name, lines) {
    try {
        const params = new URLSearchParams();
        if (lines) {
            params.append("lines", lines);
        }
        const query = params.toString();
        const res = await fetch(
            DEVICE_API + encodeURIComponent(device_name) + "/verbose-log" + (query ? "?" + query : ""),
            { mode: 'cors' }
        );
        const result_1 = await res.json();
        return result_1.data;
    } catch (error) {
        return console.warn(error);
    }
}

const LOGS_API = process.env.NODE_ENV === "production" ? "/api/logs" : URL + "/api/logs";

export async function get_launch_log_sources() {
    try {
        const res = await fetch(LOGS_API + "/sources", { mode: "cors" });
        const result = await res.json();
        return result.data;
    } catch (error) {
        return console.warn(error);
    }
}

export async function get_launch_log_tail(source_id, lines) {
    try {
        const params = new URLSearchParams();
        if (lines) {
            params.append("lines", lines);
        }
        const query = params.toString();
        const res = await fetch(
            LOGS_API + "/tail/" + encodeURIComponent(source_id) + (query ? "?" + query : ""),
            { mode: "cors" }
        );
        const result = await res.json();
        return result.data;
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

function dataMonthQuery(month) {
    return month ? `?month=${encodeURIComponent(month)}` : "";
}

export async function get_data_window(month = null) {
    try {
        const res = await fetch(DATA_API + "/window" + dataMonthQuery(month), { mode: 'cors' });
        return await res.json();
    } catch (error) {
        return console.warn(error);
    }
}

export async function get_sample_summary_rows(month = null) {
    try {
        const res = await fetch(DATA_API + "/sample_summary" + dataMonthQuery(month), { mode: 'cors' });
        return await res.json();
    } catch (error) {
        return console.warn(error);
    }
}

export async function get_powder_dosing_rows(month = null) {
    try {
        const res = await fetch(DATA_API + "/powder_dosing_actuals" + dataMonthQuery(month), { mode: 'cors' });
        return await res.json();
    } catch (error) {
        return console.warn(error);
    }
}

export async function get_task_outcome_rows(month = null) {
    try {
        const res = await fetch(DATA_API + "/task_outcome_log" + dataMonthQuery(month), { mode: 'cors' });
        return await res.json();
    } catch (error) {
        return console.warn(error);
    }
}

export function dataDownloadHref(endpoint, month = null) {
    return DATA_API + endpoint + dataMonthQuery(month);
}

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

// Mobile robot segment control
const ROBOT_CONTROL_API = process.env.NODE_ENV === "production" ? "/api/robot-control/mobile" : URL + "/api/robot-control/mobile";

export async function get_mobile_robot_catalog() {
    const res = await fetch(ROBOT_CONTROL_API + "/catalog", { mode: 'cors' });
    return await res.json();
}

export async function preview_mobile_robot_segment(segment_id, body) {
    const res = await fetch(ROBOT_CONTROL_API + "/preview/" + segment_id, {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    return await res.json();
}

export async function run_mobile_robot_segment(segment_id, body) {
    const res = await fetch(ROBOT_CONTROL_API + "/run/" + segment_id, {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    return await res.json();
}

// Prometheus BFT → DASH control
const BFT_CONTROL_API = process.env.NODE_ENV === "production" ? "/api/bft-control" : URL + "/api/bft-control";

// DASH workflow segment control
const DASH_CONTROL_API = process.env.NODE_ENV === "production" ? "/api/dash-control" : URL + "/api/dash-control";

export async function get_dash_control_catalog() {
    const res = await fetch(DASH_CONTROL_API + "/catalog", { mode: 'cors' });
    return await res.json();
}

export async function preview_dash_segment(segment_id, body) {
    const res = await fetch(DASH_CONTROL_API + "/preview/" + segment_id, {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    return await res.json();
}

export async function get_bft_control_catalog() {
    const res = await fetch(BFT_CONTROL_API + "/catalog", { mode: 'cors' });
    return await res.json();
}

export async function preview_bft_segment(segment_id, body) {
    const res = await fetch(BFT_CONTROL_API + "/preview/" + segment_id, {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    return await res.json();
}

export async function run_bft_segment(segment_id, body) {
    const res = await fetch(BFT_CONTROL_API + "/run/" + segment_id, {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    return await res.json();
}

export async function run_dash_segment(segment_id, body) {
    const res = await fetch(DASH_CONTROL_API + "/run/" + segment_id, {
        method: 'POST',
        mode: 'cors',
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
    return await res.json();
}
