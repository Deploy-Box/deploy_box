const mongoose = require("mongoose");

const groceryItem = new mongoose.Schema(
  {
    name: {
      type: String,
      required: true,
    },
    category: {
      type: String,
      required: true,
    },
    price: {
      type: Number,
      required: true,
    },
    barcode: {
      type: String,
      required: true,
    },
    brand: {
      type: String,
      required: true,
    },
    stock: {
      type: Number,
      required: true,
    },
    expiry_date: {
      type: Date,
      required: true,
    },
  },
  { timestamps: true }
);

const Item = mongoose.model("Item", groceryItem);
module.exports = Item;
