import { useState, useEffect, useRef } from "react";

import apiClient from "../api/client";

const EMPTY_STATE_MESSAGE = {
  role: "assistant",
  content: "Tell me something like 'Schedule a meeting tomorrow at 3pm'.",
};

export default function Chat({ onTaskCreated }) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await apiClient.get("/chat/history?limit=50");
        if (response.data.length === 0) {
          setMessages([EMPTY_STATE_MESSAGE]);
        } else {
          setMessages(response.data);
        }
      } catch (error) {
        console.error("Failed to load chat history:", error);
      } finally {
        setIsLoadingHistory(false);
      }
    };
    fetchHistory();
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const handleSubmit = async (event) => {
    event.preventDefault();

    const trimmed = message.trim();
    if (!trimmed || isSending || isClearing) {
      return;
    }

    const nextMessages = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setMessage("");
    setIsSending(true);

    try {
      const response = await apiClient.post("/chat/message", { message: trimmed });
      const newMessages = response.data.messages || [];

      const assistantMessage = newMessages.find((entry) => entry.role === "assistant") || {
        role: "assistant",
        content: response.data.message || "Task scheduled successfully",
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (onTaskCreated && response.data.task) {
        onTaskCreated(response.data.task);
      }
    } catch (error) {
      const errorMessage =
        error.response?.data?.detail || "I couldn't schedule that task. Please try another phrasing.";

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: errorMessage,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const handleClearMemory = async () => {
    if (isSending || isClearing) {
      return;
    }

    setIsClearing(true);
    try {
      await apiClient.delete("/chat/history");
      setMessages([EMPTY_STATE_MESSAGE]);
    } catch (error) {
      console.error("Failed to clear chat memory:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I couldn't clear the saved memory right now.",
        },
      ]);
    } finally {
      setIsClearing(false);
    }
  };

  const statusLabel = isClearing
    ? "Clearing memory..."
    : isSending
      ? "Recordando contexto..."
      : "Persistent memory enabled";

  return (
    <section className="panel chat-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Main feature</p>
          <h2>Chat scheduler</h2>
        </div>
        <div className="chat-panel-actions">
          <span className={`chat-status ${isSending ? "chat-status-active" : ""}`}>{statusLabel}</span>
          <button
            className="ghost-button"
            disabled={isLoadingHistory || isSending || isClearing}
            onClick={handleClearMemory}
            type="button"
          >
            {isClearing ? "Clearing..." : "Limpiar memoria"}
          </button>
        </div>
      </div>

      <div className="chat-history">
        {isLoadingHistory ? (
          <div className="chat-loading">Cargando historial...</div>
        ) : (
          messages.map((entry, index) => (
            <article
              className={`message-bubble ${entry.role === "user" ? "user-message" : "system-message"}`}
              key={entry.id ? entry.id : `${entry.role}-${index}`}
            >
              <span>{entry.role === "user" ? "You" : "Assistant"}</span>
              <p>{entry.content}</p>
            </article>
          ))
        )}
        {isSending && (
          <article className="message-bubble system-message">
            <span>Assistant</span>
            <p className="typing-indicator">Recordando contexto<span>.</span><span>.</span><span>.</span></p>
          </article>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <textarea
          placeholder="Schedule lunch with Ana tomorrow at 1pm"
          rows="3"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />
        <button className="primary-button" disabled={isSending || isClearing || isLoadingHistory} type="submit">
          {isSending ? "Sending..." : "Send"}
        </button>
      </form>
    </section>
  );
}
