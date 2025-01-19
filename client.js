const serverUrl = "ws://localhost:8765";
const socket = new WebSocket(serverUrl);

const languageSelector = document.getElementById("languageSelector");
const setLanguageButton = document.getElementById("setLanguage");
const outputDiv = document.getElementById("output");

socket.addEventListener("open", () => {
  console.log("WebSocket connected.");
});

socket.addEventListener("message", async (event) => {
  console.log("Message from server:", event.data);

  const data = JSON.parse(event.data);

  if (data.translation) {
    // Display the translated text
    outputDiv.textContent += `\n${data.translation}`;
  }

  if (data.audio) {
    // Handle audio data
    const audioData = Uint8Array.from(atob(data.audio), (c) => c.charCodeAt(0));

    try {
      const audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
      const audioBuffer = await audioContext.decodeAudioData(audioData.buffer);
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start(0); // Play the audio
      console.log("Audio playback started.");
    } catch (error) {
      console.error("Error decoding or playing audio:", error);
    }
  }

  if (data.message) {
    // Display general messages from the server
    outputDiv.textContent += `\n${data.message}`;
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
  socket.send(JSON.stringify({ language: selectedLanguage }));
  console.log(`Language set to ${selectedLanguage}`);
  outputDiv.textContent += `\nLanguage set to ${selectedLanguage}`;
});
