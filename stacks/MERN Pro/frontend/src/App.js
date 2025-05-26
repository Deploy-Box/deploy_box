import React, { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import axios from "axios";
import WebSocket from './components/WebSocket';

function Home({ message, items }) {
  return (
    <div>
      <h1>{message}</h1>
      <h1>Hello World</h1>
      <h2>Items</h2>
      <ul>
        {items.map((item) => (
          <li key={item._id}>{item.name}</li>
        ))}
      </ul>
    </div>
  );
}

function App() {
  const [message, setMessage] = useState("Backend is not connected");
  const [items, setItems] = useState([]);

  useEffect(() => {
    const baseUrl = window.env.REACT_APP_BACKEND_URL?.endsWith("/")
      ? window.env.REACT_APP_BACKEND_URL
      : `${window.env.REACT_APP_BACKEND_URL}/`;

    const url = `${baseUrl}api/items`;
    console.log(url);

    axios
      .get(url)
      .then((res) => {
        if (res.status === 200) {
          setMessage("Backend is connected");
          setItems(res.data);
          console.log(res.data);
        }
      })
      .catch((error) => console.error(error));
  }, []);

  return (
    <Router>
      <div>
        <nav>
          <ul>
            <li>
              <Link to="/">Home</Link>
            </li>
            <li>
              <Link to="/chat">Chat</Link>
            </li>
          </ul>
        </nav>

        <Routes>
          <Route path="/" element={<Home message={message} items={items} />} />
          <Route path="/chat" element={<WebSocket />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
