var firstChunkReceived = false; // Move the flag to a broader scope
let currentReplyP = null;

// Scroll the conversation to the bottom always

function scrollToBottom() {
    const conversationDiv = document.getElementById("conversation");
    console.log("clientHeight is: " + conversationDiv.clientHeight, "scrollHeight is: " + conversationDiv.scrollHeight);

    // Just use the scrollHeight of the conversation to scroll to the bottom
    setTimeout(() => {
        conversationDiv.scrollTop = conversationDiv.scrollHeight;
    }, 0);
}


// function scrollToBottom() {
//     const conversationDiv = document.getElementById("conversation");
//     console.log("clientHeight is: " + conversationDiv.clientHeight, "scrollHeight is: " + conversationDiv.scrollHeight);
//     const inputArea = document.getElementById("chatForm");
//     const totalHeight = conversationDiv.scrollHeight + inputArea.offsetHeight;
//     const visibleHeight = conversationDiv.offsetHeight;
//     const isOverflowing = totalHeight > visibleHeight;
//     setTimeout(() => {
//         conversationDiv.scrollTop = conversationDiv.scrollHeight;
//     }, 0);
// }


// First, grab the user's question from the question box
function askQuestion() {
    document.getElementById('askButton').disabled = true;
    document.querySelector('select[name="prompt_id"]').disabled = true;
    document.querySelector('select[name="llmmodelid"]').disabled = true;
    const question = document.getElementById("questionInput").value;
    const promptId = document.getElementById("prompt_id").value;
    const llmmodelId = document.getElementById("llmmodelid").value;
    questionInput.value = "";
    firstChunkReceived = false; // Reset the flag for each new question

    // Create a space for the conversation
    const conversationDiv = document.getElementById("conversation");

    // Add user's question
    const questionP = document.createElement("p");
    questionP.textContent = question;
    questionP.classList.add("user-question"); // Add a class to style it differently
    conversationDiv.appendChild(questionP); 

    // Display "Thinking..." while waiting for first chunk, then stream reply 
    currentReplyP = document.createElement("p");
    currentReplyP.innerHTML = "Thinking...<span class=\"spinner\"></span>";
    currentReplyP.classList.add("gpt-response");
    conversationDiv.appendChild(currentReplyP);
    scrollToBottom();

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/ask", true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            console.log("Question asked.");
        }
    }
    xhr.send("question=" + encodeURIComponent(question) + "&prompt_id=" + encodeURIComponent(promptId) + "&llmmodelid=" + encodeURIComponent(llmmodelId));
}


// Now stream the reply from the llm api
function setupEventSource() {
    if (window.eventSource) {
        window.eventSource.close(); // Close the existing connection if it exists
    }
    window.eventSource = new EventSource("/stream");

    window.eventSource.onmessage = function(e) {
        document.getElementById('askButton').disabled = true;
        console.log("Received Chunk: " + e.data);

        if (e.data === 'ENDEND') {
            document.getElementById('askButton').disabled = false;
            currentReplyP.innerHTML = currentReplyP.textContent;

            // Make a request to the /reset endpoint
            fetch('/reset_streaming_answer')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                // Handle response here if needed
            })
            .catch(error => {
                console.error('There has been a problem with your fetch operation:', error);
            });

        } else {
            document.getElementById('askButton').disabled = true;
            if (!firstChunkReceived) {
                if (currentReplyP) { 
                    currentReplyP.textContent = e.data; // Replace "Thinking..."
                }
                firstChunkReceived = true;
            } else {
                if (currentReplyP) {
                    currentReplyP.textContent += e.data;
                    scrollToBottom();
                }
            }
        }
    };
}

window.addEventListener("load", setupEventSource);

window.addEventListener("load", function() {
    var overlay = document.getElementById('passwordOverlay');
    var passwordInput = document.getElementById('passwordInput');
    var submitButton = document.getElementById('submitPassword');

    overlay.style.display = 'block';

    passwordForm.onsubmit = function(event) {
        event.preventDefault();  // Prevent the form from being submitted
        if (passwordInput.value != window.dcxChatPassword) {
            alert("Incorrect password");
            document.querySelector('meta[name="viewport"]').setAttribute('content', 'width=device-width, initial-scale=1');
        } else {
            overlay.style.display = 'none';
        }
    }
    
    // Optionally, only reset under certain conditions, e.g., a specific query parameter is present
    fetch('/reset').then(response => {
        console.log("Session reset.");
        // Proceed with any other initialization, like setting up the event source
        setupEventSource();
    });
});