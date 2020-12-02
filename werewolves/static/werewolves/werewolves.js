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
chatSocket.onmessage = function (e) {
    console.log('onmessage')
    var data = JSON.parse(e.data)
    let message_type = data['message-type']
    let message = data['message']
    let username = data['username']
    console.log('message_type:', message_type)
    if (message_type === 'players_message') {
        playerMessage(data, message)
    } else if (message_type === 'start_game_message') {
        startGame()
    } else if (message_type === 'system_message') {
        console.log('js system_message')
        step = data['step']
        console.log('step ', step)
        console.log('data:', data)
        target_id = data['target_id']
        // generate message according to step...
        message = generateSystemMessage(data, step)
        addSystemMessage(message)
        if (step === 'END_GAME') {
            updateEndGame(data)
        } else if (step === 'ANNOUNCE' || step === 'END_VOTE') {
            removeConfirmBtn(target_id)
            id = data['out_player_id']
            updateWithPlayersOut(id)
            nextStep()
        } else if (step === 'SPEECH') {
            updateSpeaker(data)
        } else {
            removeConfirmBtn(target_id)
        }
//FOR TESTING
//        updateWithPlayersOut(['1'])
//        updateSpeakerTest('1')
    } else if (message_type === 'chat_message') {
        username = data['username']
        id = data['id']
        sanitize(message)
        addMessage(message, username, id)
    } else if (message_type === 'select_message') {
        let target_id = data['target_id']
        let role = data['role']
        let step = data['step']
        let selected_player_status = data['selected_player_status']
//        console.log(`player role ${role}`)
//        console.log(`current status ${status}`)
        if (selected_player_status === 'ALIVE' && (role === step || step === 'VOTE')) {
            selectPlayer(target_id)
        }
    } else if (message_type === 'exit_game_message') {
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

        let start_button = document.getElementById('id_start_game_button')
        // Show start button only for the first joined player
//        if (message === 1) {
                start_button.style.visibility = 'visible'
//        }
        // Enable start button for the first player when we have two players in the game
//        if (message === 2 && start_button.style.visibility === 'visible') {
            start_button.disabled = false
//        }
}

/**
 * when websocket closed unexpectedly, print error message
 */
chatSocket.onclose = function (e) {
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
 Shujing: not sure when this is triggered?
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
    var hours = date.getHours();
    var minutes = date.getMinutes();
    var seconds = date.getSeconds();
    var timeString = "" + hours;
    timeString += ((minutes < 10) ? ":0" : ":") + minutes;
    timeString += ((seconds < 10) ? ":0" : ":") + seconds;
    if (message) {
        $("#chat-message-list").append(
            '<li class="messages" id="message_' + id + '">'
            + '<span class = "message-time" id="message_time_' + id + '"> [' + timeString + '] </span>  '
            + '<span class="chat-username">  ' + username + '</span>: ' +
            '<span class="message-text" id="message_text_' + id + '">' + message + '</span></li>'
        )
    }
}


// extra fields needed from system message: target_name, current_speaker_name, all_players_vote([idxd: vote_id]),

/**
 * generate different system messages according to different game steps
 * @param data
 * @param step: current game step
 */
function generateSystemMessage(data, step) {
    let message = ''
    let group = data['group']
    if (group === "general") {
        message = generateGeneralMessage(data, step)
    } else if (group === "wolves") {
        message = generateWolvesMessage(data, step)
    } else if (group === "guard") {
        message = generateGuardMessage(data, step)
    } else if (group === "seer") {
        message = generateSeerMessage(data, step)
    }
    return message
}

/**
 * generate message for general group
 * @param data
 * @param step
 */
function generateGeneralMessage(data, step) {
    if (step === "END_DAY") {
        message = "It is night time."
    } else if (step === "WOLF") {
        message = "Wolf is choosing a player to kill."
    } else if (step === "GUARD") {
        message = "Guard is choosing a player to protect."
    } else if (step === "SEER") {
        message = "Seer is seeing a player's identity."
    } else if (step === "END_NIGHT") {
        message = "It is day time."
    } else if (step === "ANNOUNCE") {
        target_id = data['target_id']
        if (target_id === '0') {
            message = "Last night, nobody gets killed."
        } else {
            target_name = data['target_name']
            message = "Last night, Player " + target_id + " " + target_name + " gets killed."
        }
    } else if (step === "SPEECH") {
        current_speaker_username = data['current_speaker_name']
        current_player_id = data['current_speaker_id']
        if (current_speaker_id === '0') {
            message = "Now each player needs to make a speech."
        } else {
            message = "Player " + current_speaker_id + ", " + current_speaker_username + "'s turn to speak."
        }
    } else if (step === "VOTE") {
        message = "Now each player can make a vote. You can abstain from voting if you don't make a choice."
    } else if (step === "END_VOTE") {
        all_players_vote = data['all_players_vote']
        for (let i = 0; i < alive_players.length; i++) {
            player_id = str(i + 1)
            vote_id = alive_players[i]
            if (vote_id === '0') {
                message += "Player " + player_id + " abstained from voting \n"
            } else if (vote_id !== '-1') {
                message += "Player " + player_id + " voted Player " + vote_id + "\n"
            }
        }
        target_id = data['target_id']
        if (target_id > 0) {
            target_name = data['target_name']
            message += target_name + " is voted out.\n"
        } else {
            message += "Nobody gets voted out.\n"
        }
    } else if (step === "END_GAME") {
        message = "Game Over.\n"
        winStatus = data['message']
        if (winStatus === 'Win') {
            message += "Good people won."
        } else {
            message += "Werewolves won."
        }
    }
}


/**
 * generate system messages for wolves group
 * @param data
 * @param step
 */
function generateWolvesMessage(data, step) {
    if (step === "WOLF") {
        message = "All wolves should pick the same player to kill. Wolves can decide to kill no one."
    } else {
        target_id = data['target_id']
        if (target_id !== 0) {
            target_name = data['target_name']
            message = "You chose to kill " + target_name
        } else {
            message = "You chose to kill no one"
        }
    }
}

/**
 * generate system messages for guard group
 * @param data
 * @param step
 */
function generateGuardMessage(data, step) {
    if (step === "GUARD") {
        message = "Choose a player to protect. \n"
        message += "Note that you can not protect the same player consecutively, and you can choose to protect nobody."
    } else {
        target_id = data['target_id']
        if (target_id !== 0) {
            target_name = data['target_name']
            message = "You chose to protect " + target_name
        } else {
            message = "You chose to protect no one"
        }
    }
}


/**
 * generate system messages for seer group
 * @param data
 * @param step
 */
function generateSeerMessage(data, step) {
    if (step === "SEER") {
        message = "Please choose a player to see a player's identity. The player will be either good or bad."
        message += "Note that you can not choose not to see anybody."
    } else {
        target_id = data['target_id']
        if (target_id !== 0) {
            target_role = data['target_role']
            if (target_role === "WOLF") {
                message = "This player is bad."
            } else {
                message = "This player is good."
            }
        } else {
            message = "You chose to see no one"
        }
    }
}


/**
 * add the system announcement to the chat box(or title)
 * @param message: the announcement
 */
function addSystemMessage(message) {
    var date = new Date;
    var hours = date.getHours();
    var minutes = date.getMinutes();
    var seconds = date.getSeconds();
    var timeString = "" + hours;
    timeString += ((minutes < 10) ? ":0" : ":") + minutes;
    timeString += ((seconds < 10) ? ":0" : ":") + seconds;
    if (message) {
        $("#chat-message-list").append(
            '<li class="messages">' +
            '<span class = "message-time"> [' + timeString + '] </span>' +
            '<span class="system-message">' + message + '</span>' +
            '</li>'
        )
    }
}

// * send target id to update game status
// * game status will be updated depends on the step
// * target includes:
// *      wolves target,
// *      seer target,
// *      guard target,
// *      vote target,
// *
// */
function updateGameStatus(id) {
    chatSocket.send(JSON.stringify({
        'type': 'system-message',
        'update': 'update',
        'target_id': id, /* should be the target id we choose, here for testing */
        'times_up': "False",
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
        'times_up': "False",
        'update': 'next_step',
    }))
}

/**
 triggered when the player selects an avatar
 need to know the current player role and game status for the confirm button to show
 **/
function sendSelect(id) {
    id = String(id)
    //want to see if role and step match and the player being selected is alive
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
            if (confirm_btn.style.display === 'block') {
                confirm_btn.style.display = 'none'
                confirm_btn.disabled = true
            }
        }
    }
    var currentButton = document.getElementById('confirm_button_' + String(id))
    currentButton.style.display = 'block'
    currentButton.disabled = false
}


