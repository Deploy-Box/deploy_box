const express = require('express');
const router = express.Router();
const Room = require('../models/roomModel');
const Chat = require('../models/chatModel');
const { protect } = require('../middleware/authMiddleware');
const { io } = require('../middleware/websocket_middleware');

// Create a new room
router.post('/', protect, async (req, res) => {
    try {
        const { name } = req.body;

        // Create new room
        const room = new Room({
            name: name.toLowerCase(),
        });

        await room.save();
        
        // Emit websocket event to all clients about the new room
        io.emit('roomCreated', room);
        
        res.status(201).json(room);
    } catch (error) {
        console.error("Error creating room:", error);
        res.status(500).json({ message: 'Error creating room', error: error.message });
    }
});

// Get all public rooms
router.get('/', protect, async (req, res) => {
    try {
        const rooms = await Room.find();
        res.json(rooms);
    } catch (error) {
        res.status(500).json({ message: 'Error fetching rooms', error: error.message });
    }
});

// Delete a room (only by creator)
router.delete('/:roomId', protect, async (req, res) => {
    try {
        const {roomId} = req.params;

        console.log("Deleting room:", roomId);

        
        const room = await Room.findOne({ 
            _id: roomId,
        });

        if (!room) {
            return res.status(404).json({ message: 'Room not found or unauthorized' });
        }

        await Chat.deleteMany({ roomId: roomId });
        await room.deleteOne();
        
        // Emit websocket event to all clients about the deleted room
        io.emit('roomDeleted', roomId);
        
        res.json({ message: 'Room deleted successfully' });
    } catch (error) {
        res.status(500).json({ message: 'Error deleting room', error: error.message });
    }
});

module.exports = router;
