
// General

const URL = "http://192.168.2.12:8895";
const STATUS_API = process.env.NODE_ENV === "production" ? "/api/status" : URL + "/api/status";
console.log(STATUS_API);
export function get_status() {
    return fetch(STATUS_API, { mode: 'cors' })
        .then(res => res.json())
        .then(result => {
            return result;
        }).catch(error => console.warn(error));
}

// UserInputs
const RESPOND_USERREQUEST_API = process.env.NODE_ENV === "production" ? "/api/userinput/submit" : URL + "/api/userinput/submit";
const PENDINGIDS_USERREQUEST_API = process.env.NODE_ENV === "production" ? "/api/userinput/pending" : URL + "/api/userinput/pending";
const SPECIFIC_USERREQUEST_PREFIX = process.env.NODE_ENV === "production" ? "/api/userinput/" : URL + "/api/userinput/";

export function get_pending_userinputrequests() {
    return fetch(PENDINGIDS_USERREQUEST_API, { mode: 'cors' })
        .then(res => res.json())
        .then(result => {
            var return_values = Object();
            return_values["pending"] = result.pending_requests;
            return_values["experiment_id_to_name"] = result.experiment_id_to_name;
            return return_values;
        }).catch(error => console.warn(error));
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