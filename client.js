const serverUrl = "ws://localhost:8765";
const socket = new WebSocket(serverUrl);

const languageSelector = document.getElementById("languageSelector");
const recognitionLanguageSelector = document.getElementById(
  "recognitionLanguageSelector"
);
const setLanguageButton = document.getElementById("setLanguage");
const outputDiv = document.getElementById("output");

socket.addEventListener("open", () => {
  console.log("WebSocket connected.");
  outputDiv.innerHTML += "<br>WebSocket connected.";
});

socket.addEventListener("message", async (event) => {
  const data = JSON.parse(event.data);
  if (data.translation) {
    outputDiv.innerHTML += `<br><strong>Translation:</strong> ${data.translation}`;
  }
  if (data.audio) {
    const audioData = Uint8Array.from(atob(data.audio), (c) => c.charCodeAt(0));
    try {
      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
      const audioBuffer = await audioContext.decodeAudioData(audioData.buffer);
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start(0);
      console.log("Audio playback started.");
    } catch (error) {
      console.error("Audio playback error:", error);
    }
  }
  if (data.message) {
    outputDiv.innerHTML += `<br><strong>Message:</strong> ${data.message}`;
  }
});

socket.addEventListener("close", () => {
  console.log("WebSocket disconnected.");
  outputDiv.innerHTML += "<br>WebSocket disconnected.";
});

socket.addEventListener("error", (error) => {
  console.error("WebSocket error:", error);
  outputDiv.innerHTML += "<br>Error occurred. Check console.";
});

setLanguageButton.addEventListener("click", () => {
  const selectedLanguage = languageSelector.value;
  const selectedRecognitionLanguage = recognitionLanguageSelector.value;
  try {
    socket.send(
      JSON.stringify({
        language: selectedLanguage,
        recognition_language: selectedRecognitionLanguage,
      })
    );
    console.log(
      `Language set to ${selectedLanguage}, recognition language set to ${selectedRecognitionLanguage}`
    );
    outputDiv.innerHTML += `<br>Language set to ${selectedLanguage}, recognition language set to ${selectedRecognitionLanguage}`;
  } catch (error) {
    console.error("Failed to set language:", error);
    outputDiv.innerHTML += "<br>Failed to set language.";
  }
});
