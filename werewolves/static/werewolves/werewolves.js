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
    $("#error").html(message);
}

//var user_id = {{ User_ID }};
var user_id = 1;
var chatSocket = new WebSocket(
    'ws://' +
    window.location.host +
    '/ws/chat/' + user_id + '/'
);

chatSocket.onmessage = function(e) {
    var data = JSON.parse(e.data);
    var message = data['message'];
    console.log('message: ', message);
    message = santinize(message);
    document.querySelector('#chatbox').value += (message + '\n');
};

chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly');
};
/*
document.querySelector('#message_input').focus();
document.querySelector('#message_input').onkeyup = function(e) {
    if (e.keyCode === 13) {  // enter, return
        document.querySelector('#message_button').click();
    }
};
document.querySelector('#message_button').onclick = function(e) {
    var messageInputDom = document.querySelector('#message_input');
    var message = messageInputDom.value;
    message = santinize(message);
    chatSocket.send(JSON.stringify({
        'message': message
    }));

    messageInputDom.value = '';
};*/