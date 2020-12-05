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
    current_player_status: null,
    speaker_id: null,
    current_speaker_role: null,
    target_id: null,
    trigger_id: null,
    seer_id: null,
    wolf_id: null,
    villager_id: null,
    message: null,
    all_players_vote: null,
    sender_id: null,
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
    } else if (message_type === 'change_host_message') {
        playerMessage(data, message)
    }
}

/**
 moduralized player message part of in message function
 **/
function playerMessage(data, message) {
    // Get message type from data
    let message_type = data['message-type']

    // Update number of players on the page
    let player_count = document.getElementById('id_player_num')
    player_count.innerHTML = message + ' / 6'

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
    if (message === 1 || message_type === 'change_host_message') {
        start_button.style.visibility = 'visible'
    }
    // Enable start button for the first player when we have two players in the game
    if (message === 6 && start_button.style.visibility === 'visible') {
        start_button.disabled = false
    }
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
    let status = data['current_player_status']
    let speaker_id = data['speaker_id']
    // generate system message according to step.
    if (!(step === "SPEECH" && speaker_id === null)) {
        let systemMessages = generateSystemMessage(data, step)
        // show message in the chatbox.
        if (step === "END_DAY" || step === "ANNOUNCE" || step === "END_VOTE" || step === 'END_GAME') {
            wait(1500)
            displayMessages(systemMessages)
        } else {
            displayMessages(systemMessages)
        }
    }
    if (step === 'END_GAME') {
        updateEndGame(data)
        showEndGameBtn()
        sendEndGame()
    } else if (step === 'ANNOUNCE' || step === 'END_VOTE') {
        if (out_player_id !== null) {
            updateWithPlayersOut(out_player_id)
        }
        if (player_id === trigger_id) {
            nextStep()
        }
    } else if (step === 'SPEECH') {
        if (speaker_id === null && player_id === trigger_id) {
            nextStep()
        } else if (speaker_id !== null) {
            updateSpeaker(data)
        }
    } else if (step === "VOTE") {
        let all_players_vote = data['all_players_vote']
        if (all_players_vote === "XXXXXX") {
            removeOldSpeaker()
        }
        if (status === "ALIVE" && target_id === null) {
            showNextStepButton("vote")
        } else if (status === "ALIVE" && target_id !== null) {
            hideNextStepButton()
        }
        if (out_player_id !== null && player_id === trigger_id) {
            nextStep()
        }
    } else if (status === "ALIVE" && (step === 'END_DAY' || (step === 'WOLF' && out_player_id !== null)
        || (step === 'GUARD' && target_id !== null) || (step === 'SEER' && target_id !== null))) {
        if (step === role) {
            hideNextStepButton();
        }
        if (player_id === trigger_id) {
            nextStep()
        }
    } else if ((step === "WOLF" && step === role && out_player_id === null)
        || (step !== "WOLF" && step === role && target_id === null)) {
        if (status === "ALIVE") {
            showNextStepButton("night")
        } else if (status === "OUT" && step !== "WOLF"){
            wait(5000)
            updateGameStatus(null)
        }
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
    systemGlobal.target_id = data['target_id']
    systemGlobal.trigger_id = data['trigger_id']
    systemGlobal.seer_id = data['seer_id']
    systemGlobal.wolf_id = data['wolf_id']
    systemGlobal.villager_id = data['villager_id']
    systemGlobal.message = data['message']
    systemGlobal.all_players_vote = data['all_players_vote']
    systemGlobal.current_player_status = data['current_player_status']
    systemGlobal.sender_id = data['sender_id']
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
 * synchronuous function to let the function wait before executing
 */
function wait(ms) {
    var start = Date.now(),
        now = start;
    while (now - start < ms) {
        now = Date.now();
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
    let message = []
    // let group = data['group']
    let role = data['current_player_role']
    let status = data['current_player_status']
    //send different messages according to role of the player
    if (status === "ALIVE" && step === "WOLF" && step === role) {
        message = generateWolvesMessage(data, step)
    } else if (status === "ALIVE" && step === "GUARD" && step === role) {
        message = generateGuardMessage(data, step)
    } else if (status === "ALIVE" && step === "SEER" && step === role) {
        message = generateSeerMessage(data, step)
    } else {
        message = generateGeneralMessage(data, step)
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
    let message = []
    let role = data['current_player_role']
    let is_kill = data['message']
    //send this message when the the night starts
    if (step === "END_DAY") {
        message.push("It is night time.")
    }
    //send this message when the wolf hasn't chosen any target
    else if (role !== "WOLF" && step === "WOLF" && is_kill === "False") {
        message.push("Wolf is choosing a player to kill.")
    }
    //send this message when the guard hasn't chosen any target
    else if (role !== "GUARD" && step === "GUARD" && target_id === null) {
        message.push("Guard is choosing a player to protect.")
    }
    //send this message when the seer hasn't chosen any target
    else if (role !== "SEER" && step === "SEER" && target_id === null) {
        message.push("Seer is seeing a player's identity.")
    } else if (step === "END_NIGHT") {
        message.push("It is day time.")
    } else if (step === "ANNOUNCE") {
        let out_player_id = data['out_player_id']
        if (out_player_id !== 0) {
            message.push("Last night, player " + out_player_id + " gets killed.")
        } else if (out_player_id === 0) {
            message.push("Last night, nobody gets killed.")
        }
    } else if (step === "SPEECH") {
        let speaker_id = data['speaker_id']
        if (speaker_id === null) {
            message.push("Now each player needs to make a speech.")
        } else {
            message.push("It's player " + speaker_id + "'s turn to speak.")
        }
    } else if (step === "VOTE") {
        let all_players_vote = data['all_players_vote']
        let player_id = data['current_player_id']
        let sender_id = data['sender_id']
        //print this only when nobody has voted
        if (all_players_vote === "XXXXXX") {
            message.push("Now each player can make a vote. You can abstain from voting.")
        } else if (player_id === sender_id && target_id !== 0) {
            message.push("You voted player " + target_id + ".")
        } else if (player_id === sender_id && target_id === 0) {
            message.push("You abstained from voting.")
        }
    } else if (step === "END_VOTE") {
        let votes = data['all_players_vote']
        for (let i = 0; i < 6; i++) {
            let player_id = String(i + 1)
            let vote_id = votes[i]
            if (vote_id === '0') {
                message.push("Player " + player_id + " abstained from voting")
            } else if (vote_id !== 'X') {
                message.push("Player " + player_id + " voted Player " + vote_id)
            }
        }
        let out_player_id = data['out_player_id']
        if (out_player_id === 0) {
            message.push("Nobody gets voted out")
        } else if (out_player_id){
            message.push("Player " + out_player_id + " is voted out.")
        }
    } else if (step === "END_GAME") {
        message.push("Game Over.")
        let winStatus = data['message']
        if (winStatus === 'Win') {
            message.push("Good people won.")
        } else {
            message.push("Werewolves won.")
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
    // target_id is the target that an individual wolf selects
    let target_id = data['target_id']
    // out_player_id is the common target of all the wolves
    let out_player_id = data['out_player_id']
    let message = []
    let is_kill = data['message']
    let player = data['current_player_id']
    let sender = data['sender_id']
    // if the none of the wolves have decided who to choose
    if (is_kill === "False") {
        console.log(`${is_kill}`)
        message.push("Now is your time to perform actions. Please choose a player to kill.")
        message.push("All wolves should pick the same player to kill. You can choose to kill no one.")
    }
    // if the wolves didn't pick the same target
    if (out_player_id === null) {
        if (target_id !== 0 && player === sender) {
            message.push("You chose to kill player " + target_id + ", but your teammate chose a different target.")
            message.push("All wolves should pick the same player to kill. You can have a discussion in the chat to decide a common target.")
        } else if (arget_id === 0 && player === sender){
            message.push("You chose to kill no one, but your teammate selected a target.")
            message.push("Wolves should have a common target. You can have a discussion in the chat to decide a common target.")
        }
    }
    // if the wolves picked a target
    else if (out_player_id === 0) {
        message.push("You chose to kill no one.")
    } else {
        message.push("You chose to kill player " + out_player_id + ".")
    }
    return message
}

/**
 * generate system messages for guard group
 * @param data
 * @param step
 */
function generateGuardMessage(data, step) {
    let target_id = data['target_id']
    let message = []
    // if the guard hasn't decided who to choose
    if (target_id === null) {
        message.push("Now is your time to perform actions. Please choose a player to protect.")
        message.push("Note that you can not protect the same player consecutively, and you can choose to protect nobody.")
    }
    // if the guard picked a target
    else if (target_id === 0) {
        message.push("You chose to protect no one.")
    }
    // if the guard did not pick any target
    else {
        message.push("You chose to protect player " + target_id + ".")
    }
    return message
}


/**
 * generate system messages for seer group
 * @param data
 * @param step
 */
function generateSeerMessage(data, step) {
    let target_id = data['target_id']
    let message = []
    // if the seer hasn't decided who to choose
    if (target_id === null) {
        message.push("Now is your time to perform actions. Please choose a player to see a player's identity.")
        message.push("The player will be either good or bad.")
        message.push("Note that you can not choose not to see anybody.")
    }
    // if the seer picked a target
    else if (target_id !== 0) {
        let target_role = data['message']
        if (target_role === "Good") {
            message.push("Player " + target_id + " is good.")
        } else if (target_role === "Bad") {
            message.push("Player " + target_id + " is bad.")
        }
    }
    // if the seer did not pick any target
    else {
        message.push("You chose to see no one")
    }
    return message
}

/**
 * add each message separately.
 */
function displayMessages(messages) {
    for (message of messages) {
        addSystemMessage(message)
        wait(500)
    }
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
    if(id === null) {
        removeAnyConfirmBtn()
    } else {
        hideConfirmBtn(id);
    }
    let sender_id = systemGlobal.current_player_id
    chatSocket.send(JSON.stringify({
        'type': 'system-message',
        'update': 'update',
        'target_id': id, /* should be the target id we choose, here for testing */
        'times_up': "False",
        'sender_id': sender_id,
    }))
}

/**
 * update the next step in game procedure. send request to the websocket
 */
function nextStep() {
    hideNextStepButton()
    /* send from websocket */
    let sender_id = systemGlobal.current_player_id
    chatSocket.send(JSON.stringify({
        'type': 'system-message',
        'times_up': "False",
        'update': 'next_step',
        'sender_id': sender_id
    }))
}

/**
 make the confirm button visible if a player is selected and make all other buttons invisible
 **/
function selectPlayer(id) {
    let status = systemGlobal.current_player_status
    if (status === "ALIVE") {
        //check if the role and step match first
        let step = systemGlobal.step
        let role = systemGlobal.current_player_role
        let target_id = systemGlobal.target_id
        let out_player_id = systemGlobal.out_player_id
        if ((step === 'VOTE' && target_id === null) ||
            (step === role && ((step === "WOLF" && out_player_id === null) || (step !== "WOLF" && target_id === null)))) {
            for (let i = 1; i <= 6; i++) {
                if (i !== id) {
                    let confirm_btn = document.getElementById('confirm_button_' + String(i))
                    if (confirm_btn.style.display === 'block') {
                        confirm_btn.style.display = 'none'
                        confirm_btn.disabled = true
                    }
                }
            }
            let out_img = '/static/werewolves/images/out.png'
            let avatar = document.getElementById('avatar_' + String(id) + '_img')
            if (avatar.getAttribute('src') !== out_img) {
                let currentButton = document.getElementById('confirm_button_' + String(id))
                currentButton.style.display = 'block'
                currentButton.disabled = false
            }
        }
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

/**
 * when the next step button is clicked, confirm button should be removed, too
 */
function removeAnyConfirmBtn() {
    for (let i = 1; i <= 6; i++) {
        let confirm_btn = document.getElementById('confirm_button_' + String(i))
        if (confirm_btn.style.display === 'block') {
            confirm_btn.style.display = 'none'
            confirm_btn.disabled = true
        }
    }
}

/**
 * change the avatar of a player if he/she is out of game
 * @param outPlayersId the id of the out player
 */
function updateWithPlayersOut(outPlayersId) {
    let img = document.getElementById('avatar_' + outPlayersId + '_img')
    if (img) {
        img.src = '/static/werewolves/images/out.png'
    }
}

/**
 * add sign to the new speaker and add the finish button
 * @param data information received from websocket
 */
function updateSpeaker(data) {
    removeOldSpeaker()
    let good_speaking_img = '/static/werewolves/images/good_speaking.png'
    let bad_speaking_img = '/static/werewolves/images/bad_speaking.png'
    let speakerId = data['speaker_id']
    let userId = data['current_player_id']
    let user_role = data['current_player_role']
    let speaker_role = data['current_speaker_role']
    let status = data['current_player_status']
    if (status === "ALIVE" && speakerId === userId) {
        showNextStepButton("speak")
    }
    //update speaker's avatar
    let img = document.getElementById('avatar_' + speakerId + '_img')
    if (user_role === 'WOLF' && speaker_role === "WOLF") {
        img.src = bad_speaking_img
    } else {
        img.src = good_speaking_img
    }
}

/**
 * removed the speaking sign of the previous speaker
 */
function removeOldSpeaker() {
    let good_speaking_img = '/static/werewolves/images/good_speaking.png'
    let bad_speaking_img = '/static/werewolves/images/bad_speaking.png'
    for (let i = 1; i <= 6; i++) {
        let id = String(i)
        let speaker_img = document.getElementById('avatar_' + id + '_img')
        if (speaker_img.getAttribute('src') === bad_speaking_img) {
            speaker_img.src = '/static/werewolves/images/bad_avatar.png'
        } else if (speaker_img.getAttribute('src') === good_speaking_img) {
            speaker_img.src = '/static/werewolves/images/good_avatar.png'
        }
    }
}


/**
 * the button is used for night action, finish speaking, and abstain vote
 * @param option
 */
function showNextStepButton(option) {
    let btn = document.getElementById('next_step_button')
    btn.style.display = 'block'
    btn.disabled = false
    if (option === "night") {
        btn.innerHTML = "Skip Action"
        btn.onclick = function () {
            updateGameStatus(null);
        };
    } else if (option === "speak") {
        btn.innerHTML = "Finish"
        btn.onclick = function () {
            nextStep();
        };
    } else if (option === "vote") {
        btn.innerHTML = "Abstain"
        btn.onclick = function () {
            updateGameStatus(null);
        };
    }
}

/**
 * hide next step button when the game moves to next step
 */
function hideNextStepButton() {
    let btn = document.getElementById('next_step_button')
    if (btn && btn.style.display === 'block') {
        btn.style.display = 'none'
        btn.disabled = true
    }
}

/**
 * update the canvas when the game is over
 * @param data information got from system message
 */
function updateEndGame(data) {
    let winStatus = data['message']
    let area = document.getElementById('show_end_game')
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

/**
 * triggered when the user clicked on the exit game href
 */
function exitGame() {
   chatSocket.send(JSON.stringify({
       'type': 'exit-game-message'
   }))
}

/**
 * send messages to websocket to inform clearing out database
 */
function sendEndGame() {
    chatSocket.send(JSON.stringify({
        'type': 'end-game-message'
    }))
}

/**
 * show the exit game btn to direct user to the rules page
 */
function showEndGameBtn() {
    let end_button = document.getElementById('id_end_game_hidden_button')
    end_button.style.display = 'block'
    end_button.disabled = false
}


// Update the count down every 1 second
// var countDown = setInterval(function() {
//     // Timer countdown is 2 minutes
//     var time = 120000

//     // Time calculations for minutes and seconds
//     var minutes = Math.floor((time % (1000 * 60 * 60)) / (1000 * 60))
//     var seconds = Math.floor((time % (1000 * 60)) / 1000)

//     // Output the result in an element with id="id_timer"
//     document.getElementById("id_timer").innerHTML = minutes + "m " + seconds + "s "

//     // If the count down is over, trigger next step
//     if (time < 0) {
//       clearInterval(countDown)
//       // Call next_step here
//       nextStep(true)
//     }
//   }, 1000);
