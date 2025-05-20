const express = require("express");
const cors = require("cors");
const itemRoutes = require("./routes/items");
const { DB_Connect } = require('./database');
const auth = require("./routes/auth.routes");

const app = express();
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
app.use("/api/auth", auth)

app.use("/error", (req, res) => {
  res.json({ message: db_error });
});

app.use("/", (req, res) => {
  res.json({ message: `Hello world, database is${db_is_connected ? "" : " not"} connected` });
});

app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send({ message: err.message });
});

app.use((req, res) => {
    res.status(404).send({ message: "Route not found" });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
