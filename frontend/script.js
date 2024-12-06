const apiUrl = 'http://127.0.0.1:5006/chat'; // Replace with your backend URL

document.getElementById('send-btn').addEventListener('click', sendMessage);
document.getElementById('user-query').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendMessage();
});

function appendMessage(content, sender = 'bot') {
  const chatHistory = document.getElementById('chat-history');
  const message = document.createElement('div');
  message.classList.add('message', sender);
  message.innerText = content;
  chatHistory.appendChild(message);
  chatHistory.scrollTop = chatHistory.scrollHeight; // Auto-scroll to the latest message
}

async function sendMessage() {
  const userInput = document.getElementById('user-query').value.trim();
  if (!userInput) return;

  appendMessage(userInput, 'user');
  document.getElementById('user-query').value = ''; // Clear the input

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: userInput,
        auth: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjp7Il9pZCI6IjY3M2VmZmIyMzU1NjM5NWMyZmYyMjIwZiIsIm5hbWUiOiJHb3ZpbmQgUmFqcHV0IiwiZW1haWwiOiJnb3ZpbmRyYWpwdXQzNzI3QGdtYWlsLmNvbSIsInBhc3N3b3JkIjoiJDJiJDEwJEJqdVE3eVNSekdhNWU3MXNscWh0SmV1NmN4eS5mUWhYcnBsQzZHS1NwUnpvUEkyYWMuVkhXIiwiZGVsZXRlZEF0IjpudWxsLCJyb2xlIjp7Il9pZCI6IjY3MWI0OWVkYTIzYWE4Zjg1MjIwMzQ4MCIsIm5hbWUiOiJ1c2VyIiwiX192IjowfSwiY3JlYXRlZEF0IjoiMjAyNC0xMS0yMVQwOTozODo1OC45MzBaIiwidXBkYXRlZEF0IjoiMjAyNC0xMS0yMVQwOTo0MToyNy41NTRaIiwiX192IjowLCJjaXR5IjoiSW5kb3JlIiwiY291bnRyeSI6IkluZGlhIiwiZ2VuZGVyIjoiTWFsZSIsInBpbl9jb2RlIjoiNDUyMDAxIiwic3RhdGUiOiJNYWRoeWEgUHJhZGVzaCJ9LCJpYXQiOjE3MzMzOTI3NjQsImV4cCI6MTczMzQxMDc2NH0.uNqV61ldCNOd8ERIMnlUhJ7qA2R0aH-QjKIINf-Ky5A", 
        IP: null, 
      }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();
    const { response: botResponse, property_details: properties } = data;

    appendMessage(botResponse);

    if (properties && properties.length > 0) {
      appendMessage('Here are some property details:', 'bot');
      properties.forEach((property) => {
        appendMessage(JSON.stringify(property, null, 2), 'bot'); // Format as JSON string
      });
    }
  } catch (error) {
    console.error('Error:', error);
    appendMessage('Sorry, something went wrong. Please try again.', 'bot');
  }
}
