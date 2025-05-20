const Validator = require("validatorjs");

const registerValidation = (req, res, next) => {
    const validateRule = {
        "fullName": "required|string|min:3", 
        "email": "required|email", 
        "password": "required|min:6",
        "phoneNumber": "required|max:10|min:10"
    };

    // Create a new instance of the validator
    const validation = new Validator(req.body, validateRule);

    // Check if validation fails
    if (validation.fails()) {
        return res.status(412).send({
            success: false,
            message: 'Validation failed',
            data: validation.errors
        });
    }

    // Proceed to the next middleware
    next();
};

const loginValidation = (req, res, next) => {
    const validateRule = {
        "email": "required|email", 
        "password": "required|min:6"
    };

    // Create a new instance of the validator
    const validation = new Validator(req.body, validateRule);

    // Check if validation fails
    if (validation.fails()) {
        return res.status(412).send({
            success: false,
            message: 'Validation failed',
            data: validation.errors
        });
    }

    // Proceed to the next middleware
    next();
};

module.exports = {
    registerValidation,
    loginValidation
};
