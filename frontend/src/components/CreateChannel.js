import { useState } from "react";

function CreateChannel({ token, onChannelCreated }) {
    const [channelName, setChannelName] = useState("");
    const [channelDescription, setChannelDescription] = useState("");

    const handleCreateChannel = async () => {
        try {
            const response = await fetch("http://127.0.0.1:8000/channels/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ name: channelName, description: channelDescription }),
            });

            if (response.ok) {
                const newChannel = await response.json();
                onChannelCreated(newChannel);
                setChannelName("");
                setChannelDescription("");
                alert("Channel created successfully!");
            } else {
                alert("Failed to create channel");
            }
        } catch (error) {
            console.error("Error creating channel:", error);
        }
    };

    return (
        <div>
            <h3>Create Channel</h3>
            <input
                type="text"
                placeholder="Channel Name"
                value={channelName}
                onChange={(e) => setChannelName(e.target.value)}
            />
            <br />
            <input
                type="text"
                placeholder="Channel Description"
                value={channelDescription}
                onChange={(e) => setChannelDescription(e.target.value)}
            />
            <br />
            <button onClick={handleCreateChannel}>Create Channel</button>
        </div>
    );
}

export default CreateChannel;
