function handleSubmit(input_val) {
    date_input = document.getElementById('date_input').value;
    // Check if date_input is empty
    if (!date_input) {
        // Populate with the current datetime in the correct format, including seconds
        date_input = new Date().toISOString().slice(0, 19);
    }

    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    var conversationDiv = document.getElementById('conversation');
    conversationDiv.innerHTML += '<strong>user :</strong> ' + input_val + '<br>';

    // fetch is nice because it is asynchronous, similar to AJAX but
    // with a nicer API and built into the browser.
    fetch('/chatbot/api/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            message: input_val,
            datetime: date_input
        })
    })
    .then(response => response.json())
    .then(data => {
        var conversationDiv = document.getElementById('conversation');
        conversationDiv.innerHTML += '<strong>' + data.sender + ':</strong> ' + data.message + '<br>';
        document.getElementById('user_input').value = ''; // Clear input field
    })
    .then(() => {
        fetch('/get_task_list/')
            .then(response => response.text())
            .then(html=> {
                document.getElementById('tasks').innerHTML = html;
            })
    });
}

document.getElementById('test-button').addEventListener('click', function(event){
    let textField = document.getElementById('user_input');
    textField.value = '';

    handleSubmit('NOCONF hi. i want to learn to cook. i want to practice MWF at 5 PM every week.');
});

document.addEventListener('DOMContentLoaded', function(){
    document.getElementById('chatForm').addEventListener('submit', function(event){
        event.preventDefault();
        let textField = document.getElementById('user_input');
        let user_input = textField.value;
        textField.value = ''; // clear the text field

        handleSubmit(user_input);
    });

    document.getElementById('user_input').addEventListener('keydown', function(event) { 
        if (event.key == 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSubmit();
        }
    });
});