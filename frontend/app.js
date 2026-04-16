// This gets replaced with your real Railway URL in the next steps
const API_BASE = "https://meal-planner-production-d424.up.railway.app";

function getSessionId() {
  let id = localStorage.getItem("meal_session_id");
  if (!id) {
    id = "session_" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem("meal_session_id", id);
  }
  return id;
}

const sessionId = getSessionId();
document.getElementById("session-label").textContent = `Session: ${sessionId}`;

fetch(`${API_BASE}/session?session_id=${sessionId}`, { method: "POST" });

const chatBox   = document.getElementById("chat-box");
const input     = document.getElementById("user-input");
const sendBtn   = document.getElementById("send-btn");

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
  return div;
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  sendBtn.disabled = true;
  appendMessage("user", message);
  const botDiv = appendMessage("bot", "Thinking...");
  let fullText = "";

  try {
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    botDiv.textContent = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const line of decoder.decode(value).split("\n")) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6);
        if (data === "[DONE]") break;
        if (data.startsWith("[ERROR]")) { botDiv.textContent = data; break; }
        fullText += data;
        botDiv.textContent = fullText;
        chatBox.scrollTop = chatBox.scrollHeight;
      }
    }
  } catch (err) {
    botDiv.textContent = "Could not reach the server. Please try again.";
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keydown", e => { if (e.key === "Enter") sendMessage(); });