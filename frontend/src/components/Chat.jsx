import { useState, useEffect, useRef } from "react";

import apiClient from "../api/client";
import { getApiErrorMessage } from "../api/errors";

export default function Chat({ onTaskCreated }) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await apiClient.get("/chat/history?limit=50");
        if (response.data.length === 0) {
          setMessages([
            {
              role: "assistant",
              content: "Tell me something like 'Schedule a meeting tomorrow at 3pm'.",
            },
          ]);
        } else {
          setMessages(response.data);
        }
      } catch (error) {
        const fallbackMessage = getApiErrorMessage(error, "Unable to load chat history.");
        console.error("Failed to load chat history:", fallbackMessage);
        setMessages([
          {
            role: "assistant",
            content: fallbackMessage,
          },
        ]);
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
    if (!trimmed || isSending) {
      return;
    }

    const nextMessages = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setMessage("");
    setIsSending(true);

    try {
      const response = await apiClient.post("/chat", { message: trimmed });
      const newMessages = response.data.messages || [];
      
      // If the backend returned both messages, we can just append the assistant one.
      // Or we can just append from response.data.message
      const assistantMessage = newMessages.find(m => m.role === "assistant") || {
        role: "assistant",
        content: response.data.message || "Task scheduled successfully",
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (onTaskCreated && response.data.task) {
        onTaskCreated(response.data.task);
      }
    } catch (error) {
      const errorMessage = getApiErrorMessage(
        error,
        "I couldn't schedule that task. Please try another phrasing."
      );

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

  return (
    <section className="panel chat-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Main feature</p>
          <h2>Chat scheduler</h2>
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
            <p className="typing-indicator">Escribiendo<span>.</span><span>.</span><span>.</span></p>
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
        <button className="primary-button" disabled={isSending || isLoadingHistory} type="submit">
          {isSending ? "Sending..." : "Send"}
        </button>
      </form>
    </section>
  );
}
