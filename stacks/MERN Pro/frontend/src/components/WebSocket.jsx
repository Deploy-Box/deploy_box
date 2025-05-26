import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import io from 'socket.io-client';
import './WebSocket.css';

const WebSocket = () => {
    const navigate = useNavigate();
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [currentRoom, setCurrentRoom] = useState('');
    const [newRoomInput, setNewRoomInput] = useState('');
    const [availableRooms, setAvailableRooms] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const socketRef = useRef();
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // Fetch available rooms from the backend
    const fetchRooms = async () => {
        try {
            const token = localStorage.getItem('accessToken');
            const response = await fetch(`${window.env.REACT_APP_BACKEND_URL}/api/rooms`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch rooms');
            }

            const rooms = await response.json();
            setAvailableRooms(rooms);
            setIsLoading(false);
        } catch (error) {
            console.error('Error fetching rooms:', error);
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchRooms();
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        // Initialize socket connection with auth token
        const token = localStorage.getItem('accessToken');
        socketRef.current = io(window.env.REACT_APP_BACKEND_URL, {
            auth: {
                token
            }
        });

        // Listen for messages
        socketRef.current.on("message", (data) => {
            console.log("Received message:", data);
            setMessages(prevMessages => [...prevMessages, data]);
        });

        // Listen for room joined confirmation
        socketRef.current.on("roomJoined", (roomId) => {
            setCurrentRoom(availableRooms.find(room => room._id === roomId));
            setMessages([]); // Clear messages when joining new room
        });

        socketRef.current.on("chatHistory", (history) => {
            setMessages(history);
        });
        // Listen for new room creation
        socketRef.current.on("roomCreated", (newRoom) => {
            console.log("New room created:", newRoom);
            setAvailableRooms(prevRooms => {
                // Check if room already exists to prevent duplicates
                if (!prevRooms.some(room => room._id === newRoom._id)) {
                    return [...prevRooms, newRoom];
                }
                return prevRooms;
            });
        });

        // Listen for room deletion
        socketRef.current.on("roomDeleted", (roomId) => {
            console.log("Room deleted:", roomId);
            setAvailableRooms(prevRooms => prevRooms.filter(room => room._id !== roomId));
            // If user is in the deleted room, reset their room
            if (currentRoom && availableRooms.find(room => room._id === roomId)) {
                setCurrentRoom('');
                setMessages([]);
            }
        });

        // Cleanup on unmount
        return () => {
            if (socketRef.current) {
                if (currentRoom) {
                    socketRef.current.emit("leaveRoom", currentRoom);
                }
                socketRef.current.disconnect();
            }
        };
    }, [availableRooms]);

    const handleLogout = () => {
        localStorage.removeItem('accessToken');
        navigate('/login');
    };

    const joinRoom = async (roomId, roomName) => {
        try {
            const token = localStorage.getItem('accessToken');
            // Join room in backend
            const response = await fetch(`${window.env.REACT_APP_BACKEND_URL}/api/rooms/${roomId}/join`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to join room');
            }

            // Leave current room in socket if any
            if (currentRoom) {
                socketRef.current.emit("leaveRoom", currentRoom);
            }
            // Join new room in socket
            socketRef.current.emit("joinRoom", roomId);
            socketRef.current.emit("requestChatHistory", roomId);
        } catch (error) {
            console.error('Error joining room:', error);
        }
    };

    const handleCreateRoom = async (e) => {
        e.preventDefault();
        if (newRoomInput.trim()) {
            try {
                console.log("Creating room:", newRoomInput.trim());
                const token = localStorage.getItem('accessToken');
                const response = await fetch(`${window.env.REACT_APP_BACKEND_URL}/api/rooms`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ name: newRoomInput.trim() })
                });

                if (!response.ok) {
                    throw new Error('Failed to create room');
                }

                const newRoom = await response.json();
                setNewRoomInput('');
                // Automatically join the newly created room
                joinRoom(newRoom._id, newRoom.name);
                // Note: We don't need to manually update availableRooms here anymore
                // as it will be handled by the websocket event
            } catch (error) {
                console.error('Error creating room:', error);
            }
        }
    };

    const sendMessage = (e) => {
        e.preventDefault();
        if (inputValue.trim() && currentRoom && currentRoom._id) {
            console.log("Sending message:", inputValue, "to room:", currentRoom);
            socketRef.current.emit("message", {
                roomId: currentRoom._id,
                message: inputValue
            });
            setInputValue('');
        }
    };

    const renderMessage = (message, index) => {
        console.log("Rendering message:", message);
        if (message.type === 'system') {
            return (
                <div key={index} className="message system-message">
                    {message.content}
                </div>
            );
        }
        return (
            <div key={index} className="message chat-message">
                <span className="sender">{message.sender}:</span> {message.content}
            </div>
        );
    };

    const handleDeleteRoom = async () => {
        try {
            const roomId = currentRoom?._id;

            if (!roomId) {
                alert("Please select a room to delete");
                return;
            }

            console.log("Deleting room:", roomId);
            const token = localStorage.getItem('accessToken');
            const response = await fetch(`${window.env.REACT_APP_BACKEND_URL}/api/rooms/${roomId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete room');
            }

            setCurrentRoom('');
            setMessages([]);

            // Note: Room list update will be handled by the websocket event
        } catch (error) {
            console.error('Error deleting room:', error);
        }
    };

    if (isLoading) {
        return <div className="loading">Loading rooms...</div>;
    }

    return (
        <div className="websocket-container">
            <div className="rooms-section">
                <h3>Available Rooms</h3>
                <div className="room-list">
                    {availableRooms.map((room) => (
                        <button
                            key={room._id}
                            onClick={() => joinRoom(room._id, room.name)}
                            className={`room-button ${currentRoom.name === room.name ? 'active' : ''}`}
                        >
                            {room.name}
                        </button>
                    ))}
                </div>
                <form onSubmit={handleCreateRoom} className="create-room-form">
                    <input
                        type="text"
                        value={newRoomInput}
                        onChange={(e) => setNewRoomInput(e.target.value)}
                        placeholder="Create new room..."
                        className="room-input"
                    />
                    <button type="submit" className="create-room-button">Create Room</button>
                </form>
                <div className="logout-section">
                    <button onClick={handleDeleteRoom} className="logout-button" disabled={!currentRoom}>Delete Room</button>
                </div>
                <div className="logout-section">
                    <button onClick={handleLogout} className="logout-button">
                        Logout
                    </button>
                </div>
            </div>

            <div className="chat-section">
                <div className="messages-container">
                    <h2>{currentRoom ? `Chat Messages - ${currentRoom.name}` : 'Select a Room'}</h2>
                    <div className="messages-list">
                        {messages.map((message, index) => renderMessage(message, index))}
                        <div ref={messagesEndRef} />
                    </div>
                </div>

                <form onSubmit={sendMessage} className="message-form">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={currentRoom ? "Type your message..." : "Join a room to chat"}
                        className="message-input"
                        disabled={!currentRoom}
                    />
                    <button type="submit" className="send-button" disabled={!currentRoom}>
                        Send
                    </button>
                </form>
            </div>
        </div>
    );
};

export default WebSocket;