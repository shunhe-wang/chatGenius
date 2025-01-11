import { useState, useEffect } from "react";
import CreateChannel from "./CreateChannel";

function Chat({ token }) {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [channelId, setChannelId] = useState(1); // Default channel
  const [channels, setChannels] = useState([]); // List of available channels
  const [userId, setUserId] = useState(null);
  const [socket, setSocket] = useState(null);
  const [selectedThread, setSelectedThread] = useState(null);
  const [threadMessages, setThreadMessages] = useState([]);

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
    if (!newMessage.trim()) return; // Don't send empty messages
    
    try {
      const response = await fetch(`http://127.0.0.1:8000/channels/${channelId}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: newMessage }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        console.error("Failed to send message:", error);
        return;
      }
      
      setNewMessage(""); // Clear input only on success
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const handleChannelCreated = (newChannel) => {
    setChannels((prevChannels) => [...prevChannels, newChannel]);
  };

  const handleChannelChange = (e) => {
    setChannelId(Number(e.target.value));
    fetchMessages();
  };

  const handleReaction = async (messageId, emoji) => {
    try {
      await fetch(`http://127.0.0.1:8000/messages/${messageId}/reactions?emoji=${emoji}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error("Failed to add reaction", error);
    }
  };

  const fetchThreadMessages = async (messageId) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/messages/${messageId}/thread`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json();
      setThreadMessages(data);
    } catch (error) {
      console.error("Failed to fetch thread messages");
    }
  };

  const sendReply = async (parentId, content) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/messages/${parentId}/reply`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content }),
      });
      
      if (!response.ok) {
        throw new Error("Failed to send reply");
      }
      
      setNewMessage(""); // Clear input
    } catch (error) {
      console.error("Failed to send reply:", error);
    }
  };

  useEffect(() => {
    if (channelId) {
      fetchMessages();
    }
  }, [channelId]);

  useEffect(() => {
    // Assuming your token is a JWT, decode it to get the user ID
    // This is a basic example - adjust according to your token structure
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      setUserId(payload.sub); // or whatever field contains the user ID
    } catch (error) {
      console.error('Failed to decode token', error);
    }
  }, [token]);

  useEffect(() => {
    // Create WebSocket connection with token in URL
    const ws = new WebSocket(`ws://127.0.0.1:8000/ws?token=${token}`);
    
    ws.onopen = () => {
      console.log('WebSocket Connected');
      // Subscribe to current channel
      if (channelId) {
        ws.send(JSON.stringify({
          type: 'subscribe',
          channel_id: channelId
        }));
      }
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message received:', data);
      
      switch (data.type) {
        case 'new_message':
          // Add new message to state
          setMessages(prev => [...prev, data.message]);
          break;
        
        case 'new_reply':
          if (selectedThread === data.parent_id) {
            setThreadMessages(prev => [...prev, data.message]);
          }
          break;
        
        case 'reaction_update':
          // Update message reactions
          setMessages(prev => 
            prev.map(msg => 
              msg.id === data.message_id 
                ? { ...msg, reactions: data.reactions }
                : msg
            )
          );
          break;
          
        default:
          console.log('Unknown message type:', data.type);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      // Optionally implement reconnection logic here
    };
    
    setSocket(ws);
    
    // Cleanup on unmount
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [token, channelId, selectedThread]);

  // Add channel subscription when channel changes
  useEffect(() => {
    if (socket && socket.readyState === WebSocket.OPEN && channelId) {
      socket.send(JSON.stringify({
        type: 'subscribe',
        channel_id: channelId
      }));
    }
  }, [socket, channelId]);

  useEffect(() => {
    fetchChannels();
  }, [token]);

  return (
    <div style={{ display: 'flex' }}>
      <div style={{ flex: 1 }}>
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
          {messages.map((msg, idx) => {
            console.log('Rendering message:', msg);
            return (
              <div key={idx} style={{ marginBottom: '10px' }}>
                <p>{msg.content}</p>
                <div style={{ display: 'flex', gap: '5px' }}>
                  {['👍', '❤️', '😄', '🎉'].map((emoji) => (
                    <button 
                      key={emoji}
                      onClick={() => handleReaction(msg.id, emoji)}
                      style={{
                        background: msg.reactions?.[emoji]?.includes(userId) ? '#e3e3e3' : 'white',
                        padding: '5px 10px',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      {emoji} {msg.reactions?.[emoji]?.length || 0}
                    </button>
                  ))}
                  <button 
                    onClick={() => {
                      setSelectedThread(msg.id);
                      fetchThreadMessages(msg.id);
                    }}
                  >
                    Reply
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Message Input */}
        <input
          type="text"
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
        />
        <button onClick={sendMessage}>Send</button>
      </div>

      {/* Thread sidebar */}
      {selectedThread && (
        <div style={{ width: '300px', borderLeft: '1px solid #ccc', padding: '20px' }}>
          <button onClick={() => setSelectedThread(null)}>Close Thread</button>
          
          <div style={{ marginTop: '20px' }}>
            {threadMessages.map((msg, idx) => (
              <div key={idx} style={{ marginBottom: '10px' }}>
                <p>{msg.content}</p>
              </div>
            ))}
          </div>
          
          {/* Thread reply input */}
          <div style={{ marginTop: '20px' }}>
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Reply to thread..."
            />
            <button onClick={() => sendReply(selectedThread, newMessage)}>Reply</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Chat;
