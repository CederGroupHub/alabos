
// General
const STATUS_API = process.env.NODE_ENV === "production" ? "/api/status" : "http://localhost:8896/api/status";

export function get_status() {
    return fetch(STATUS_API, { mode: 'cors' })
        .then(res => res.json())
        .then(result => {
            return result;
        }).catch(error => console.warn(error));
}

// UserInputs
const RESPOND_USERREQUEST_API = process.env.NODE_ENV === "production" ? "/api/userinput/submit" : "http://localhost:8896/api/userinput/submit";
const PENDINGIDS_USERREQUEST_API = process.env.NODE_ENV === "production" ? "/api/userinput/pending" : "http://localhost:8896/api/userinput/pending";
const SPECIFIC_USERREQUEST_PREFIX = process.env.NODE_ENV === "production" ? "/api/userinput/" : "http://localhost:8896/api/userinput/";

export function get_pending_userinputrequests() {
    return fetch(PENDINGIDS_USERREQUEST_API, { mode: 'cors' })
        .then(res => res.json())
        .then(result => {
            return result.pending_requests;
        }).catch(error => console.warn(error));
}

export function respond_to_userinputrequest(request_id, status, note) {
    return fetch(RESPOND_USERREQUEST_API, {
        method: 'POST',
        mode: 'cors',
        body: JSON.stringify({
            "request_id": request_id,
            "status": status,
            "note": note
        })
    });
}

// Experiments
const ALL_EXPERIMENT_IDS_API = process.env.NODE_ENV === "production" ? "/api/experiment/get_all_ids" : "http://localhost:8896/api/experiment/get_all_ids";

const SPECIFIC_EXPERIMENT_API = process.env.NODE_ENV === "production" ? "/api/experiment/" : "http://localhost:8896/api/experiment/";

export function get_experiment_ids() {
    return fetch(ALL_EXPERIMENT_IDS_API, { mode: 'cors' })
        .then(res => res.json())
        .then(result => {
            return result.experiment_ids;
        }).catch(error => console.warn(error));
}


export function get_experiment_status(experiment_id) {
    return fetch(SPECIFIC_EXPERIMENT_API + experiment_id, { mode: 'cors' })
        .then(res => res.json())
        .then(result => {
            return result;
        }).catch(error => console.warn(error));
}