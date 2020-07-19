function ask_and_jump(message, target_url) {
    if (confirm(message)) {
        window.location.assign(target_url)
    }
}

function jump(target_url) {
    window.location.assign(target_url)
}