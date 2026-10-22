"use strict";

const quizForm = document.querySelector("#quiz-form");

if (quizForm) {
  quizForm.addEventListener("submit", (event) => {
    if (!quizForm.reportValidity()) {
      event.preventDefault();
      return;
    }

    const submitButton = document.querySelector("#generate-button");
    const buttonLabel = document.querySelector("#button-label");
    const status = document.querySelector("#loading-status");

    submitButton.disabled = true;
    submitButton.setAttribute("aria-busy", "true");
    buttonLabel.textContent = "Building your quiz…";
    status.hidden = false;
  });
}
