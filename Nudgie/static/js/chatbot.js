function handleSubmit() {
    let textField = document.getElementById("user_input");
    date_input = document.getElementById('date_input').value;

    let user_input = textField.value;
    
    textField.value = ""; // clear the text field

    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    var conversationDiv = document.getElementById("conversation");
    conversationDiv.innerHTML += "<strong>user :</strong> " + user_input + "<br>";

    // fetch is nice because it is asynchronous, similar to AJAX but
    // with a nicer API and built into the browser.
    fetch('/chatbot/api/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            message: user_input,
            datetime: date_input
        })
    })
    .then(response => response.json())
    .then(data => {
        var conversationDiv = document.getElementById("conversation");
        conversationDiv.innerHTML += "<strong>" + data.sender + ":</strong> " + data.message + "<br>";
        document.getElementById("user_input").value = ""; // Clear input field        
    });
}

document.addEventListener("DOMContentLoaded", function(){
    document.getElementById("chatForm").addEventListener("submit", function(event){
        event.preventDefault();
        handleSubmit();
    });

    document.getElementById('user_input').addEventListener('keydown', function(event) { 
        if (event.key == 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSubmit();
        }
    });
});