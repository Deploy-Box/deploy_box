const express = require("express");
const { getItems, addItem, updateItem, deleteItem } = require("../controllers/itemController");
const router = express.Router();

router.get("/", getItems);
router.post("/", addItem);
router.put("/:id", updateItem);
router.delete("/:id", deleteItem);

module.exports = router;
