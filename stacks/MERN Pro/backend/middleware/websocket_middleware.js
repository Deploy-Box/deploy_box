const { Server } = require("socket.io");
const express = require("express");
const jwt = require("jsonwebtoken");

const port = process.env.PORT || 5500;

const app = express();

const expressServer = app.listen(port, "0.0.0.0", () => {
  console.log(`Server is running on port ${port}`);
});

const io = new Server(expressServer, {
  cors: {
    origin:
      process.env.NODE_ENV === "production"
        ? false
        : [
            "http://127.0.0.1:5500",
            "http://localhost:5500",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://192.168.4.35:3000",
          ],
    methods: ["GET", "POST"],
  },
});

// Middleware to authenticate socket connections
io.use((socket, next) => {
  try {
    const token = socket.handshake.auth.token;
    if (!token) {
      return next(new Error("Authentication failed - No token provided"));
    }

    // Verify the token
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    socket.user = decoded; // Store user data in socket for later use
    next();
  } catch (err) {
    return next(new Error("Authentication failed - Invalid token"));
  }
});

io.on("connection", (socket) => {
  console.log(`User ${socket.id} connected (${socket.user.email})`);

  // Handle joining a room
  socket.on("joinRoom", (room) => {
    socket.join(room);
    console.log(`User ${socket.id} (${socket.user.email}) joined room: ${room}`);
    socket.emit("roomJoined", room);
    
    const joinMessage = {
      type: 'system',
      content: `${socket.user.email} joined ${room}`,
      room: room
    };
    io.to(room).emit("message", joinMessage);
  });

  // Handle leaving a room
  socket.on("leaveRoom", (room) => {
    socket.leave(room);
    console.log(`User ${socket.id} (${socket.user.email}) left room: ${room}`);
    
    const leaveMessage = {
      type: 'system',
      content: `${socket.user.email} left ${room}`,
      room: room
    };
    io.to(room).emit("message", leaveMessage);
  });

  // Handle messages in a specific room
  socket.on("message", ({ room, message }) => {
    console.log(`Message received in room ${room} from ${socket.user.email}: ${message}`);
    const chatMessage = {
      type: 'chat',
      content: message,
      sender: socket.user.email,
      room: room
    };
    io.to(room).emit("message", chatMessage);
  });

  socket.on("disconnect", () => {
    console.log(`User ${socket.id} (${socket.user.email}) disconnected`);
  });
});

module.exports = { io, app, expressServer };
