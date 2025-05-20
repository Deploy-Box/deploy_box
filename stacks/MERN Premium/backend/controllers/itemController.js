const Item = require("../models/itemModel");

// Get all items
async function getItems(req, res) {
    try {
        const items = await Item.find();
        res.json(items);
    } catch (error) {
        res.status(500).json({ message: "Error fetching items", error });
    }
}

// Add a new item
async function addItem(req, res) {
    try {
        if (typeof req.body !== "object") {
            return res.status(400).json({ message: "Request body must be an object" });
        }

        if (Array.isArray(req.body)) {
            return addBulkItems(req, res);
        }

        const newItem = new Item(req.body);
        const result = await newItem.save();
        res.status(201).json({ insertedId: result._id });
    } catch (error) {
        res.status(400).json({ message: "Error adding item", error });
    }
}

// Add bulk items
async function addBulkItems(req, res) {
    try {
        const items = req.body;
        const result = await Item.insertMany(items);
        res.status(201).json({ insertedCount: result.length });
    } catch (error) {
        res.status(400).json({ message: "Error adding items", error });
    }
}

// Update an item
async function updateItem(req, res) {
    const { id } = req.params;
    try {
        const updatedItem = await Item.findByIdAndUpdate(
            id,
            req.body,
            { new: true }
        );
        if (!updatedItem) {
            return res.status(404).json({ message: "Item not found" });
        }
        res.json(updatedItem);
    } catch (error) {
        res.status(400).json({ message: "Error updating item", error });
    }
}

// Delete an item
async function deleteItem(req, res) {
    const { id } = req.params;
    try {
        const deletedItem = await Item.findByIdAndDelete(id);
        if (!deletedItem) {
            return res.status(404).json({ message: "Item not found" });
        }
        res.json({ message: "Item deleted", deletedItem });
    } catch (error) {
        res.status(400).json({ message: "Error deleting item", error });
    }
}

module.exports = { getItems, addItem, updateItem, deleteItem };
