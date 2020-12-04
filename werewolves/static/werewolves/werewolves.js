/**
 * create a new WebSocket with a certain websocket URL
 */
var chatSocket = new WebSocket(
    'ws://' +
    window.location.host +
    '/ws/chat/'
)

/**
 * global object to store information received from system message
 */
var systemGlobal = {
    group: null,
    step: null,
    out_player_id: null,
    current_player_id: null,
    current_player_role: null,
    speaker_id: null,
    current_speaker_role: null,
    current_speaker_name: null,
    target_id: null,
    target_name: null,
    trigger_id: null,
    seer_id: null,
    wolf_id: null,
    villager_id: null,
    message: null
}

/**
 * when websocket receive message, call addMessage
 */
chatSocket.onmessage = function (e) {
    let data = JSON.parse(e.data)
    let message_type = data['message-type']
    let message = data['message']
    if (message_type === 'players_message') {
        playerMessage(data, message)
    } else if (message_type === 'start_game_message') {
        startGame()
    } else if (message_type === 'system_message') {
       systemMessageHandle(data)
    } else if (message_type === 'chat_message') {
        let username = data['username']
        let id = data['id']
        sanitize(message)
        addChatMessage(message, username, id)
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
    all_players.forEach(function (player_name) {
        let new_player = document.createElement("li")
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
 * handle system message received from websocket
 */
function systemMessageHandle(data) {
    updateSystemGlobal(data)
    let step = data['step']
    let role = data['current_player_role']
    let target_id = data['target_id']
    let out_player_id = data['out_player_id']
    let player_id = data['current_player_id']
    let trigger_id = data['trigger_id']
    // generate system message according to step.
    let systemMessage = generateSystemMessage(data, step)
    // show message in the chatbox.
    addSystemMessage(systemMessage)
    if (step === 'END_GAME') {
        updateEndGame(data)
    } else if (step === 'ANNOUNCE' || step === 'END_VOTE') {
        updateWithPlayersOut(out_player_id)
        if (player_id === trigger_id) {
            nextStep()
        }
    } else if (step === 'SPEECH') {
        if (data['speaker_id'] === null && player_id === trigger_id) {
                nextStep()
        } else {
            updateSpeaker(data)
        }
    } else if (step === 'END_DAY' || (step === 'WOLF' && out_player_id !== null)
        || (step === 'GUARD' && target_id !== null) || (step === 'SEER' && target_id !== null)) {
        if (player_id === trigger_id) {
            nextStep()
        }
    }
    // when to show the skip action button? when the players haven't decide target yet
    else if ((step === "WOLF"&& step === role && out_player_id === null )
        || (step !== "WOLF" && step === role && target_id === null)) {
        showNextStepButton("night")
    }
}




/**
 * update global system message object.
 * @param data information receiveed from websocket.
 */
function updateSystemGlobal(data) {
    systemGlobal.group = data['group']
    systemGlobal.step = data['step']
    systemGlobal.out_player_id = data['out_player_id']
    systemGlobal.current_player_id = data['current_player_id']
    systemGlobal.current_player_role = data['current_player_role']
    systemGlobal.sepaker_id = data['sepaker_id']
    systemGlobal.current_speaker_role = data['current_speaker_role']
    systemGlobal.current_speaker_name = data['current_speaker_name']
    systemGlobal.target_id = data['target_id']
    systemGlobal.target_name = data['target_name']
    systemGlobal.trigger_id = data['trigger_id']
    systemGlobal.seer_id = data['seer_id']
    systemGlobal.wolf_id = data['wolf_id']
    systemGlobal.villager_id = data['villager_id']
    systemGlobal.message = data['message']
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
 * @param username usename of the request user
 * @param id id of the chat message
 */
function addChatMessage(message, username, id) {
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
    } else if (group === "wolves" && step === "WOLF") {
        message = generateWolvesMessage(data, step)
    } else if (group === "guard" && step === "GUARD") {
        message = generateGuardMessage(data, step)
    } else if (group === "seer" && step === "SEER") {
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
    let target_id = data['target_id']
    let message = ""
    //send this message when the the night starts
    if (step === "END_DAY") {
        message = "It is night time."
    }
    //send this message when the wolf hasn't chosen any target
    else if (step === "WOLF" && target_id === null) {
        console.log(`target_id in general message ${target_id}`)
        message = "Wolf is choosing a player to kill."
    }
    //send this message when the guard hasn't chosen any target
    else if (step === "GUARD" && target_id === null) {
        message = "Guard is choosing a player to protect."
    }
    //send this message when the seer hasn't chosen any target
    else if (step === "SEER" && target_id === null) {
        message = "Seer is seeing a player's identity."
    } else if (step === "END_NIGHT") {
        message = "It is day time."
    } else if (step === "ANNOUNCE") {
        let out_player_id = data['out_player_id']
        if (out_player_id === '0') {
            message = "Last night, nobody gets killed."
        } else {
            let target_name = data['target_name']
            message = "Last night, Player " + out_player_id + " " + target_name + " gets killed."
        }
    } else if (step === "SPEECH") {
        let current_speaker_name = data['current_speaker_name']
        let speaker_id = data['speaker_id']
        if (speaker_id === '0') {
            message = "Now each player needs to make a speech."
        } else {
            message = "Player " + speaker_id + ", " + current_speaker_name + "'s turn to speak."
        }
    } else if (step === "VOTE") {
        message = "Now each player can make a vote. You can abstain from voting if you don't make a choice."
    } else if (step === "END_VOTE") {
       let  all_players_vote = data['all_players_vote']
        for (let i = 0; i < alive_players.length; i++) {
            let player_id = str(i + 1)
            let vote_id = alive_players[i]
            if (vote_id === '0') {
                message += "Player " + player_id + " abstained from voting \n"
            } else if (vote_id !== '-1') {
                message += "Player " + player_id + " voted Player " + vote_id + "\n"
            }
        }
        target_id = data['target_id']
        if (target_id !== '0') {
            let target_name = data['target_name']
            message += target_name + " is voted out.\n"
        } else {
            message += "Nobody gets voted out.\n"
        }
    } else if (step === "END_GAME") {
        message = "Game Over.\n"
        let winStatus = data['message']
        if (winStatus === 'Win') {
            message += "Good people won."
        } else {
            message += "Werewolves won."
        }
    }
    return message
}


/**
 * generate system messages for wolves group
 * @param data
 * @param step
 */
function generateWolvesMessage(data, step) {
    console.log("in wolevs messages")
    // target_id is the target that an individual wolf selects
    let target_id = data['target_id']
    console.log(`target_id ${target_id}`)
    // out_player_id is the common target of all the wolves
    let out_player_id = data['out_player_id']
    console.log(`out_player_id ${out_player_id}`)
    let message = ""
    // if the wolf hasn't decide who to choose
    if (target_id === null) {
        message = "All wolves should pick the same player to kill. You can choose to kill no one."
    }
    // if the wolves didn't pick the same target
    else if (out_player_id === null) {
        //TODO: how to distinguish different wolves
        message = "You chose to kill player " + target_id + ", but your teammate chose a different target. \n"
            + "All wolves should pick the same player to kill. You can have a discussion in the chat to decide a common target."
    }
    // if the wolves picked a target
    else if (out_player_id !== '0') {
        message = "You chose to kill player " + out_player_id + "."
    }
    // out_player_id === 0, if the wolves did not pick any target
    else {
        message = "You chose to kill no one"
    }
    return message
}

/**
 * generate system messages for guard group
 * @param data
 * @param step
 */
function generateGuardMessage(data, step) {
    console.log("in guard messages")
    let target_id = data['target_id']
    console.log(`target_id ${target_id}`)
    let message = ""
    // if the guard hasn't decided who to choose
    if (target_id === null) {
        message = "Choose a player to protect. \n"
        message += "Note that you can not protect the same player consecutively, and you can choose to protect nobody."
    }
    // if the guard picked a target
    else if (target_id !== '0') {
        message = "You chose to protect player " + target_id + "."
    }
    // if the guard did not pick any target
    else {
        message = "You chose to protect no one"
    }
    return message
}


/**
 * generate system messages for seer group
 * @param data
 * @param step
 */
function generateSeerMessage(data, step) {
    console.log("in seer messages")
    let target_id = data['target_id']
    console.log(`target_id ${target_id}`)
    let message = ""
    // if the seer hasn't decided who to choose
    if (target_id === null) {
        message = "Please choose a player to see a player's identity. The player will be either good or bad. \n"
        message += "Note that you can not choose not to see anybody."
    }
    // if the seer picked a target
    else if (target_id !== '0') {
        let target_role = data['message']
        if (target_role === "Good") {
            message = "Player " + target_id + " is good."
        } else if (target_role === "Bad"){
            message = "Player " + target_id + " is bad."
        }
    }
    // if the seer did not pick any target
    else {
        message = "You chose to see no one"
    }
    return message
}


/**
 * add the system announcement to the chat box(or title)
 * @param message: the announcement
 */
function addSystemMessage(message) {
    let date = new Date;
    let hours = date.getHours();
    let minutes = date.getMinutes();
    let seconds = date.getSeconds();
    let timeString = "" + hours;
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
    hideConfirmBtn(id);
    hideNextStepButton();
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
    console.log("in next step")
    hideNextStepButton()
    /* send from websocket */
    chatSocket.send(JSON.stringify({
        'type': 'system-message',
        'times_up': "False",
        'update': 'next_step',
    }))
}

/**
 make the confirm button visible if a player is selected and make all other buttons invisible
 **/
function selectPlayer(id) {
    //check if the role and step match first
    let step = systemGlobal.step
    let role = systemGlobal.current_player_role
    if (step === 'VOTE' || step === role) {
        for (let i = 1; i <= 6; i++) {
            if (i !== id) {
                let confirm_btn = document.getElementById('confirm_button_' + String(i))
                if (confirm_btn.style.display === 'block') {
                    confirm_btn.style.display = 'none'
                    confirm_btn.disabled = true
                }
            }
        }
        let currentButton = document.getElementById('confirm_button_' + String(id))
        currentButton.style.display = 'block'
        currentButton.disabled = false
    }
}


/**
 after updating game status in consumers.py, we should remove the confirm buttons on the page
 **/
function hideConfirmBtn(id) {
    let confirm_btn = document.getElementById('confirm_button_' + id)
    if (confirm_btn) {
        confirm_btn.style.display = 'none'
        confirm_btn.disabled = true
    }
}

function updateWithPlayersOut(outPlayersId) {
    let img = document.getElementById('avatar_' + outPlayersId + '_img')
    img.src = '/static/werewolves/images/out.png'
}

function updateSpeaker(data) {
    //remove stars
    for (let i = 1; i <= 6; i++) {
        var speaker_img = document.getElementById('avatar_' + i.toString() + '_img')
        if (speaker_img.src === '/static/werewolves/images/bad_speaking.png') {
            speaker_img.src = '/static/werewolves/images/bad_avatar.png'
        } else if (speaker_img.src === '/static/werewolves/images/good_speaking.png') {
            speaker_img.src = '/static/werewolves/images/good_avatar.png'
        }
    }
    let speakerId = data['speaker_id']
    let userId = data['current_player_id']
    let speaker_role = data['current_speaker_role']
    let user_role = data['current_player_role']
    let img = document.getElementById('avatar_' + speakerId + '_img')
    if (user_role === speaker_role && user_role === 'WOLF') {
        img.src = '/static/werewolves/images/bad_speaking.png'
    } else {
        img.src = '/static/werewolves/images/good_speaking.png'
    }
    if (speakerId === userId) {
       showNextStepButton("speak")
    }
}

//decide what content to show in the button
function showNextStepButton(option) {
    let btn = document.getElementById('next_step_button')
    btn.style.display = 'block'
    btn.disabled = false
    if (option === "night") {
        btn.innerHTML = "Skip Action"
        btn.onclick = "updateGameStatus(null)"
    } else if (option === "speak") {
        btn.innerHTML = "Finish"
        btn.onclick = "nextStep()"
    }
}

// hide the step button when the next step function is tirggered
function hideNextStepButton() {
    console.log("in hide next step button")
    let btn = document.getElementById('next_step_button')
    console.log(`btn ${btn}`)
    if (btn.style.display === 'block') {
        btn.style.display = 'none'
        console.log(`btn style ${btn.style.display}`)
        btn.disabled = true
        console.log(`btn disabled ${btn.disabled}`)
    }
}

function updateEndGame(data) {
    let winStatus = data['message']
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
    let current_player_role = data['current_player_role']
    if (current_player_role !== 'WOLF') {
        let wolves_ids = data['wolf_id']
        for (let i = 0; i < wolves_ids.length; i++) {
            let wolf_img = document.getElementById('avatar_' + wolves_ids[i] + '_img')
            wolf_img.src = '/static/werewolves/images/bad_avatar.png'
        }
    }
    //update villagers
    let villager_ids = data['villager_id']
    for (let i = 0; i < villager_ids.length; i++) {
        let villager_img = document.getElementById('avatar_' + villager_ids[i] + '_img')
        villager_img.src = '/static/werewolves/images/villager.png'
    }
    //update seer
    let seer_id = data['seer_id']
    let seer_img = document.getElementById('avatar_' + seer_id + '_img')
    seer_img.src = '/static/werewolves/images/seer.png'
    //update guard
    let guard_id = data['guard_id']
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
