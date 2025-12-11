import { useState, useEffect, useRef } from "react";
import CrawlerForm from "./components/CrawlerForm";
import StatusDisplay from "./components/StatusDisplay";
import "./App.css";

const API_URL = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

function App() {
  const [validators, setValidators] = useState([]);
  const [statusUpdates, setStatusUpdates] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showForm, setShowForm] = useState(true);
  const wsRef = useRef(null);

  useEffect(() => {
    // Fetch available validators
    fetch(`${API_URL}/api/validators`)
      .then((res) => res.json())
      .then((data) => setValidators(data.validators))
      .catch((err) => console.error("Error fetching validators:", err));

    // Setup WebSocket connection
    const connectWebSocket = () => {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log("WebSocket connected");
      };

      ws.onmessage = (event) => {
        const update = JSON.parse(event.data);
        setStatusUpdates((prev) => [...prev, update]);

        if (update.type === "complete" || update.type === "error") {
          setIsRunning(false);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleStartCrawl = async (
    url,
    selectedValidators,
    maxPages,
  ) => {
    // Clear previous status updates
    setStatusUpdates([]);
    setIsRunning(true);
    setShowForm(false);

    try {
      const response = await fetch(`${API_URL}/api/crawl`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          validators: selectedValidators,
          max_pages: maxPages,
          max_depth: 2,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to start crawl");
      }

      const data = await response.json();
      console.log("Crawl started:", data);
    } catch (error) {
      console.error("Error starting crawl:", error);
      setIsRunning(false);
      setStatusUpdates([
        {
          type: "error",
          stage: "error",
          status: "failed",
          message: `Error: ${error.message}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  const handleNewScan = () => {
    setStatusUpdates([]);
    setShowForm(true);
    setIsRunning(false);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Data Collection Validator</h1>
        <p>Crawl websites and validate Adobe implementation</p>
      </header>

      <div className="app-content">
        {showForm && (
          <CrawlerForm
            validators={validators}
            onStartCrawl={handleStartCrawl}
            isRunning={isRunning}
          />
        )}

        {(statusUpdates.length > 0 || isRunning) && (
          <StatusDisplay
            updates={statusUpdates}
            isRunning={isRunning}
            onNewScan={handleNewScan}
          />
        )}
      </div>
    </div>
  );
}

export default App;
