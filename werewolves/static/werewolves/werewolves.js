function sanitize(s) {
    // Be sure to replace ampersand first
    return s.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
}
function getCSRFToken() {
    let cookies = document.cookie.split(";")
    for (let i = 0; i < cookies.length; i++) {
        let c = cookies[i].trim()
        if (c.startsWith("csrftoken=")) {
            return c.substring("csrftoken=".length, c.length)
        }
    }
    return "unknown";
}
function updateError(xhr, status, error) {
    displayError('Status=' + xhr.status + ' (' + error + ')')
}

function displayError(message) {
    $("#error").html(message)
}



//var user_id = {{ User_ID }};
var user_id = 1;
var chatSocket = new WebSocket(
    'ws://' +
    window.location.host +
    '/ws/chat/' + user_id + '/'
)

chatSocket.onmessage = function(e) {
    var data = JSON.parse(e.data)
    var message = data['message']
    message = sanitize(message)
    console.log('message: ', message)
    addMessage(message)
}

chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly')
}

function sendMessage() {
    var messageInputDom = document.querySelector('#message_input');
    var message = messageInputDom.value;
    //var messageInputDom = document.getElementById('message_input');
    //var message = messageInputDom.value
    message = sanitize(message)
    console.log('message_onlick: ', message)
    chatSocket.send(JSON.stringify({
        'message': message
    }))
    messageInputDom.value = '';
}

function addMessage(message) {
    console.log(message)
    let list = document.getElementById("chatbox")

    let message_element = document.createElement("div")
    message_element.innerHTML = message
    list.appendChild(message_element)
}


