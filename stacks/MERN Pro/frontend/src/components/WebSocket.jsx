import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';

const WebSocket = () => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const socketRef = useRef();

    useEffect(() => {
        // Initialize socket connection
        socketRef.current = io("http://localhost:5500");

        // Listen for messages
        socketRef.current.on("message", (data) => {
            console.log("Received message:", data);
            setMessages(prevMessages => [...prevMessages, data]);
        });

        // Cleanup on unmount
        return () => {
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
        };
    }, []);

    const sendMessage = (e) => {
        e.preventDefault();
        if (inputValue.trim()) {
            console.log("Sending message:", inputValue);
            socketRef.current.emit("message", inputValue);
            setInputValue('');
        }
    };

    return (
        <div className="websocket-container">
            <div className="messages-container">
                <h2>Chat Messages</h2>
                <ul>
                    {messages.map((message, index) => (
                        <li key={index}>{message}</li>
                    ))}
                </ul>
            </div>
            <form onSubmit={sendMessage} className="message-form">
                <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Type your message..."
                    className="message-input"
                />
                <button type="submit" className="send-button">Send</button>
            </form>
        </div>
    );
};

export default WebSocket; 