/**
 after updating game status in consumers.py, we should remove the confirm buttons on the page
 **/
function removeConfirmBtn(id) {
    let confirm_btn = document.getElementById('confirm_button_' + id)
    confirm_btn.style.display = 'none'
    confirm_btn.disabled = true
}

function updateWithPlayersOut(outPlayersId) {
    let img = document.getElementById('avatar_' + outPlayersId + '_img')
    img.src = '/static/werewolves/images/out.png'
}

function updateSpeaker(data) {
    //remove stars
    for (let i = 1; i <= 6; i++) {
        var speaker_img = document.getElementById('avatar_' + str(i) + '_img')
        if (speaker_img.src === '/static/werewolves/images/bad_speaking.png') {
            speaker_img.src = '/static/werewolves/images/bad_avatar.png'
        } else if (speaker_img.src === '/static/werewolves/images/good_speaking.png') {
            speaker_img.src = '/static/werewolves/images/good_avatar.png'
        }
    }
    speakerId = data['current_speaker_id']
    userId = data['current_player_id']
    speaker_role = data['current_speaker_role']
    user_role = data['current_player_role']
    let img = document.getElementById('avatar_' + speakerId + '_img')
    if (user_role === speaker_role === 'WOLF') {
        img.src = '/static/werewolves/images/bad_speaking.png'
    } else {
        img.src = '/static/werewolves/images/good_speaking.png'
    }
    if (speakerId === userId) {
        let btn = document.getElementById('finish_button')
        btn.style.display = 'block'
        btn.disabled = false
    }
}

