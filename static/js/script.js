var startButton = document.querySelector("#startQuiz");     // Main page start button
var timer = document.querySelector("#timer");               // Timer when quiz starts
var mainContent = document.querySelector("#mainContent");   // Start page content div
var questionEl = document.querySelector("#title");          // card title
var quizContent = document.querySelector("#quizContent");   // Question options div
var resultDiv = document.querySelector("#answer");          // Div for showing answer is correct/wrong
var completeTest = document.querySelector("#completeTest"); // Div for displaying final scores
var navhighscorelink = document.querySelector("#navhighscorelink");

var secondsLeft = 300, questionIndex = 0, correct = 0;
var totalQuestions = typeof questions !== 'undefined' ? questions.length : 0;
var ans;
var choiceArray = [], divArray = [];
var examSubmitted = false;
var isProcessingAnswer = false;
var transitionTimeout = null;

// Create buttons for choices
for (var i = 0; i < 4; i++) {
    var dv = document.createElement("div");
    var ch = document.createElement("button");
    ch.setAttribute("data-index", i);
    ch.setAttribute("class", "btn rounded-pill mb-2 option-btn");
    ch.setAttribute("style", "background:#5f9ea0; color: #fff; width: 100%; text-align: left; padding: 10px 20px; transition: background 0.2s;");
    choiceArray.push(ch);
    divArray.push(dv);
}

// Start Quiz function
function startQuiz() {
    if (startButton) {
        startButton.disabled = true;
        startButton.style.display = "none";
    }
    startTimer();
    buildQuestion();
}

// Function to start timer when quiz starts
function startTimer() {
    var timeInterval = setInterval(function () {
        secondsLeft--;
        if (timer) {
            timer.textContent = "Time : " + Math.max(0, secondsLeft) + " sec";
        }

        if (secondsLeft <= 0 || questionIndex >= totalQuestions) {
            clearInterval(timeInterval);
            if (transitionTimeout) clearTimeout(transitionTimeout);
            if (resultDiv) resultDiv.style.display = "none";
            if (quizContent) quizContent.style.display = "none";
            if (timer) timer.textContent = "Time's up!";
            viewResult();
            if (secondsLeft <= 0 && !examSubmitted) {
                submitExam();
            }
        }
    }, 1000);
}

function buildQuestion() {
    if (examSubmitted || secondsLeft <= 0) {
        viewResult();
        return;
    }
    isProcessingAnswer = false;
    if (questionEl) questionEl.style.display = "none";
    if (mainContent) mainContent.style.display = "none";
    if (quizContent) quizContent.style.display = "none";

    if (questionIndex >= totalQuestions) {
        viewResult();
        return;
    }

    ans = (questions[questionIndex].answer || "").trim();

    if (questionEl) {
        questionEl.innerHTML = "Q" + (questionIndex + 1) + ": " + questions[questionIndex].title;
        questionEl.setAttribute("class", "text-left");
        questionEl.style.display = "block";
    }

    if (quizContent) {
        quizContent.innerHTML = "";
        for (var j = 0; j < 4; j++) {
            var index = choiceArray[j].getAttribute("data-index");
            var optionText = questions[questionIndex].choices[index] || "";
            choiceArray[j].disabled = false;
            choiceArray[j].style.opacity = "1";
            choiceArray[j].textContent = (+index + 1) + ". " + optionText.trim();
            divArray[j].appendChild(choiceArray[j]);
            quizContent.appendChild(divArray[j]);
        }
        quizContent.style.display = "block";
    }
}

// Event Listener for options buttons
if (quizContent) {
    quizContent.addEventListener("click", function (event) {
        var element = event.target;
        if (!element.classList.contains("option-btn") || isProcessingAnswer) {
            return;
        }

        isProcessingAnswer = true;
        // Disable all buttons immediately to prevent multi-clicking
        choiceArray.forEach(function (btn) {
            btn.disabled = true;
            btn.style.opacity = "0.7";
        });

        var userAnswer = element.textContent.trim();
        var dotIndex = userAnswer.indexOf(". ");
        var userOption = dotIndex !== -1 ? userAnswer.substring(dotIndex + 2).trim() : userAnswer;

        if (userOption.toLowerCase() === ans.toLowerCase()) {
            correct++;
            if (resultDiv) {
                resultDiv.textContent = "✔ Correct!";
                resultDiv.style.color = "#28a745";
                resultDiv.style.fontWeight = "bold";
                resultDiv.style.display = "block";
            }
        } else {
            secondsLeft = Math.max(0, secondsLeft - 10);
            if (resultDiv) {
                resultDiv.textContent = "✖ Wrong answer! (-10 sec)";
                resultDiv.style.color = "#dc3545";
                resultDiv.style.fontWeight = "bold";
                resultDiv.style.display = "block";
            }
        }

        transitionTimeout = setTimeout(function () {
            if (resultDiv) {
                resultDiv.style.display = "none";
            }
            if (examSubmitted || secondsLeft <= 0) return;
            questionIndex++;
            buildQuestion();
        }, 600);
    });
}

function submitExam() {
    if (examSubmitted) return;
    examSubmitted = true;
    if (transitionTimeout) clearTimeout(transitionTimeout);

    var submitBtn = document.querySelector("#submitTestBtn");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Submitting exam...";
    }

    $.ajax({
        type: "POST",
        url: "/exam",
        contentType: "application/json",
        data: JSON.stringify({ input: correct }),
        success: function (response) {
            if (response && response.link) {
                window.location.href = "/" + response.link + "/" + encodeURIComponent(response.output);
            }
        },
        error: function (xhr, status, error) {
            console.error("Exam submission failed:", error);
            window.location.href = "/showResultFail/ExamCompleted";
        }
    });
}

// Function to show score when quiz completes
function viewResult() {
    if (questionEl) {
        questionEl.innerHTML = "Great Job! Your Test is Completed!";
        questionEl.style.display = "block";
    }

    if (completeTest && !document.querySelector("#submitTestBtn")) {
        var scoreButton = document.createElement("button");
        scoreButton.id = "submitTestBtn";
        scoreButton.setAttribute("class", "btn rounded-pill mb-2 ml-3 mt-2 btn-success");
        scoreButton.textContent = "Submit Exam";
        completeTest.appendChild(scoreButton);

        scoreButton.addEventListener("click", function () {
            submitExam();
        });
    }
}

// Start button event listener
$(document).ready(function () {
    if (startButton) {
        startButton.addEventListener("click", function () {
            startButton.disabled = true;
            $.ajax({
                type: "POST",
                url: "/exam",
                contentType: "application/json",
                data: JSON.stringify({ input: '' }),
                success: function (response) {
                    startQuiz();
                },
                error: function (xhr, status, error) {
                    startQuiz();
                }
            });
        });
    }
});
