const mongoose = require("mongoose");
const userSchema = mongoose.Schema({
  userId:{
    type:String
  }, 
  fullName:{
    type:String 
  }, 
  email:{
    type:String
  }, 
  password: {
    type:String
  },
})

module.exports = mongoose.model("User", userSchema)