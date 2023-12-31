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
                .then(html => {
                    document.getElementById('tasks').innerHTML = html;
                })
        });
}

function standardSubmissionWrapper() {
    let textField = document.getElementById('user_input');
    let user_input = textField.value;
    textField.value = ''; // clear the text field

    handleSubmit(user_input);
}

document.getElementById('test-button').addEventListener('click', function (event) {
    let textField = document.getElementById('user_input');
    textField.value = '';

    s =
        handleSubmit("NOCONF hi. i want to learn to cook. i want to practice MWF at 5 PM every week. I tend to be very tired "
            + "on Mondays because of work. On Wednesday I'll need a bit of a boost because the kids tend to "
            + "keep me busy you know? Also on these same days (MWF) at 7 AM I'd like to study cooking theory."
            + "This will be a separate task from the cooking practice. I'd like this to last for one month.");
});

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('chatForm').addEventListener('submit', function (event) {
        event.preventDefault();

        standardSubmissionWrapper();
    });

    document.getElementById('user_input').addEventListener('keydown', function (event) {
        if (event.key == 'Enter' && !event.shiftKey) {
            event.preventDefault();

            standardSubmissionWrapper();
        }
    });

    document.getElementById('tasks').addEventListener('click', function (e) {

        if (e.target && e.target.classList.contains('task-trigger-btn')) {

            const task_name = e.target.getAttribute('data-task-name');
            const due_date = e.target.getAttribute('data-due-date');
            const next_run_time = e.target.getAttribute('data-next-run-time');
            const periodic_task_id = e.target.getAttribute('data-periodic-task-id');

            triggerPeriodicTask(task_name, due_date, next_run_time, periodic_task_id);
        }
    });
});

function triggerPeriodicTask(task_name, due_date, next_run_time, periodic_task_id) {
    // Handle the task trigger based on the task details
    console.log(`Task Name: ${task_name}, Due Date: ${due_date}`);

    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    fetch('/trigger_task/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            task_name: task_name,
            due_date: due_date,
            next_run_time: next_run_time,
            periodic_task_id: periodic_task_id
        })
    })
        .then(() => {
            fetch('/get_conversation_display/')
                .then(response => response.text())
                .then(html => {
                    document.getElementById('conversation').innerHTML = html;
                })
        })
        .then(() => {
            fetch('/get_task_list/')
                .then(response => response.text())
                .then(html => {
                    document.getElementById('tasks').innerHTML = html;
                })
        });
}