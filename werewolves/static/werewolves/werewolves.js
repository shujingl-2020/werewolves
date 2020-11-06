/**
 * create a new WebSocket with a certain websocket URL
 */
var chatSocket = new WebSocket(
    'ws://' +
    window.location.host +
    '/ws/chat/' //+ user_id + '/'
)
/**
 * when websocket receive message, call addMessage
 */
chatSocket.onmessage = function(e) {
    var data = JSON.parse(e.data)
    var message = data['message']
    message = sanitize(message)
    addMessage(message)
}
/**
 * when websocket closed unexpectedly, print error message
 */
chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly')
}

/**
 * sanitize input text
 */ 
function sanitize(s) {
    // Be sure to replace ampersand first
    return s.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
}

/**
 * send a message from websocket
 */
function sendMessage() {
    var messageInputDom = document.querySelector('#message_input');
    var message = messageInputDom.value;
    message = sanitize(message)
    /* send from websocket */
    chatSocket.send(JSON.stringify({
        'message': message
    }))
    messageInputDom.value = '';
}
/**
 * add the new message at the bottom of the chat box
 * need future update
 * @param message: the message to add to the chatbox 
 */
function addMessage(message) {
    let list = document.getElementById("chatbox")
    let message_element = document.createElement("div")
    message_element.innerHTML = message
    list.appendChild(message_element)
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
