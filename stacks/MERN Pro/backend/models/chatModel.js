const mongoose = require("mongoose");
const chatSchema = mongoose.Schema({
  senderUserId: {
    type: String,
  },
  roomId: {
    type: String,
  },
  messageContent: {
    type: String,
  },
  timeStamp: {
    type: Date,
    default: Date.now,
  },
});

module.exports = mongoose.model("Chat", chatSchema);
