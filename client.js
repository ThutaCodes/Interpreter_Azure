const serverUrl = "ws://localhost:8765";
const socket = new WebSocket(serverUrl);

const languageSelector = document.getElementById("languageSelector");
const setLanguageButton = document.getElementById("setLanguage");
const outputDiv = document.getElementById("output");

socket.addEventListener("open", () => {
  console.log("WebSocket connected.");
});

socket.addEventListener("message", (event) => {
  console.log("Message from server:", event.data); // Log the incoming message

  const data = JSON.parse(event.data);

  if (data.translation) {
    // If the message contains a translation, append it to the UI
    outputDiv.textContent += `\n${data.translation}`;
  } else if (data.message) {
    // For general server messages
    outputDiv.textContent += `\n${data.message}`;
  } else {
    console.log("Unrecognized message format:", data);
  }
});

socket.addEventListener("close", () => {
  console.log("WebSocket disconnected.");
});

socket.addEventListener("error", (error) => {
  console.error("WebSocket error:", error);
});

setLanguageButton.addEventListener("click", () => {
  const selectedLanguage = languageSelector.value;
  socket.send(JSON.stringify({ language: selectedLanguage })); // Notify server of selected language
  console.log(`Language set to ${selectedLanguage}`);
  outputDiv.textContent += `\nLanguage set to ${selectedLanguage}`;
});
