const express = require("express");
const router = express.Router();

//Imporing the authvalidation functions for login and register 
const {  registerValidation, loginValidation} = require("../middleware")
//Importing functions from auth controller
const { login, register, userProfile, users} = require("../controllers/auth.controller")
//Importing the JWT verifyer from auth middleware 
const verifyToken = require("../auth.middleware") 

//Register route with register validation 
router.post("/register", registerValidation, register);
//Login route with register validation
router.post("/login", loginValidation, login);
//Profile route with register validation
router.get("/profile/:id", verifyToken, userProfile);
//all users route with 
router.get("/users", verifyToken, users);

module.exports = router;