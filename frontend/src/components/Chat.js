import { useState, useEffect } from "react";

function Chat({ token }) {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");

  const fetchMessages = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/channels/1/messages", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setMessages(data);
    } catch (error) {
      console.error("Failed to fetch messages");
    }
  };

  const sendMessage = async () => {
    try {
      await fetch("http://127.0.0.1:8000/channels/1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: newMessage }),
      });
      setNewMessage("");
      fetchMessages();
    } catch (error) {
      console.error("Failed to send message");
    }
  };

  useEffect(() => {
    fetchMessages();
  }, []);

  return (
    <div>
      <h2>Chat</h2>
      <div>
        {messages.map((msg, idx) => (
          <p key={idx}>{msg.content}</p>
        ))}
      </div>
      <input
        type="text"
        value={newMessage}
        onChange={(e) => setNewMessage(e.target.value)}
      />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
}

export default Chat;
