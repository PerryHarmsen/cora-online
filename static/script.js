const recordBtn = document.getElementById("recordBtn");
const status = document.getElementById("status");
const chat = document.getElementById("chat");

recordBtn.onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream);
  let chunks = [];

  mediaRecorder.start();
  status.textContent = "Listening...";

  setTimeout(() => {
    mediaRecorder.stop();
  }, 5000); // Record for 5 seconds

  mediaRecorder.ondataavailable = e => chunks.push(e.data);

  mediaRecorder.onstop = async () => {
    status.textContent = "Processing...";
    const blob = new Blob(chunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append("audio", blob);

    const response = await fetch("/transcribe", { method: "POST", body: formData });
    const data = await response.json();
    const userText = data.text;

    chat.innerHTML += `<p><strong>You:</strong> ${userText}</p>`;

    const replyRes = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userText })
    });
    const replyData = await replyRes.json();
    const reply = replyData.reply;

    chat.innerHTML += `<p><strong>C.O.R.A.:</strong> ${reply}</p>`;

    // Play ElevenLabs voice (optional)
    const audioRes = await fetch("/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: reply })
    });
    const audioBlob = await audioRes.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    new Audio(audioUrl).play();

    status.textContent = "Idle";
  };
};