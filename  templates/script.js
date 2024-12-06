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
  chatHistory.scrollTop = chatHistory.scrollHeight; 
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
        auth: null, // Placeholder; replace with actual auth token if required
        IP: '127.0.0.1', // Example IP; replace with real user IP if needed
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
