const express = require("express");
const cors = require("cors");
const itemRoutes = require("./routes/items");
const { DB_Connect } = require('./database');
const auth = require("./routes/authRoutes");
const { app, io, expressServer } = require('./middleware/websocket_middleware');
const roomRoutes = require("./routes/roomRoutes");

const corsOptions = {
  origin: "*", // Allow all origins (for testing)
  methods: "GET,HEAD,PUT,PATCH,POST,DELETE",
  allowedHeaders: "Content-Type,Authorization",
};

app.use(cors(corsOptions));
app.use(express.json());

let db_is_connected = false;

DB_Connect()
  .then(() => {
    console.log("MongoDB Connected")
    db_is_connected = true;
  })
  .catch((err) => {
    console.error("MongoDB Connection Error:", err)
    process.exit(1);
  });

app.use("/api/items", itemRoutes);
app.use("/api/rooms", roomRoutes);
app.use("/api/auth", auth);

app.use("/", (req, res) => {
  res.json({ message: "Welcome to the API" });
});

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ message: "Something went wrong!" });
});

app.use((req, res) => {
  res.status(404).json({ message: "Route not found" });
});
