window.addEventListener("load", function() {
    var overlay = document.getElementById('passwordOverlay');
    var passwordInput = document.getElementById('passwordInput');
    var submitButton = document.getElementById('submitPassword');

    overlay.style.display = 'block';

    passwordForm.onsubmit = function(event) {
        event.preventDefault();  // Prevent the form from being submitted
        if (passwordInput.value != window.tempPassword) {
            alert("Incorrect password");
            document.querySelector('meta[name="viewport"]').setAttribute('content', 'width=device-width, initial-scale=1');
        } else {
            overlay.style.display = 'none';
        }
    }
});