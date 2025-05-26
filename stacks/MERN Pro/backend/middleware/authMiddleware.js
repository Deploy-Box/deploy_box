const jwt = require("jsonwebtoken");

const protect = (req, res, next) => {
  const token = req.headers.authorization.replace("Bearer ", "");
  const decoded = jwt.verify(token, process.env.JWT_SECRET);
  req.userData = decoded;
  next();
};

module.exports = { protect };