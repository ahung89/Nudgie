document.addEventListener("DOMContentLoaded", function(){
    document.getElementById("chatForm").addEventListener("submit", function(event){
        event.preventDefault();
        var user_input = document.getElementById("user_input").value;
        let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        //  hacky as hell, would be better to include this in the response rather than hardcoding but this is all placeholder so its ok.
        //  i'll do it later lol
        var conversationDiv = document.getElementById("conversation");
        conversationDiv.innerHTML += "<strong>User :</strong> " + user_input + "<br>";
        fetch('/chatbot/api/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                message: user_input
            })
        })
        .then(response => response.json())
        .then(data => {
            var conversationDiv = document.getElementById("conversation");
            conversationDiv.innerHTML += "<strong>" + data.sender + ":</strong> " + data.message + "<br>";
            document.getElementById("user_input").value = ""; // Clear input field        
        });
    });
});