function updateEndGame(data) {
    winStatus = data['message']
    let area = docuemnt.getElementById('show_end_game')
    let text = ''
    if (winStatus === 'Win') {
        text = 'Good People Won!'
    } else {
        text = 'Werewolves Won!'
    }
    area.innerHTML = text
    //update avatars
    //update wolves
    current_player_role = data['current_player_role']
    if (current_player_role !== 'WOLF') {
        wolves_ids = data['wolf_id']
        for (let i = 0; i < wolves_ids.length; i++) {
            var wolf_img = document.getElementById('avatar_' + wolves_ids[i] + '_img')
            wolf_img.src = '/static/werewolves/images/bad_avatar.png'
        }
    }
    //update villagers
    villager_ids = data['villager_id']
    for (let i = 0; i < villager_ids.length; i++) {
        var villager_img = document.getElementById('avatar_' + villager_ids[i] + '_img')
        villager_img.src = '/static/werewolves/images/villager.png'
    }
    //update seer
    seer_id = data['seer_id']
    let seer_img = document.getElementById('avatar_' + seer_id + '_img')
    seer_img.src = '/static/werewolves/images/seer.png'
    //update guard
    guard_id = data['guard_id']
    let guard_img = document.getElementById('avatar_' + guard_id + '_img')
    guard_img.src = '/static/werewolves/images/guard.png'
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
