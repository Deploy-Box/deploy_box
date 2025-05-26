import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import io from 'socket.io-client';
import './WebSocket.css';

const WebSocket = () => {
    const navigate = useNavigate();
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [currentRoom, setCurrentRoom] = useState('');
    const [newRoomInput, setNewRoomInput] = useState('');
    const [availableRooms] = useState(['general', 'random', 'tech']);
    const socketRef = useRef();
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

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
        socketRef.current.on("roomJoined", (room) => {
            setCurrentRoom(room);
            setMessages([]); // Clear messages when joining new room
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
    }, []);

    const handleLogout = () => {
        localStorage.removeItem('accessToken');
        navigate('/login');
    };

    const joinRoom = (room) => {
        if (currentRoom) {
            socketRef.current.emit("leaveRoom", currentRoom);
        }
        socketRef.current.emit("joinRoom", room);
    };

    const handleCreateRoom = (e) => {
        e.preventDefault();
        if (newRoomInput.trim()) {
            joinRoom(newRoomInput.trim());
            setNewRoomInput('');
        }
    };

    const sendMessage = (e) => {
        e.preventDefault();
        if (inputValue.trim() && currentRoom) {
            console.log("Sending message:", inputValue, "to room:", currentRoom);
            socketRef.current.emit("message", {
                room: currentRoom,
                message: inputValue
            });
            setInputValue('');
        }
    };

    const renderMessage = (message, index) => {
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

    return (
        <div className="websocket-container">
            <div className="rooms-section">
                <h3>Available Rooms</h3>
                <div className="room-list">
                    {availableRooms.map((room) => (
                        <button
                            key={room}
                            onClick={() => joinRoom(room)}
                            className={`room-button ${currentRoom === room ? 'active' : ''}`}
                        >
                            {room}
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
                    <button onClick={handleLogout} className="logout-button">
                        Logout
                    </button>
                </div>
            </div>
            
            <div className="chat-section">
                <div className="messages-container">
                    <h2>{currentRoom ? `Chat Messages - ${currentRoom}` : 'Select a Room'}</h2>
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