const serverUrl = "ws://localhost:8765";
const socket = new WebSocket(serverUrl);

const inputLanguageSelector = document.getElementById("inputLanguageSelector");
const outputLanguageSelector = document.getElementById(
  "outputLanguageSelector"
);
const setLanguageButton = document.getElementById("setLanguage");
const outputDiv = document.getElementById("output");

socket.addEventListener("open", () => {
  console.log("WebSocket connected.");
});

socket.addEventListener("message", async (event) => {
  console.log("Message from server:", event.data);

  const data = JSON.parse(event.data);

  if (data.translation) {
    outputDiv.textContent += `\nTranslation: ${data.translation}`;
  }

  if (data.audio) {
    try {
      const audioData = Uint8Array.from(atob(data.audio), (c) =>
        c.charCodeAt(0)
      );
      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
      const audioBuffer = await audioContext.decodeAudioData(audioData.buffer);
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start(0);
      console.log("Audio playback started.");
    } catch (error) {
      console.error("Error decoding or playing audio:", error);
    }
  }

  if (data.message) {
    outputDiv.textContent += `\nMessage: ${data.message}`;
  }
});

socket.addEventListener("close", () => {
  console.log("WebSocket disconnected.");
});

socket.addEventListener("error", (error) => {
  console.error("WebSocket error:", error);
});

setLanguageButton.addEventListener("click", () => {
  const inputLanguage = inputLanguageSelector.value;
  const outputLanguage = outputLanguageSelector.value;

  socket.send(
    JSON.stringify({
      language: outputLanguage,
      source_language: inputLanguage,
    })
  );
  console.log(
    `Output language set to ${outputLanguage}, source language set to ${inputLanguage}`
  );
  outputDiv.textContent += `\nOutput language set to ${outputLanguage}, source language set to ${inputLanguage}`;
});
