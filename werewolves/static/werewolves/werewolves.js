/**
 * create a new WebSocket with a certain websocket URL
 */
var chatSocket = new WebSocket(
    'ws://' +
    window.location.host +
    '/ws/chat/'
)
/**
 * when websocket receive message, call addMessage
 */
chatSocket.onmessage = function(e) {
    var data = JSON.parse(e.data)
    console.log(data)
    let message_type = data['message-type']
    let message = data['message']
    let username = data['username']
    if (message_type === 'chat_message') {
        message = sanitize(message)
        addMessage(message, username)
    } else if (message_type === 'players_message') {
        // Update number of players on the page
        let num_players = data['message']
        let player_count = document.getElementById('id_player_num')
        player_count.innerHTML = message + ' / 6'

        // Update list of player names on the page
        let all_players = data['players']
        console.log(all_players)
        let player_list = document.getElementById('id_player_list')
        // Remove the old player list
        while (player_list.hasChildNodes()) {
            player_list.removeChild(player_list.firstChild)
        }
        // Recreate the player list
        all_players.forEach(function(player_name) {
            let new_player  = document.createElement("li")
            new_player.innerHTML = player_name
            player_list.append(new_player)
        })

        // Update the player who just joined
        let player_name = data['last_player']
        let player_joined = document.getElementById('id_player_join')
        player_joined.innerHTML = player_name + ' joined'
        
        // TODO: Change later to == 6
        if (num_players > 0) {
            let startButton = document.getElementById('id_start_game_button')
            startButton.disabled = false
        }
    } else if (message_type === 'system_message') {
        addSystemMessage(message)
    }
}

function sendJoin() {
    if (chatSocket.readyState === 1) {
        chatSocket.send(JSON.stringify({
            'type': 'join-message',
            'message': 'Join',
        }))
    }
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
        'type': 'chat-message',
        'message': message
    }))
    messageInputDom.value = '';
}
/**
 * add the new message at the bottom of the chat box
 * need future update
 * @param message: the message to add to the chatbox 
 */
function addMessage(message, username) {
    // append a new messgae to the chat box
    // TODO: add time and need to distinguish different groups
    $("#chat-message-list").append (
        '<li class="message">' + '<span class="chat-username">' + username + '</span>: ' + message + '</li>'
    )
}

/**
 * add the system announcement to the chat box(or title)
 * @param message: the announcement
 */
function addSystemMessage(message) {
    if (message) {
        $("#chat-message-list").append (
            '<li class="message">' + 
            '<span>' + "system: " + message + '</span>' + 
            '</li>'
        )
    }
}
/**
 * send target id to update game status
 * gatme status will be update depends on the step
 * target includes: 
 *      wolves target,
 *      seer target, 
 *      guard target,
 *      vote target,
 * 
 */
function updateGameStatus() {
    chatSocket.send(JSON.stringify({
        'type': 'system-message',
        'update': 'update',
        'target_id': 1, /* should be the target id we choose, here for testing */
    }))
}

/**
 * update the next step in game procedure. send request to the websocket
 */

function nextStep() {
    /* send from websocket */
    //updateGameStatus()
    chatSocket.send(JSON.stringify({
        'type': 'system-message',
        'update': 'next_step'
    }))
}

// function getCSRFToken() {
//     let cookies = document.cookie.split(";")
//     for (let i = 0; i < cookies.length; i++) {
//         let c = cookies[i].trim()
//         if (c.startsWith("csrftoken=")) {
//             return c.substring("csrftoken=".length, c.length)
//         }
//     }
//     return "unknown";
// }
// function updateError(xhr, status, error) {
//     displayError('Status=' + xhr.status + ' (' + error + ')')
// }

// function displayError(message) {
//     $("#error").html(message)
// }