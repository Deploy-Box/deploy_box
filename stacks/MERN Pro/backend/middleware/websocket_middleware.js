const { Server } = require("socket.io");
const express = require("express");

const port = process.env.PORT || 5500;

const app = express();

const expressServer = app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});

const io = new Server(expressServer, {
    cors: {
        origin: process.env.NODE_ENV === "production" ? false : ["http://127.0.0.1:5500", "http://localhost:5500"],
        methods: ["GET", "POST"]
    },
});

io.on("connection", (socket) => {
    console.log(`User ${socket.id} connected`);
    
    socket.on("message", (data) => {
        console.log(`Message received: ${data}`);
        io.emit('message', `${socket.id.slice(0,4)}: ${data}`);
    });

    socket.on("disconnect", () => {
        console.log(`User ${socket.id} disconnected`);
    });
});

module.exports = { io, app, expressServer };