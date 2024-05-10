async function setSessionHash() {
    const sessionHashSpan = document.getElementById("session_hash_span");
    const sessionHash = await fetch(
        `http://raspberrypi.local/api/v1/session_hash/latest`,
        {
            method: "GET",
            headers: {
                Accept: "application/json"
            }
        }
    ).then((r) => r.json()).then((r) => r.session_hash);
    sessionHashSpan.innerText = `Current session hash: ${sessionHash}`;
    
    const sessionHashSelect = document.getElementById("session_hash_select");
    const sessionHashOptionsArr = await fetch(
        `http://raspberrypi.local/api/v1/session_hash/all`,
        {
            method: "GET",
            headers: {
                Accept: "application/json"
            }
        }
    ).then((r) => r.json()).then((r) => r.session_hashes);
    while (sessionHashSelect.firstChild) {
        sessionHashSelect.removeChild(sessionHashSelect.lastChild);
    }
    for (let hash of sessionHashOptionsArr) {
        let thisEl = document.createElement("option");
        thisEl.innerText = `${new Date(hash[1]).toLocaleString('en-CA')} - ${hash[0]}`; // [datetime_created] - [session_hash]
        sessionHashSelect.appendChild(thisEl);
    }
    sessionHashDisplayUpdate();
};

function sessionHashDisplayUpdate() {
    let hash = document.getElementById("session_hash_select").value.split("-")[3]
    document.getElementById("session_hash_selected_display").innerText = `Selected hash: ${hash}`
}

async function download(format) {
    document.getElementById("loading_dialog").showModal();
    let selectedTag = document.getElementById("session_hash_select").value.split("-")[3].trim();
    try {
        const response = await fetch(
            `http://raspberrypi.local/api/v1/race_data/all/${selectedTag}/${format}`,
            {
                method: "GET"
            }
        );
            
        if (response.redirected) {
            window.open(response.url, '_blank');
            document.getElementById("loading_dialog").close();
        } else {
            document.getElementById("loading_dialog_label").innerText = `HTTP Error${response.status ? ` ${response.status}` : ""}. Check console`;
            console.log(response);
        }
    } catch (err) {
        document.getElementById("loading_dialog_label").innerText = "Fetch Error! Check console";
        console.log(err);
    }
}

setSessionHash();