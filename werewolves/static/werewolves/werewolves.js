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

    let message_type = data['message-type']
    let message = data['message']
    let username = data['username']

    if (message_type === 'players_message') {
        playerMessage(data, message)
    }
    else if (message_type === 'start_game_message') {
        startGame()
    }
    else if (message_type === 'system_message') {
        addSystemMessage(message)
    }
    else if (message_type === 'chat_message') {
        username = data['username']
        id = data['id']
        sanitize(message)
        addMessage(message, username, id)
    }
    else if (message_type === 'select_message') {
        let target_id = data['target_id']
        let role = data['role']
        let status = data['status']
//        console.log(`player role ${role}`)
//        console.log(`current status ${status}`)
        if (role === status || status === 'VOTE') {
             selectPlayer(target_id)
        }
    }
    else if (message_type === 'confirm_message') {
         updateCanvas()
    }
    else if (message_type === 'exit_game_message') {
        endGame()
    }
}

/**
moduralized player message part of in message function
**/
function playerMessage(data, message) {
        // Update number of players on the page
        let player_count = document.getElementById('id_player_num')
        player_count.innerHTML = message + ' / 6' // TODO: Change to ' / 6' later

        // Update list of player names on the page
        let all_players = data['players']
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

        let start_button = document.getElementById('id_start_game_hidden_button')
//         Show start button only for the first joined player
//        if (message === 1) {
            start_button.style.visibility = 'visible'
//        }
         //Enable start button for the first player when we have two players in the game
//        if (message === 2 && start_button.style.visibility === 'visible') {
            start_button.disabled = false
//        }
}

/**
 * when websocket closed unexpectedly, print error message
 */
chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly')
}

/**
triggered when the player enters the waiting room page
**/
function sendJoin() {
    if (chatSocket.readyState === 1) {
        chatSocket.send(JSON.stringify({
            'type': 'join-message',
            'message': 'Join',
        }))
    }
}

/**
triggered when the player clicks on the start button
**/
function sendStart() {
    chatSocket.send(JSON.stringify({
        'type': 'start-game-message'
    }))
}


/**
enter the game page
**/
function startGame() {
    let start_button = document.getElementById('id_start_game_hidden_button')
    start_button.disabled = false
    start_button.click()
}

/**
Shujing: not sure when is this triggered?
**/
function distributeCard() {
    chatSocket.send(JSON.stringify({
        'type': 'distribute-card-message',
        'message': 'Distribute Card',
    }))
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
 * add the new message at the bottom of the chat box
 * need future update
 * @param message: the message to add to the chatbox
 */
function addMessage(message, username, id) {
    // append a new messgae to the chat box
    var date = new Date;
    var hours   = date.getHours();
    var minutes = date.getMinutes();
    var seconds = date.getSeconds();
    var timeString = "" + hours;
    timeString  += ((minutes < 10) ? ":0" : ":") + minutes;
    timeString  += ((seconds < 10) ? ":0" : ":") + seconds;
    if (message) {
    $("#chat-message-list").append (
      '<li class="messages" id="message_' +  id + '">'
      +'<span class = "message-time" id="message_time_' + id + '"> [' + timeString + '] </span>  '
      +'<span class="chat-username">  ' + username + '</span>: '+
      '<span class="message-text" id="message_text_' + id + '">' + message + '</span></li>'
     )
     }
}

/**
 * add the system announcement to the chat box(or title)
 * @param message: the announcement
 */
function addSystemMessage(message) {
    var date = new Date;
    var hours   = date.getHours();
    var minutes = date.getMinutes();
    var seconds = date.getSeconds();
    var timeString = "" + hours;
    timeString  += ((minutes < 10) ? ":0" : ":") + minutes;
    timeString  += ((seconds < 10) ? ":0" : ":") + seconds;
    if (message) {
        $("#chat-message-list").append (
            '<li class="messages">' +
            '<span class = "message-time"> [' + timeString + '] </span>' +
            '<span class="system-message">' + message + '</span>' +
            '</li>'
        )
    }
}

// Shujing: I implemented this in sendConfirm function, not sure if we should still include this function
// * send target id to update game status
// * game status will be update depends on the step
// * target includes:
// *      wolves target,
// *      seer target,
// *      guard target,
// *      vote target,
// *
// */
//function updateGameStatus() {
//    chatSocket.send(JSON.stringify({
//        'type': 'system-message',
//        'update': 'update',
//        'target_id': 1, /* should be the target id we choose, here for testing */
//    }))
//}

/**
 * update the next step in game procedure. send request to the websocket
 */
function nextStep() {
    /* send from websocket */
    //updateGameStatus()
    chatSocket.send(JSON.stringify({
        'type': 'system-message',
        //'update': 'next_step'
    }))
}

/**
triggered when the player selects an avatar
need to know the current player role and game status for the confirm button to show
**/
function sendSelect(id) {
    id = String(id)
    chatSocket.send(JSON.stringify({
        'type': 'select-message',
        'id': id,
    }))
}

/**
make the confirm button visible if a player is selected and make all other buttons invisible
**/
function selectPlayer(id) {
   for (let i = 1; i <= 6; i++) {
        if (i !== id) {
            var confirm_btn = document.getElementById('confirm_button_' + String(i))
            if (confirm_btn.style.display ==='block') {
                  confirm_btn.style.display ='none'
                  confirm_btn.disabled = true
            }
        }
   }
   var currentButton = document.getElementById('confirm_button_' + String(id))
   currentButton.style.display ='block'
   currentButton.disabled = false
}

/**
triggered when the player clicks on a confrim button
update game status in consumers.py
**/
function sendConfirm(target_id) {
    console.log('in send confirm')
    id = String(target_id)
    chatSocket.send(JSON.stringify({
        'type': 'confirm-message',
        'target': id
    }))
}

/**
after updating game status in consumers.py, we should remove the confirm buttons on the page
**/
function updateCanvas() {
    // as for werewolves, they may have selected different targets,  so we need to have a generic opearation
    var elements = document.getElementsByClassName('confirm-button');
    while(elements.length > 0){
        elements[0].parentNode.removeChild(elements[0]);
    }
}


//function exitGame() {
//    chatSocket.send(JSON.stringify({
//        'type': 'exit-game-message'
//    }))
//}
//
//function endGame() {
//    let end_button = document.getElementById('id_end_game_button')
//    end_button.disabled = false
//    end_button.click()
//}