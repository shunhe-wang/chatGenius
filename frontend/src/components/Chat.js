import { useState, useEffect } from "react";
import CreateChannel from "./CreateChannel";

function Chat({ token }) {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [channelId, setChannelId] = useState(1); // Default channel
  const [channels, setChannels] = useState([]); // List of available channels

  const fetchMessages = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/channels/${channelId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setMessages(data);
    } catch (error) {
      console.error("Failed to fetch messages");
    }
  };

  const fetchChannels = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/channels/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setChannels(data);
    } catch (error) {
      console.error("Failed to fetch channels");
    }
  };

  const sendMessage = async () => {
    try {
      await fetch(`http://127.0.0.1:8000/channels/${channelId}/messages`, {
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

  const handleChannelCreated = (newChannel) => {
    setChannels((prevChannels) => [...prevChannels, newChannel]);
  };

  const handleChannelChange = (e) => {
    setChannelId(e.target.value);
    fetchMessages();
  };

  useEffect(() => {
    fetchChannels();
    fetchMessages();
  }, [channelId]);

  return (
    <div>
      <h2>Chat</h2>

      {/* Add the Create Channel form here */}
      <CreateChannel token={token} onChannelCreated={handleChannelCreated} />

      {/* Channel Selector */}
      <div>
        <h3>Channels</h3>
        <select value={channelId} onChange={handleChannelChange}>
          {channels.map((channel) => (
            <option key={channel.id} value={channel.id}>
              {channel.name}
            </option>
          ))}
        </select>
      </div>

      {/* Chat Messages */}
      <div>
        {messages.map((msg, idx) => (
          <p key={idx}>{msg.content}</p>
        ))}
      </div>

      {/* Message Input */}
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
