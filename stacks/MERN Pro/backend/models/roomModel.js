const mongoose = require('mongoose');

const roomSchema = new mongoose.Schema({
    name: {
        type: String,
        required: true,
        unique: true,
        trim: true,
        lowercase: true
    }
}, {
    timestamps: true
});

// Index for faster queries
roomSchema.index({ name: 1 });

const Room = mongoose.model('Room', roomSchema);

module.exports = Room;
